from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - optional dependency in this host
    END = "__end__"
    START = "__start__"
    StateGraph = None

from app.core.config import get_settings
from app.services.conversation_context import (
    ConversationContextSnapshot,
    _extract_asset_value,
    _extract_goal,
    _extract_lance,
    _extract_property_type,
    _extract_target_use_case,
    _extract_timeline,
    _infer_expected_slot,
)
from app.services.lead_capture import extract_cpf, extract_full_name, extract_phone


settings = get_settings()


@dataclass
class LangGraphTurnRequest:
    tenant_id: str
    conversation_id: str
    message_text: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    lead_name: str | None = None
    lead_phone: str | None = None
    lead_cpf: str | None = None
    lead_metadata: dict[str, Any] = field(default_factory=dict)
    conversation_context: dict[str, Any] = field(default_factory=dict)
    channel: str = "whatsapp"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LangGraphTurnResponse:
    reply_text: str
    reply_fragments: list[str]
    follow_up_suggestion: str | None = None
    handoff_requested: bool = False
    slot_projection: dict[str, Any] = field(default_factory=dict)
    runtime_label: str = "langgraph"
    flow_stage: str = "qualification"


@dataclass
class RuntimeContext:
    slots: dict[str, str]
    expected_slot: str | None = None
    last_confirmed_slot: str | None = None
    missing_profile_fields: list[str] = field(default_factory=list)
    summary: str = ""
    memory_notes: list[str] = field(default_factory=list)
    pipeline_status: str | None = None
    new_slots: dict[str, str] = field(default_factory=dict)
    proposal_commitment_state: str = "nenhum"


def is_langgraph_runtime_enabled() -> bool:
    return bool(settings.langgraph_runtime_enabled)


def _extract_existing_projection(request: LangGraphTurnRequest) -> dict[str, str]:
    metadata = request.lead_metadata or {}
    projection = metadata.get("langgraph_slot_projection")
    if isinstance(projection, dict):
        return {str(key): str(value) for key, value in projection.items() if isinstance(key, str) and isinstance(value, str)}
    return {}


def _validated_snapshot(request: LangGraphTurnRequest) -> ConversationContextSnapshot | None:
    payload = request.conversation_context or {}
    if not isinstance(payload, dict) or not payload:
        return None
    try:
        return ConversationContextSnapshot.model_validate(payload)
    except Exception:
        return None


def _extract_projection_from_snapshot(snapshot: ConversationContextSnapshot | None) -> dict[str, str]:
    if snapshot is None:
        return {}

    projection: dict[str, str] = {}
    projection.update(
        {
            key: value
            for key, value in snapshot.extracted_slots.items()
            if isinstance(key, str) and isinstance(value, str) and value and value != "nao informado"
        }
    )
    mapping = {
        "lead_name": snapshot.lead_name,
        "asset_type": snapshot.asset_type,
        "goal": snapshot.goal,
        "asset_value": snapshot.asset_value,
        "timeline": snapshot.timeline,
        "lance": snapshot.lance,
    }
    for key, value in mapping.items():
        if isinstance(value, str) and value and value != "nao informado":
            projection[key] = value
    return projection


def _detect_human_request(text: str) -> bool:
    lowered = text.lower()
    triggers = (
        "atendente",
        "humano",
        "pessoa",
        "consultor",
        "falar com algu",
        "quero falar com",
    )
    return any(trigger in lowered for trigger in triggers)


def _metadata_missing_profile_fields(request: LangGraphTurnRequest) -> list[str]:
    metadata = request.lead_metadata or {}
    values = metadata.get("required_profile_fields_missing")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str)]


def _metadata_pipeline_status(request: LangGraphTurnRequest) -> str | None:
    metadata = request.lead_metadata or {}
    value = metadata.get("pipeline_status") or request.metadata.get("pipeline_status")
    return value if isinstance(value, str) and value.strip() else None


