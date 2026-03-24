from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select

from app.agents.state import AgentState
from app.agents.tools import tool_rag_search, tool_web_search_allowlist
from app.core.db import SessionLocal
from app.models.entities import Lead
from app.services.agents import get_published_agent_version_or_none
from app.services.conversation_context import (
    ConversationContextSnapshot,
    build_conversation_context_snapshot,
    format_conversation_context_for_prompt,
    load_cached_conversation_context,
)
from app.services.lead_capture import describe_lead_profile, next_required_profile_field_label, required_profile_fields
from app.services.llm import generate_sales_reply
from app.services.personas import get_persona_context_for_agent

_EMOJI_CODEPOINT_RANGES = (
    (0x1F300, 0x1FAFF),
    (0x1F1E6, 0x1F1FF),
    (0x2600, 0x27BF),
)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip()


def _is_emoji_char(char: str) -> bool:
    if not char:
        return False
    codepoint = ord(char)
    return any(start <= codepoint <= end for start, end in _EMOJI_CODEPOINT_RANGES)


def _limit_emojis(text: str, *, max_emojis: int = 1) -> str:
    if max_emojis <= 0:
        return "".join(char for char in text if not _is_emoji_char(char))

    kept: list[str] = []
    emoji_count = 0
    for char in text:
        if _is_emoji_char(char):
            emoji_count += 1
            if emoji_count <= max_emojis:
                kept.append(char)
            continue
        kept.append(char)
    return "".join(kept)


def _format_currency_like(value: str) -> str:
    compact = _clean_text(value)
    if not compact:
        return compact
    if re.search(r"(?i)\br\$", compact):
        return compact
    return compact if compact.startswith("R$") else f"R$ {compact}"


def _extract_amount(text: str) -> str | None:
    folded = _fold(text)
    if not folded:
        return None

    match = re.search(r"(\d+(?:[.,]\d+)?\s*(?:mil|milhao|milhoes|mi|k|mil))", folded)
    if match:
        value = match.group(1).replace(" ", "")
        value = value.replace("milhao", "milhão").replace("milhoes", "milhões")
        return _format_currency_like(value)

    match = re.search(r"r\$\s*([\d.,]+)", folded)
    if match:
        return _format_currency_like(f"R$ {match.group(1)}")

    match = re.search(r"\b(\d{2,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b", folded)
    if match:
        return _format_currency_like(match.group(1))
    return None


def _extract_timeline(text: str) -> str | None:
    folded = _fold(text)
    match = re.search(r"(?:ate|até|em)\s+(\d+\s*(?:meses?|anos?|semanas?|dias?))", folded)
    if match:
        return match.group(1).replace("  ", " ").strip()
    match = re.search(r"\b(\d+\s*(?:meses?|anos?|semanas?|dias?))\b", folded)
    if match:
        return match.group(1).replace("  ", " ").strip()
    return None


def _looks_like_timeline_answer(text: str) -> bool:
    folded = _fold(text)
    return any(term in folded for term in ["mes", "meses", "ano", "anos", "semana", "semanas", "dia", "dias"])


def _extract_property_type(text: str) -> str | None:
    folded = _fold(text)
    if any(
        term in folded
        for term in [
            "casa",
            "imovel",
            "imóvel",
            "apartamento",
            "sobrado",
            "terreno",
            "moto",
            "motocicleta",
            "carro",
            "veiculo",
            "veículo",
            "caminhao",
            "caminhão",
            "caminhonete",
        ]
    ):
        if "casa" in folded:
            return "casa"
        if "apartamento" in folded:
            return "apartamento"
        if "sobrado" in folded:
            return "sobrado"
        if "terreno" in folded:
            return "terreno"
        if "moto" in folded or "motocicleta" in folded:
            return "moto"
        if "caminhonete" in folded:
            return "caminhonete"
        if "caminhao" in folded:
            return "caminhao"
        if "carro" in folded:
            return "carro"
        if "veiculo" in folded:
            return "veiculo"
        return "imovel"
    return None


