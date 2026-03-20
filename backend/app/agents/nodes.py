import re
import unicodedata

from app.agents.state import AgentState
from app.agents.tools import tool_rag_search, tool_web_search_allowlist
from app.services.llm import generate_sales_reply
from app.core.db import SessionLocal
from app.services.agents import get_published_agent_version_or_none
from app.services.conversation_context import (
    ConversationContextSnapshot,
    build_conversation_context_snapshot,
    format_conversation_context_for_prompt,
    load_cached_conversation_context,
)
from app.services.personas import get_persona_context_for_agent


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip()


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


def _extract_property_type(text: str) -> str | None:
    folded = _fold(text)
    if any(term in folded for term in ["casa", "imovel", "imóvel", "apartamento", "sobrado", "terreno"]):
        if "casa" in folded:
            return "casa"
        if "apartamento" in folded:
            return "apartamento"
        if "sobrado" in folded:
            return "sobrado"
        if "terreno" in folded:
            return "terreno"
        return "imovel"
    return None


def _extract_lance(text: str) -> str | None:
    folded = _fold(text)
    if "lance" not in folded and "dar" not in folded:
        return None
    return _extract_amount(text)


def _build_conversation_memory(history: list[dict[str, str]], current_message: str) -> dict[str, str]:
    property_type: str | None = None
    property_value: str | None = None
    timeline: str | None = None
    lance: str | None = None
    summary_parts: list[str] = []

    for item in history + [{"role": "user", "content": current_message}]:
        content = item.get("content", "")
        if not content:
            continue
        role = item.get("role", "user")
        if role == "user":
            extracted_type = _extract_property_type(content)
            if extracted_type:
                property_type = extracted_type

            extracted_timeline = _extract_timeline(content)
            if extracted_timeline:
                timeline = extracted_timeline

            extracted_lance = _extract_lance(content)
            if extracted_lance:
                lance = extracted_lance

            extracted_value = _extract_amount(content)
            if extracted_value and "lance" not in _fold(content):
                property_value = extracted_value

            folded = _fold(content)
            if any(term in folded for term in ["quero", "gostaria", "objetivo", "pretendo", "quero ver", "quero comprar"]):
                summary_parts.append(_clean_text(content))

    if property_type:
        summary_parts.append(f"tipo_de_imovel={property_type}")
    if property_value:
        summary_parts.append(f"valor_do_imovel={property_value}")
    if timeline:
        summary_parts.append(f"prazo={timeline}")
    if lance:
        summary_parts.append(f"lance={lance}")

    return {
        "property_type": property_type or "nao informado",
        "property_value": property_value or "nao informado",
        "timeline": timeline or "nao informado",
        "lance": lance or "nao informado",
        "summary": "; ".join(summary_parts) if summary_parts else "sem fatos estruturados",
    }


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

    if memory["property_type"] != "nao informado" and memory["property_value"] != "nao informado" and memory["timeline"] != "nao informado":
        core = "Se fizer sentido, eu sigo com a proposta e a simulacao usando o valor do bem, o prazo e o lance que voce ja passou."
    elif memory["property_type"] != "nao informado" and memory["property_value"] != "nao informado":
        core = "Se quiser, eu sigo com a simulacao usando o valor do bem que voce ja passou."
    elif "orcamento" in query or "parcela" in query or state.intent == "price":
        core = "Qual faixa de parcela cabe hoje no seu orcamento para eu montar a melhor simulacao?"
    elif "adesao" in query or "contrato" in query:
        core = "Se fizer sentido, eu posso te orientar agora no proximo passo da proposta e contrato digital."
    elif "seminovo" in query or "carro" in query:
        core = "Me diga o veiculo desejado, ano e faixa de valor para eu direcionar a simulacao."
    elif memory["property_type"] in {"casa", "imovel", "apartamento", "sobrado", "terreno"}:
        core = "Me diga o tipo de imovel, a faixa de valor e o prazo para eu direcionar a simulacao."
    else:
        core = "Se quiser, eu sigo com uma simulacao guiada usando valor do bem, prazo e faixa de parcela."

    if "diret" in tone or "assertiv" in tone:
        return f"Vamos avancar: {core}"
    if "premium" in tone or "sofistic" in tone:
        return f"Proximo passo sugerido: {core}"
    return f"Para eu te orientar melhor: {core}"


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
    text = state.message_text.lower()
    if any(word in text for word in ["casa", "imovel", "imóvel", "apartamento", "sobrado", "terreno"]):
        state.intent = "property"
    elif "lance" in text:
        state.intent = "lance"
    elif any(word in text for word in ["preco", "valor", "custo", "orcamento", "orçamento", "parcela"]):
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
    memory = _build_conversation_memory(state.conversation_history, state.message_text)
    runtime = await _get_agent_runtime_context(state)
    structured_context_block = format_conversation_context_for_prompt(cached_context)
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
        "Se faltar dado, deixe claro e faca uma pergunta objetiva. "
        "Nao volte a pedir informacoes ja informadas na memoria da conversa. "
        "Se o lead enviar apenas um numero ou valor curto, trate como atualizacao do campo mais provavel ja discutido na conversa. "
        "Se a conversa ja tiver valor do bem, prazo e lance, consolide esses dados e avance para simulacao ou proposta, sem recomeçar a qualificacao. "
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
        f"{persona_block}"
        f"Intento={state.intent}. "
        f"Historico={history_block}. "
        f"Contexto={state.retrieved_context}. "
        f"Pergunta do lead={state.message_text}"
    )
    state.draft_reply = await generate_sales_reply(prompt)
    _enforce_grounding_rules(state)
    state.reply_fragments = _split_reply_fragments(state.draft_reply)
    state.follow_up_suggestion = _build_follow_up_suggestion(state, runtime)
    state.next_action = "send"
    return state