def _proposal_commitment_state(history: list[dict[str, str]], pipeline_status: str | None) -> str:
    if pipeline_status in {"scheduled", "proposal_ready", "proposal", "simulation"}:
        return "simulacao_em_andamento"
    assistant_messages = [
        str(item.get("content") or "").lower()
        for item in history
        if item.get("role") == "assistant" and item.get("content")
    ]
    if any(
        token in message
        for message in assistant_messages
        for token in (
            "vou preparar a simulação",
            "vou preparar a simulacao",
            "vou enviar a simulação",
            "vou enviar a simulacao",
            "proposta personalizada",
            "proposta oficial",
            "já estou preparando a simulação",
            "ja estou preparando a simulacao",
            "sigo para a simulação",
            "sigo para a simulacao",
        )
    ):
        return "simulacao_em_andamento"
    return "nenhum"


def _build_runtime_context(request: LangGraphTurnRequest) -> RuntimeContext:
    snapshot = _validated_snapshot(request)
    slots = _extract_projection_from_snapshot(snapshot)
    slots.update(_extract_existing_projection(request))
    if request.lead_name:
        slots["lead_name"] = request.lead_name
    if request.lead_phone:
        slots["phone"] = request.lead_phone
    if request.lead_cpf:
        slots["cpf"] = request.lead_cpf
    expected_slot = None
    last_confirmed_slot = None
    summary = ""
    memory_notes: list[str] = []
    if snapshot is not None:
        if snapshot.current_question_slot != "nao informado":
            expected_slot = snapshot.current_question_slot
        if snapshot.last_confirmed_slot != "nao informado":
            last_confirmed_slot = snapshot.last_confirmed_slot
        if snapshot.summary != "sem fatos estruturados":
            summary = snapshot.summary
        memory_notes = list(snapshot.memory_notes)

    pipeline_status = _metadata_pipeline_status(request)
    return RuntimeContext(
        slots=slots,
        expected_slot=expected_slot,
        last_confirmed_slot=last_confirmed_slot,
        missing_profile_fields=_metadata_missing_profile_fields(request),
        summary=summary,
        memory_notes=memory_notes,
        pipeline_status=pipeline_status,
        proposal_commitment_state=_proposal_commitment_state(request.conversation_history, pipeline_status),
    )


def _apply_message_to_slots(runtime: RuntimeContext, request: LangGraphTurnRequest) -> RuntimeContext:
    slots = dict(runtime.slots)
    previous_slots = dict(slots)
    text = request.message_text
    expected_slot = runtime.expected_slot or _infer_expected_slot(request.conversation_history)

    lead_name = extract_full_name(text)
    if lead_name and (expected_slot == "lead_name" or not _extract_property_type(text)):
        slots["lead_name"] = lead_name

    asset_type = _extract_property_type(text)
    if asset_type:
        slots["asset_type"] = asset_type

    target_use_case = _extract_target_use_case(text)
    if target_use_case:
        slots["goal"] = target_use_case

    extracted_goal = _extract_goal(text)
    if extracted_goal and "goal" not in slots and expected_slot == "goal":
        slots["goal"] = extracted_goal

    asset_value = _extract_asset_value(text)
    timeline = _extract_timeline(text)
    lance = _extract_lance(text)

    if asset_value and expected_slot != "lance":
        slots["asset_value"] = asset_value
    if timeline:
        slots["timeline"] = timeline
    if lance:
        slots["lance"] = lance

    cpf = extract_cpf(text)
    if cpf:
        slots["cpf"] = cpf

    phone = extract_phone(text)
    if phone:
        slots["phone"] = phone

    runtime.slots = slots
    runtime.expected_slot = expected_slot
    runtime.new_slots = {
        key: value
        for key, value in slots.items()
        if value and previous_slots.get(key) != value
    }
    return runtime


def _missing_business_slots(slots: dict[str, str]) -> list[str]:
    ordered = ("asset_type", "goal", "asset_value", "timeline")
    return [slot for slot in ordered if not slots.get(slot)]


def _missing_profile_slots(runtime: RuntimeContext) -> list[str]:
    if runtime.missing_profile_fields:
        normalized = {
            "nome_completo": "lead_name",
            "cpf": "cpf",
            "telefone": "phone",
        }
        return [normalized[item] for item in runtime.missing_profile_fields if item in normalized]

    slots = runtime.slots
    missing: list[str] = []
    if not slots.get("lead_name"):
        missing.append("lead_name")
    if not slots.get("cpf"):
        missing.append("cpf")
    if not slots.get("phone"):
        missing.append("phone")
    return missing