def _extract_lance(text: str) -> str | None:
    folded = _fold(text)
    if "lance" not in folded and "dar" not in folded:
        return None
    return _extract_amount(text)


def _infer_expected_slot(history: list[dict[str, str]]) -> str | None:
    last_assistant_message = next(
        (item.get("content", "") for item in reversed(history) if item.get("role") == "assistant" and item.get("content")),
        "",
    )
    folded = _fold(last_assistant_message)
    if not folded:
        return None
    if "lance" in folded:
        return "lance"
    if "prazo" in folded or "meses" in folded or "anos" in folded:
        return "timeline"
    if "valor" in folded or "faixa de valor" in folded or "quanto" in folded:
        return "property_value"
    if "tipo de imovel" in folded or "qual bem" in folded or "qual veiculo" in folded:
        return "property_type"
    return None


def _build_conversation_memory(history: list[dict[str, str]], current_message: str) -> dict[str, str]:
    messages = history + ([{"role": "user", "content": current_message}] if current_message else [])
    snapshot = build_conversation_context_snapshot(
        messages,
        tenant_id="memory",
        conversation_id="memory",
        last_intent="unknown",
    )
    return {
        "lead_name": snapshot.lead_name,
        "asset_type": snapshot.asset_type,
        "asset_value": snapshot.asset_value,
        "target_use_case": snapshot.target_use_case,
        "goal": snapshot.goal,
        "timeline": snapshot.timeline,
        "lance": snapshot.lance,
        "current_question_slot": snapshot.current_question_slot,
        "last_confirmed_slot": snapshot.last_confirmed_slot,
        "summary": snapshot.summary,
        "extracted_slots": str(snapshot.extracted_slots),
    }


def _build_conversation_delta(previous: dict[str, str], current: dict[str, str]) -> list[str]:
    labels = {
        "lead_name": "lead_name",
        "asset_type": "asset_type",
        "asset_value": "asset_value",
        "target_use_case": "target_use_case",
        "goal": "goal",
        "timeline": "prazo",
        "lance": "lance",
    }
    delta: list[str] = []
    for key, label in labels.items():
        before = previous.get(key, "nao informado")
        after = current.get(key, "nao informado")
        if after != "nao informado" and after != before:
            delta.append(f"{label}={after}")
    return delta


def _proposal_commitment_state(history: list[dict[str, str]]) -> str:
    assistant_messages = [
        _fold(item.get("content", ""))
        for item in history
        if item.get("role") == "assistant" and item.get("content")
    ]
    if any(
        token in message
        for message in assistant_messages
        for token in [
            "vou preparar a simulacao",
            "vou enviar a simulacao",
            "proposta personalizada",
            "proposta oficial",
            "ja estou preparando a simulacao",
        ]
    ):
        return "simulacao_em_andamento"
    return "nenhum"


def _build_initial_opening_fragments() -> list[str]:
    return [
        "Olá! Aqui é da Orfi Consórcios 👋",
        "Me conta: você está buscando imóvel ou veículo?",
    ]


