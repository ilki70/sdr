import re
import unicodedata

from app.agents.state import AgentState
from app.agents.tools import tool_rag_search, tool_web_search_allowlist
from app.services.llm import generate_sales_reply
from app.core.db import SessionLocal
from app.services.agents import get_published_agent_version_or_none
from app.services.personas import get_persona_context_for_agent


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


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
            reply = f"{reply.rstrip()} Sobre entrada ou condicoes iniciais, o correto e confirmar pela proposta oficial da VINAC."

    if ("seminovo" in folded_query or "idade" in folded_query) and "3 anos" in folded_context and "3 anos" not in folded_reply:
        reply = f"{reply.rstrip()} Pelo contexto oficial VINAC usado aqui, o seminovo deve ter ate 3 anos."

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
            reply = f"{reply.rstrip()} Se quiser, eu preparo uma simulacao dentro do menor intervalo oficial da VINAC."

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

    if "orcamento" in query or "parcela" in query or state.intent == "price":
        core = "Qual faixa de parcela cabe hoje no seu orcamento para eu montar a melhor simulacao?"
    elif "adesao" in query or "contrato" in query:
        core = "Se fizer sentido, eu posso te orientar agora no proximo passo da proposta e contrato digital."
    elif "seminovo" in query or "carro" in query:
        core = "Me diga o veiculo desejado, ano e faixa de valor para eu direcionar a simulacao."
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
    if any(word in text for word in ["preco", "valor", "custo"]):
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
    history_block = " | ".join(history_lines[-8:]) if history_lines else "sem historico anterior"
    runtime = await _get_agent_runtime_context(state)
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
        "Sempre tente conduzir o lead para o proximo passo concreto, como simulacao, adesao ou envio de proposta. "
        "Se o lead falar de orcamento, compatibilize a resposta com faixas de parcela e sem inventar valores fora do contexto. "
        "Nao invente taxa de adesao, entrada, carencia ou limite tecnico que nao esteja explicitamente no contexto. "
        "Regras operacionais: "
        "se a pergunta for sobre seminovo e limite de idade, responda objetivamente com o limite oficial. "
        "Se a pergunta for sobre adesao, cite proposta, contrato digital, primeira parcela e inicio da concorrencia. "
        "Se a pergunta for sobre carta de credito, cite que pode escolher outro modelo e onde comprar, conforme contexto. "
        "Se o orcamento estiver abaixo da faixa minima do site, reconheca isso de forma consultiva, cite a faixa minima oficial, "
        "evite encerrar a conversa cedo e faca uma pergunta objetiva sobre carro desejado, prazo ou margem para aproximar a parcela minima. "
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