def _slot_prompt(slot_name: str, *, greeted: bool) -> list[str]:
    prompts = {
        "lead_name": [
            "Olá! Aqui é da Orfi Consórcios.",
            "Para eu te atender melhor, qual é o seu nome?",
        ]
        if not greeted
        else ["Para eu te atender melhor, qual é o seu nome?"],
        "asset_type": ["Você está buscando imóvel ou veículo?"],
        "goal": ["Seu objetivo principal é morar, investir ou outro?"],
        "asset_value": ["Qual é a faixa de valor do bem que você busca?"],
        "timeline": ["Qual prazo faz sentido para você?"],
        "cpf": ["Antes de seguir com a simulação, preciso confirmar seu CPF."],
        "phone": ["E qual telefone devo usar no seu cadastro?"],
    }
    return prompts.get(slot_name, ["Me diga um pouco mais para eu seguir com você."])


def _has_previous_assistant_turn(request: LangGraphTurnRequest) -> bool:
    return any(item.get("role") == "assistant" for item in request.conversation_history)


def _follow_up_for_slot(slot_name: str) -> str:
    labels = {
        "lead_name": "nome do lead",
        "asset_type": "tipo de bem",
        "goal": "objetivo principal",
        "asset_value": "faixa de valor",
        "timeline": "prazo",
        "cpf": "CPF",
        "phone": "telefone",
    }
    return f"Capturar {labels.get(slot_name, slot_name)}."


def _slot_confirmation(runtime: RuntimeContext) -> str | None:
    ordered_labels = {
        "lead_name": "nome",
        "asset_type": "bem",
        "goal": "objetivo",
        "asset_value": "valor",
        "timeline": "prazo",
        "lance": "lance",
        "cpf": "CPF",
        "phone": "telefone",
    }
    parts: list[str] = []
    for key in ("lead_name", "asset_type", "goal", "asset_value", "timeline", "lance", "cpf", "phone"):
        value = runtime.new_slots.get(key)
        if value:
            label = ordered_labels[key]
            parts.append(f"{label}: {value}")
    if not parts:
        return None
    if len(parts) == 1:
        return f"Perfeito, anotei {parts[0]}."
    return f"Perfeito, anotei {'; '.join(parts[:3])}."


def _detect_objection_type(text: str) -> str | None:
    lowered = text.lower()
    objection_map = {
        "fees": ("taxa", "juros", "caro", "custa", "administracao", "administração"),
        "trust": ("seguro", "confiar", "golpe", "medo", "confiavel", "confiável"),
        "comparison": ("financiamento", "financiar", "comparado", "comparacao", "comparação"),
        "lance": ("lance",),
        "timeline": ("contemplac", "contemplação", "quando", "demora", "prazo"),
    }
    for objection_type, tokens in objection_map.items():
        if any(token in lowered for token in tokens):
            return objection_type
    return None


def _objection_reply(objection_type: str, runtime: RuntimeContext) -> str:
    if objection_type == "fees":
        return "Faz sentido olhar isso com cuidado. O melhor caminho aqui é comparar o custo total e o prazo da proposta oficial, sem prometer economia fora do cenário real."
    if objection_type == "trust":
        return "Sua cautela faz sentido. Eu posso te orientar com base no fluxo oficial e, antes de qualquer avanço, deixar a proposta e as condições bem claras."
    if objection_type == "comparison":
        return "A comparação faz sentido, mas ela depende muito do prazo, da parcela e da estratégia de contemplação. O ideal é colocar seu caso no papel antes de concluir qual caminho fica melhor."
    if objection_type == "lance":
        if runtime.slots.get("lance"):
            return f"Perfeito. Considerando o lance de {runtime.slots['lance']}, eu consigo seguir a conversa sem perder esse ponto."
        return "O lance pode acelerar bastante, mas ele precisa ser analisado junto com valor do bem, prazo e estratégia da proposta."
    if objection_type == "timeline":
        return "Prazo de contemplação é um ponto importante. O ideal é alinhar valor do bem, prazo e estratégia para te orientar com responsabilidade."
    return "Entendi seu ponto. Eu vou te orientar de forma objetiva e sem prometer algo fora do contexto."