def _enforce_grounding_rules(state: AgentState) -> None:
    reply = state.draft_reply
    folded_reply = _fold(reply)
    folded_query = _fold(state.message_text)
    folded_context = _fold(" ".join(state.retrieved_context))

    if "financi" in folded_query and "nao exige entrada" in folded_reply:
        reply = reply.replace(
            "nao exige entrada",
            "tem condicoes que devem ser confirmadas na proposta oficial",
        )
    if "financi" in folded_query and "nao precisa de entrada" in folded_reply:
        reply = reply.replace(
            "nao precisa de entrada",
            "deve ter as condicoes confirmadas na proposta oficial",
        )
    if "financi" in folded_query and "entrada" in _fold(reply):
        reply = re.sub(
            r"(?i)ja\s+que\s+as\s+parcelas\s+sao\s+fixas\s+e\s+nao\s+ha\s+necessidade\s+de\s+entrada\.?",
            "ja que o planejamento e previsivel e as condicoes especificas devem ser confirmadas na proposta oficial.",
            reply,
        )
        reply = re.sub(
            r"(?i)nao\s+(exige|ha necessidade de|precisa de)\s+entrada",
            "tem condicoes que devem ser confirmadas na proposta oficial",
            reply,
        )
        if "entrada" in _fold(reply):
            reply = f"{reply.rstrip()} Sobre entrada ou condicoes iniciais, o correto e confirmar pela proposta oficial do produto."

    if ("seminovo" in folded_query or "idade" in folded_query) and "3 anos" in folded_context and "3 anos" not in folded_reply:
        reply = f"{reply.rstrip()} Pelo contexto oficial usado aqui, o seminovo deve ter ate 3 anos."

    if "adesao" in folded_query and "primeira parcela" in folded_context and "concorr" not in folded_reply:
        reply = f"{reply.rstrip()} Depois de pagar a primeira parcela, voce ja comeca a concorrer no grupo."
    elif "adesao" in folded_query and "primeira parcela" in folded_context and "ja comeca a concorrer" not in folded_reply:
        reply = f"{reply.rstrip()} Em termos praticos, depois de pagar a primeira parcela, voce ja comeca a concorrer."

    if ("orcamento" in folded_query or "900" in folded_query) and ("1.000" in folded_context or "1000" in folded_context):
        if "1.000" not in reply and "1000" not in reply:
            reply = f"{reply.rstrip()} No fluxo online atual, as parcelas divulgadas no site comecam em R$ 1.000,00."
        reply = reply.replace("entrada maior", "avaliar simulacao guiada")
        if "faixa minima" not in _fold(reply):
            reply = f"{reply.rstrip()} Hoje voce esta abaixo da faixa minima publicada no site."
        if "qual carro" not in _fold(reply):
            reply = f"{reply.rstrip()} Me diga qual carro voce busca e se existe alguma margem para aproximar da parcela minima."
        if "simul" not in _fold(reply):
            reply = f"{reply.rstrip()} Se quiser, eu preparo uma simulacao dentro do menor intervalo oficial do produto."

    if "carta" in folded_query and "onde comprar" in folded_context and "onde comprar" not in folded_reply:
        reply = f"{reply.rstrip()} O contexto oficial tambem informa que voce tem liberdade para escolher onde comprar o veiculo."

    state.draft_reply = reply


def _split_reply_fragments(reply: str, max_chars: int = 180) -> list[str]:
    sentences = [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+", reply.replace("\n", " ").strip())
        if segment.strip()
    ]
    if not sentences:
        return [reply.strip()] if reply.strip() else []

    fragments: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            fragments.append(current.strip())
        current = sentence
    if current:
        fragments.append(current.strip())
    return fragments[:4]