def _proposal_progress_reply(runtime: RuntimeContext) -> list[str]:
    slots = runtime.slots
    if slots.get("asset_value") and slots.get("timeline"):
        return [
            "Perfeito. Eu sigo com a simulação com base no que já alinhamos.",
            f"Hoje eu tenho valor em {slots['asset_value']} e prazo em {slots['timeline']}.",
        ]
    return ["Perfeito. Eu sigo com a simulação com base no que já alinhamos."]


def _looks_like_restart_question(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "tudo bem",
            "oi",
            "ola",
            "olá",
            "viu minha mensagem",
            "andou",
            "avançou",
            "avancou",
        )
    )


def _compose_langgraph_reply(runtime: RuntimeContext, request: LangGraphTurnRequest) -> LangGraphTurnResponse:
    slots = runtime.slots
    confirmation = _slot_confirmation(runtime)
    if _detect_human_request(request.message_text):
        fragments = [
            "Vou direcionar seu atendimento para um consultor humano.",
        ]
        return LangGraphTurnResponse(
            reply_text="\n\n".join(fragments),
            reply_fragments=fragments,
            follow_up_suggestion="Assumir atendimento humano e revisar contexto capturado.",
            handoff_requested=True,
            slot_projection=slots,
            flow_stage="handoff",
        )

    if runtime.pipeline_status == "handoff":
        fragments = ["Seu atendimento já está com um consultor humano. Vou manter o contexto atualizado por aqui."]
        return LangGraphTurnResponse(
            reply_text=fragments[0],
            reply_fragments=fragments,
            follow_up_suggestion="Aguardar atendimento humano e revisar novas mensagens do lead.",
            handoff_requested=True,
            slot_projection=slots,
            flow_stage="handoff",
        )

    if runtime.proposal_commitment_state == "simulacao_em_andamento":
        missing_profile = _missing_profile_slots(runtime)
        if missing_profile:
            next_slot = missing_profile[0]
            fragments = _proposal_progress_reply(runtime)
            fragments.append(_slot_prompt(next_slot, greeted=True)[0])
            return LangGraphTurnResponse(
                reply_text="\n\n".join(fragments),
                reply_fragments=fragments,
                follow_up_suggestion=_follow_up_for_slot(next_slot),
                slot_projection=slots,
                flow_stage="proposal_in_progress",
            )
        if _looks_like_restart_question(request.message_text):
            fragments = _proposal_progress_reply(runtime)
            fragments.append("Se fizer sentido, eu sigo daqui sem reiniciar sua qualificação.")
            return LangGraphTurnResponse(
                reply_text="\n\n".join(fragments),
                reply_fragments=fragments,
                follow_up_suggestion="Seguir com simulacao sem reiniciar qualificacao.",
                slot_projection=slots,
                flow_stage="proposal_in_progress",
            )

    objection_type = _detect_objection_type(request.message_text)
    if objection_type:
        missing_business = _missing_business_slots(slots)
        base = _objection_reply(objection_type, runtime)
        if missing_business:
            next_slot = runtime.expected_slot or missing_business[0]
            if next_slot not in missing_business:
                next_slot = missing_business[0]
            ask = _slot_prompt(next_slot, greeted=True)[0]
            fragments = [base, ask] if not confirmation else [confirmation, base, ask]
            return LangGraphTurnResponse(
                reply_text="\n\n".join(fragments),
                reply_fragments=fragments,
                follow_up_suggestion=_follow_up_for_slot(next_slot),
                slot_projection=slots,
                flow_stage="objection_handling",
            )
        if _missing_profile_slots(runtime):
            next_slot = _missing_profile_slots(runtime)[0]
            ask = _slot_prompt(next_slot, greeted=True)[0]
            fragments = [base, ask] if not confirmation else [confirmation, base, ask]
            return LangGraphTurnResponse(
                reply_text="\n\n".join(fragments),
                reply_fragments=fragments,
                follow_up_suggestion=_follow_up_for_slot(next_slot),
                slot_projection=slots,
                flow_stage="objection_handling",
            )
        fragments = [base, "Se fizer sentido, eu sigo com a simulação a partir do que você já me passou."]
        if confirmation:
            fragments.insert(0, confirmation)
        return LangGraphTurnResponse(
            reply_text="\n\n".join(fragments),
            reply_fragments=fragments,
            follow_up_suggestion="Conduzir para simulacao com base no contexto ja confirmado.",
            slot_projection=slots,
            flow_stage="objection_handling",
        )

    missing_business = _missing_business_slots(slots)
    greeted = _has_previous_assistant_turn(request)
    if missing_business:
        next_slot = runtime.expected_slot or missing_business[0]
        if next_slot not in missing_business:
            next_slot = missing_business[0]
        fragments = _slot_prompt(next_slot, greeted=greeted)
        if confirmation:
            fragments = [confirmation, *fragments]
        return LangGraphTurnResponse(
            reply_text="\n\n".join(fragments),
            reply_fragments=fragments,
            follow_up_suggestion=_follow_up_for_slot(next_slot),
            slot_projection=slots,
            flow_stage="qualification",
        )

    missing_profile = _missing_profile_slots(runtime)
    if missing_profile:
        next_slot = runtime.expected_slot or missing_profile[0]
        if next_slot not in missing_profile:
            next_slot = missing_profile[0]
        fragments = _slot_prompt(next_slot, greeted=True)
        if confirmation and next_slot == "lead_name":
            fragments = [confirmation, *fragments]
        return LangGraphTurnResponse(
            reply_text="\n\n".join(fragments),
            reply_fragments=fragments,
            follow_up_suggestion=_follow_up_for_slot(next_slot),
            slot_projection=slots,
            flow_stage="registration",
        )

    fragments = ["Perfeito. Com esses dados, eu sigo para a simulação."]
    if confirmation:
        fragments.insert(0, confirmation)
    summary = f"Lead pronto para simulacao com valor {slots['asset_value']} e prazo {slots['timeline']}."
    if runtime.summary:
        summary = f"{summary} Contexto consolidado: {runtime.summary}."
    return LangGraphTurnResponse(
        reply_text=fragments[0],
        reply_fragments=fragments,
        follow_up_suggestion=summary,
        slot_projection=slots,
        flow_stage="proposal_ready",
    )