def _build_follow_up_suggestion(state: AgentState, persona: dict[str, str] | None) -> str:
    tone = _fold(persona["tone"]) if persona else "consultivo"
    query = _fold(state.message_text)
    memory = _build_conversation_memory(state.conversation_history, state.message_text)
    lead = getattr(state, "lead_profile", None)

    if lead:
        missing_label = next_required_profile_field_label(lead)
        qualified_for_proposal = (
            memory["asset_type"] != "nao informado"
            and memory["asset_value"] != "nao informado"
            and memory["timeline"] != "nao informado"
        )
        if missing_label and qualified_for_proposal:
            core = f"Antes da simulacao, preciso confirmar seu {missing_label}."
            if "diret" in tone or "assertiv" in tone:
                return f"Vamos fechar o cadastro: {core}"
            if "premium" in tone or "sofistic" in tone:
                return f"Proximo passo sugerido: {core}"
            return f"Para eu avancar com seguranca: {core}"

    if memory["asset_type"] != "nao informado" and memory["asset_value"] != "nao informado" and memory["timeline"] != "nao informado":
        core = "Se fizer sentido, eu sigo com a proposta e a simulacao usando o valor do bem, o prazo e o lance que voce ja passou."
    elif memory["asset_type"] != "nao informado" and memory["asset_value"] != "nao informado":
        core = "Se quiser, eu sigo com a simulacao usando o valor do bem que voce ja passou."
    elif "orcamento" in query or "parcela" in query or state.intent == "price":
        core = "Qual faixa de parcela cabe hoje no seu orcamento para eu montar a melhor simulacao?"
    elif "adesao" in query or "contrato" in query:
        core = "Se fizer sentido, eu posso te orientar agora no proximo passo da proposta e contrato digital."
    elif state.intent == "investment" or any(term in query for term in ["investir", "investimento", "vale a pena", "retorno"]):
        core = "Me diga o objetivo do investimento, o valor do bem e o prazo desejado para eu alinhar a melhor proposta."
    elif "seminovo" in query or "carro" in query:
        core = "Me diga o veiculo desejado, ano e faixa de valor para eu direcionar a simulacao."
    elif memory["asset_type"] in {"casa", "imovel", "apartamento", "sobrado", "terreno"}:
        core = "Me diga o tipo de imovel, a faixa de valor e o prazo para eu direcionar a simulacao."
    elif memory["asset_type"] in {"moto", "carro", "veiculo", "caminhao", "caminhonete"}:
        core = "Me diga a faixa de valor, o prazo e se voce pretende usar lance para eu direcionar a simulacao."
    else:
        core = "Se quiser, eu sigo com uma simulacao guiada usando valor do bem, prazo e faixa de parcela."

    if "diret" in tone or "assertiv" in tone:
        return f"Vamos avancar: {core}"
    if "premium" in tone or "sofistic" in tone:
        return f"Proximo passo sugerido: {core}"
    return f"Para eu te orientar melhor: {core}"


def _build_first_touch_style_guidance(state: AgentState) -> str:
    has_assistant_turn = any(item.get("role") == "assistant" for item in state.conversation_history)
    guidance = [
        "Mantenha um tom simpatico, acolhedor e educado.",
        "Evite repetir a mesma saudacao, a mesma pergunta ou a mesma formula de texto em turnos consecutivos.",
        "Nao altere a ordem atual de coleta de dados; apenas deixe a conversa mais natural e humana.",
        "Use o nome do lead com parcimonia; nao repita o nome em toda resposta.",
        "Use emojis com muita parcimonia: no maximo um emoji sutil na abertura e evite emojis nas demais respostas.",
        "Faça no maximo uma pergunta por turno.",
        "Confirme somente os dados novos que chegaram nesta rodada, em uma frase curta, sem repetir o resumo completo.",
    ]
    if not has_assistant_turn:
        guidance.insert(
            0,
            (
                "Se esta for a primeira resposta do atendimento, cumprimente, se apresente como Íris, "
                "pergunte o nome do lead e diga que esta disponivel para ajudar com duvidas sobre consorcios."
            ),
        )
        guidance.insert(
            1,
            (
                "Depois da abertura, conduza com delicadeza para entender o que o lead pretende "
                "para que a melhor proposta possa ser preparada."
            ),
        )
    return " ".join(guidance)


async def _load_lead_for_state(state: AgentState) -> Lead | None:
    if not state.lead_id:
        return None
    async with SessionLocal() as session:
        result = await session.execute(
            select(Lead).where(
                Lead.tenant_id == state.tenant_id,
                Lead.id == state.lead_id,
            )
        )
        return result.scalar_one_or_none()


def _format_lead_profile_block(lead: Lead | None) -> str:
    if not lead:
        return "cadastro_indisponivel"
    return (
        f"nome={lead.name or 'nao informado'}; "
        f"cpf={getattr(lead, 'cpf', None) or 'nao informado'}; "
        f"telefone={lead.phone or 'nao informado'}; "
        f"status={describe_lead_profile(lead)}"
    )