def _run_deterministic_flow(request: LangGraphTurnRequest) -> LangGraphTurnResponse:
    runtime = _build_runtime_context(request)
    runtime = _apply_message_to_slots(runtime, request)
    return _compose_langgraph_reply(runtime, request)


def _compile_graph():
    if StateGraph is None:
        return None

    class RuntimeState(dict):
        pass

    graph = StateGraph(RuntimeState)

    def load_state(state: RuntimeState) -> RuntimeState:
        request = state["request"]
        state["runtime"] = _build_runtime_context(request)
        return state

    def extract_state(state: RuntimeState) -> RuntimeState:
        request = state["request"]
        state["runtime"] = _apply_message_to_slots(state["runtime"], request)
        return state

    def respond_state(state: RuntimeState) -> RuntimeState:
        request = state["request"]
        state["response"] = _compose_langgraph_reply(state["runtime"], request)
        return state

    graph.add_node("load_state", load_state)
    graph.add_node("extract_state", extract_state)
    graph.add_node("respond_state", respond_state)
    graph.add_edge(START, "load_state")
    graph.add_edge("load_state", "extract_state")
    graph.add_edge("extract_state", "respond_state")
    graph.add_edge("respond_state", END)
    return graph.compile()


_compiled_graph = _compile_graph()


async def run_message_through_langgraph(request: LangGraphTurnRequest) -> LangGraphTurnResponse:
    if _compiled_graph is None:
        return _run_deterministic_flow(request)
    result = _compiled_graph.invoke({"request": request})
    return result["response"]