async def _get_agent_runtime_context(state: AgentState) -> dict[str, str]:
    persona = await get_persona_context_for_agent(state.tenant_id, state.agent_id)
    async with SessionLocal() as session:
        if state.agent_id:
            agent_version = await get_published_agent_version_or_none(session, state.tenant_id, state.agent_id)
        else:
            agent_version = None
    policy_text = ""
    if agent_version:
        policy_text = "; ".join(str(item) for item in agent_version.policy_json.get("rules", []))
    return {
        "persona_name": persona["persona_name"] if persona else "nao configurada",
        "tone": persona["tone"] if persona else "consultivo",
        "prompt_system": agent_version.prompt_system if agent_version else (persona["prompt_system"] if persona else ""),
        "approach_rules": persona["approach_rules"] if persona else "",
        "objection_playbook": persona["objection_playbook"] if persona else "",
        "policy_text": policy_text,
    }


async def classify_intent(state: AgentState) -> AgentState:
    text = _fold(state.message_text)
    if any(word in text for word in ["casa", "imovel", "apartamento", "sobrado", "terreno", "moto", "carro", "veiculo", "caminhao", "caminhonete"]):
        state.intent = "property"
    elif any(word in text for word in ["investir", "investimento", "vale a pena", "retorno", "aplicar", "aplicacao"]):
        state.intent = "investment"
    elif "lance" in text:
        state.intent = "lance"
    elif any(word in text for word in ["preco", "valor", "custo", "orcamento", "parcela"]):
        state.intent = "price"
    elif any(word in text for word in ["duvida", "como funciona"]):
        state.intent = "question"
    else:
        state.intent = "generic"
    state.confidence_score = 0.7
    return state


async def retrieve_context(state: AgentState) -> AgentState:
    rag_context = await tool_rag_search(state.tenant_id, state.message_text)
    web_context = await tool_web_search_allowlist(state.tenant_id, state.message_text)
    state.retrieved_context = rag_context + web_context
    return state


async def compose_reply(state: AgentState) -> AgentState:
    assistant_turn_count = sum(
        1 for item in state.conversation_history if item.get("role") == "assistant" and item.get("content")
    )
    if assistant_turn_count == 0:
        opening_fragments = _build_initial_opening_fragments()
        state.draft_reply = "\n\n".join(opening_fragments)
        state.reply_fragments = opening_fragments
        state.follow_up_suggestion = "Perguntar se o lead busca imóvel ou veículo."
        state.next_action = "send"
        return state

    history_lines = [
        f"{item['role']}: {item['content']}"
        for item in state.conversation_history
        if item.get("content")
    ]
    history_block = " | ".join(history_lines[-12:]) if history_lines else "sem historico anterior"
    cached_context = None
    if state.conversation_context:
        cached_context = ConversationContextSnapshot.model_validate(state.conversation_context)
    elif state.conversation_id:
        cached_context = await load_cached_conversation_context(state.tenant_id, state.conversation_id)
    if cached_context is None:
        cached_context = build_conversation_context_snapshot(
            state.conversation_history,
            tenant_id=state.tenant_id,
            conversation_id=state.conversation_id or "unknown",
            last_intent=state.intent,
        )
    previous_memory = _build_conversation_memory(state.conversation_history, "")
    memory = _build_conversation_memory(state.conversation_history, state.message_text)
    new_facts = _build_conversation_delta(previous_memory, memory)
    new_facts_block = ", ".join(new_facts) if new_facts else "nenhum dado novo estruturado"
    runtime = await _get_agent_runtime_context(state)
    lead_profile = await _load_lead_for_state(state)
    state.lead_profile = lead_profile
    structured_context_block = format_conversation_context_for_prompt(cached_context)
    lead_profile_block = _format_lead_profile_block(lead_profile)
    required_profile_block = ",".join(required_profile_fields(lead_profile)) if lead_profile else "desconhecido"
    proposal_commitment_block = _proposal_commitment_state(state.conversation_history)
    media_block = " | ".join(state.media_context) if state.media_context else "sem midia"
    persona_block = (
        f"Agente ativo={runtime['persona_name']}. "
        f"Tom={runtime['tone']}. "
        f"Prompt base={runtime['prompt_system']}. "
        f"Regras comerciais={runtime['approach_rules']}. "
        f"Tratamento de objecoes={runtime['objection_playbook']}. "
        f"Politicas do agente={runtime['policy_text']}. "
    )
    prompt = (
        "Atue como atendente comercial consultivo configuravel. "
        "Priorize o playbook publicado do agente e as paginas oficiais do cliente quando estiverem no contexto. "
        "Use apenas fatos sustentados pelo contexto oficial recuperado. "
        f"{_build_first_touch_style_guidance(state)} "
        "Se faltar dado, deixe claro e faca uma pergunta objetiva. "
        "Nao volte a pedir informacoes ja informadas na memoria da conversa. "
        "Use os slots estruturados da memoria curta como fonte principal de contexto da conversa. "
        "Para liberar simulacao, proposta ou envio comercial, o cadastro obrigatorio precisa ter nome completo, CPF e telefone. "
        "Se o lead ja estiver qualificado para proposta, mas algum desses dados obrigatorios faltar, pergunte apenas pelo proximo dado faltante e nao ofereca a proposta ainda. "
        "Quando o telefone ja vier do canal, nao peca telefone novamente. "
        "Se o historico mostrar que simulacao ou proposta ja foi prometida, nao reinicie qualificacao nem volte a pedir dados ja confirmados. "
        "Nesse estado, responda como simulacao em andamento: esclareca as opcoes concretas, reconheca o que ja foi combinado e avance sem contradicao. "
        "Se o lead contestar repeticao ou incoerencia, reconheca o contexto ja capturado e corrija a rota em vez de repetir a mesma pergunta. "
        "So atualize um slot quando houver alta confianca no texto do lead ou quando a ultima pergunta do assistente apontar explicitamente esse slot. "
        "Se o lead enviar apenas um numero ou valor curto, trate como resposta ao slot perguntado no turno anterior. "
        "Se a conversa ja tiver bem, valor, prazo e lance, consolide esses dados e avance para simulacao ou proposta, sem recomeçar a qualificacao. "
        f"Dados novos desta rodada={new_facts_block}. "
        "Se houver dado novo, confirme apenas esse dado, sem refazer todo o resumo e sem reapresentar o proprio nome. "
        "Se nao houver dado novo, nao comece com confirmacao; avance com uma pergunta ou um proximo passo util. "
        "Nunca faça mais de uma pergunta por resposta. "
        f"Contexto estruturado do Redis={structured_context_block}. "
        f"Midia processada={media_block}. "
        "Sempre tente conduzir o lead para o proximo passo concreto, como simulacao, adesao ou envio de proposta. "
        "Se o lead falar de orcamento, compatibilize a resposta com faixas de parcela e sem inventar valores fora do contexto. "
        "Nao invente taxa de adesao, entrada, carencia ou limite tecnico que nao esteja explicitamente no contexto. "
        "Regras operacionais: "
        "se a pergunta for sobre seminovo e limite de idade, responda objetivamente com o limite oficial. "
        "Se a pergunta for sobre adesao, cite proposta, contrato digital, primeira parcela e inicio da concorrencia. "
        "Se a pergunta for sobre carta de credito, cite que pode escolher outro modelo e onde comprar, conforme contexto. "
        "Se o orcamento estiver abaixo da faixa minima do site, reconheca isso de forma consultiva, cite a faixa minima oficial, "
        "evite encerrar a conversa cedo e faca uma pergunta objetiva sobre carro desejado, prazo ou margem para aproximar a parcela minima. "
        f"Memoria da conversa={memory}. "
        f"Cadastro do lead={lead_profile_block}. "
        f"Campos obrigatorios ainda faltando={required_profile_block}. "
        f"Estado de proposta={proposal_commitment_block}. "
        f"{persona_block}"
        f"Intento={state.intent}. "
        f"Historico={history_block}. "
        f"Contexto={state.retrieved_context}. "
        f"Pergunta do lead={state.message_text}"
    )
    state.draft_reply = await generate_sales_reply(prompt)
    _enforce_grounding_rules(state)
    state.draft_reply = _limit_emojis(state.draft_reply, max_emojis=1)
    state.reply_fragments = _split_reply_fragments(state.draft_reply)
    state.follow_up_suggestion = _build_follow_up_suggestion(state, runtime)
    state.next_action = "send"
    return state
