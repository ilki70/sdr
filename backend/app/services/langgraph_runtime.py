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
from app.services.conversation_policy import (
    PolicyDecision,
    active_handoff_decision,
    closing_decision,
    detect_closing_signal,
    detect_human_request,
    human_handoff_decision,
    last_assistant_message,
    objection_decision,
    proposal_in_progress_decision,
    proposal_ready_decision,
    qualification_decision,
    registration_decision,
    simulation_delivery_decision,
)
from app.services.conversation_runtime_context import (
    infer_conversation_mode,
    infer_current_topic,
    infer_last_agent_commitment,
    proposal_commitment_state,
)
from app.services.conversation_runtime_state import get_runtime_state
from app.services.conversation_semantics import (
    detect_delivery_channel,
    detect_objection_type,
    detect_pending_user_request,
    detect_simulation_adjustment,
    detect_speech_act,
    extract_budget_monthly,
    follow_up_for_slot,
    has_explicit_name_intro,
    infer_runtime_expected_slot,
    looks_like_name_candidate,
    looks_like_restart_question,
    missing_business_slots,
    missing_profile_slots,
    objection_reply,
    slot_confirmation,
    slot_prompt,
)
from app.services.conversation_turn_interpreter import interpret_turn_semantics
from app.services.conversation_context import (
    ConversationContextSnapshot,
    _amount_matches_timeline,
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
    runtime_metadata: dict[str, Any] = field(default_factory=dict)
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
    current_topic: str = "qualification"
    conversation_mode: str = "collecting"
    last_agent_commitment: str | None = None
    pending_user_request: str | None = None
    speech_act: str = "inform"
    objection_type: str | None = None
    adjustment_type: str | None = None


def _policy_context(request: LangGraphTurnRequest) -> dict[str, Any] | None:
    value = request.metadata.get("policy_context")
    return value if isinstance(value, dict) else None


def _semantic_interpretation(request: LangGraphTurnRequest) -> dict[str, Any]:
    value = request.metadata.get("semantic_interpretation")
    return value if isinstance(value, dict) else {}


def is_langgraph_runtime_enabled() -> bool:
    return bool(settings.langgraph_runtime_enabled)


def _extract_existing_projection(request: LangGraphTurnRequest) -> dict[str, str]:
    metadata = request.lead_metadata or {}
    projection = metadata.get("langgraph_slot_projection")
    if isinstance(projection, dict):
        return {str(key): str(value) for key, value in projection.items() if isinstance(key, str) and isinstance(value, str)}
    return {}


def _extract_existing_runtime_state(request: LangGraphTurnRequest) -> dict[str, str]:
    state = get_runtime_state(request.lead_metadata, source="langgraph")
    return {
        str(key): str(value)
        for key, value in state.items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    }


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


def _build_runtime_context(request: LangGraphTurnRequest) -> RuntimeContext:
    snapshot = _validated_snapshot(request)
    persisted_state = _extract_existing_runtime_state(request)
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
    runtime = RuntimeContext(
        slots=slots,
        expected_slot=expected_slot,
        last_confirmed_slot=last_confirmed_slot,
        missing_profile_fields=_metadata_missing_profile_fields(request),
        summary=summary,
        memory_notes=memory_notes,
        pipeline_status=pipeline_status,
        proposal_commitment_state=proposal_commitment_state(request.conversation_history, pipeline_status),
    )
    runtime.last_agent_commitment = infer_last_agent_commitment(
        request.conversation_history,
        persisted_state.get("last_agent_commitment"),
    )
    runtime.current_topic = infer_current_topic(
        persisted_topic=persisted_state.get("current_topic"),
        pipeline_status=runtime.pipeline_status,
        proposal_commitment_state_value=runtime.proposal_commitment_state,
        missing_profile_fields=runtime.missing_profile_fields,
        slots=runtime.slots,
        expected_slot=runtime.expected_slot,
        history=request.conversation_history,
    )
    runtime.conversation_mode = infer_conversation_mode(
        current_topic=runtime.current_topic,
        last_agent_commitment=runtime.last_agent_commitment,
        persisted_mode=persisted_state.get("conversation_mode"),
    )
    runtime.pending_user_request = persisted_state.get("pending_user_request")
    runtime.speech_act = persisted_state.get("speech_act", "inform")
    return runtime


def _apply_message_to_slots(runtime: RuntimeContext, request: LangGraphTurnRequest) -> RuntimeContext:
    slots = dict(runtime.slots)
    previous_slots = dict(slots)
    text = request.message_text
    expected_slot = runtime.expected_slot or infer_runtime_expected_slot(request.conversation_history)
    semantic = _semantic_interpretation(request)
    semantic_slots = semantic.get("slot_updates") if isinstance(semantic.get("slot_updates"), dict) else {}

    for key, value in semantic_slots.items():
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            slots[key] = value

    lead_name = extract_full_name(text)
    if (
        "lead_name" not in semantic_slots
        and lead_name
        and (expected_slot == "lead_name" or has_explicit_name_intro(text))
        and looks_like_name_candidate(lead_name)
    ):
        slots["lead_name"] = lead_name

    asset_type = _extract_property_type(text)
    if asset_type and "asset_type" not in semantic_slots:
        slots["asset_type"] = asset_type

    target_use_case = _extract_target_use_case(text)
    if target_use_case and "goal" not in semantic_slots:
        slots["goal"] = target_use_case

    extracted_goal = _extract_goal(text)
    if extracted_goal and "goal" not in slots and "goal" not in semantic_slots and expected_slot == "goal":
        slots["goal"] = extracted_goal

    asset_value = _extract_asset_value(text)
    timeline = _extract_timeline(text)
    lance = _extract_lance(text)

    if expected_slot == "lance" and asset_value and not lance and "lance" not in semantic_slots:
        lance = asset_value

    if asset_value and timeline and _amount_matches_timeline(asset_value, timeline):
        asset_value = None
    elif asset_value and lance and asset_value == lance and expected_slot != "asset_value":
        asset_value = None
    elif asset_value and slots.get("lance") and asset_value == slots.get("lance") and expected_slot in {"lead_name", "cpf", "phone"}:
        asset_value = None

    if asset_value and "asset_value" not in semantic_slots and expected_slot not in {"lance", "timeline", "budget_monthly"}:
        slots["asset_value"] = asset_value
    elif (
        asset_value
        and "asset_value" not in semantic_slots
        and expected_slot == "timeline"
        and timeline
        and not _amount_matches_timeline(asset_value, timeline)
    ):
        slots["asset_value"] = asset_value
    if timeline and "timeline" not in semantic_slots:
        slots["timeline"] = timeline
    if lance and "lance" not in semantic_slots:
        slots["lance"] = lance

    budget_monthly = extract_budget_monthly(text, expected_slot)
    if budget_monthly and "budget_monthly" not in semantic_slots:
        slots["budget_monthly"] = budget_monthly

    cpf = extract_cpf(text)
    if cpf and "cpf" not in semantic_slots:
        slots["cpf"] = cpf

    phone = extract_phone(text)
    if phone and "phone" not in semantic_slots:
        slots["phone"] = phone

    delivery_channel = detect_delivery_channel(text)
    if delivery_channel and "preferred_delivery_channel" not in semantic_slots:
        slots["preferred_delivery_channel"] = delivery_channel

    runtime.slots = slots
    runtime.expected_slot = expected_slot
    runtime.new_slots = {
        key: value
        for key, value in slots.items()
        if value and previous_slots.get(key) != value
    }
    return runtime


def _refresh_runtime_semantics(runtime: RuntimeContext, request: LangGraphTurnRequest) -> RuntimeContext:
    semantic = _semantic_interpretation(request)
    runtime.pending_user_request = (
        semantic.get("pending_user_request")
        if isinstance(semantic.get("pending_user_request"), str) and semantic.get("pending_user_request")
        else detect_pending_user_request(
            request.message_text,
            current_topic=runtime.current_topic,
            last_agent_commitment=runtime.last_agent_commitment,
        )
    )
    runtime.speech_act = (
        semantic.get("speech_act")
        if isinstance(semantic.get("speech_act"), str) and semantic.get("speech_act")
        else detect_speech_act(
            request.message_text,
            history=request.conversation_history,
            current_topic=runtime.current_topic,
            last_agent_commitment=runtime.last_agent_commitment,
        )
    )
    runtime.objection_type = (
        semantic.get("objection_type")
        if isinstance(semantic.get("objection_type"), str) and semantic.get("objection_type")
        else detect_objection_type(request.message_text)
    )
    runtime.adjustment_type = (
        semantic.get("adjustment_type")
        if isinstance(semantic.get("adjustment_type"), str) and semantic.get("adjustment_type")
        else detect_simulation_adjustment(request.message_text)
    )

    if runtime.pipeline_status == "handoff":
        runtime.current_topic = "handoff"
        runtime.conversation_mode = "handoff"
        return runtime

    if runtime.speech_act == "closing":
        runtime.current_topic = "closing"
        runtime.conversation_mode = "closing"
        return runtime

    if runtime.pending_user_request == "confirm_simulation":
        runtime.current_topic = "simulation_delivery"
        runtime.conversation_mode = "awaiting_delivery_channel"
    elif runtime.pending_user_request in {"send_simulation", "choose_delivery_channel"} or runtime.last_agent_commitment == "send_simulation":
        runtime.current_topic = "simulation_delivery"
        runtime.conversation_mode = "delivering"
    elif runtime.proposal_commitment_state == "simulacao_em_andamento":
        runtime.current_topic = "simulation_followup"
        runtime.conversation_mode = "advancing_simulation"
    elif runtime.speech_act == "objection":
        runtime.current_topic = "objection_handling"
        runtime.conversation_mode = "handling_objection"
    elif missing_business_slots(runtime.slots):
        runtime.current_topic = "qualification"
        runtime.conversation_mode = "collecting"
    elif missing_profile_slots(missing_profile_fields=runtime.missing_profile_fields, slots=runtime.slots):
        runtime.current_topic = "registration"
        runtime.conversation_mode = "collecting_profile"
    else:
        runtime.current_topic = "proposal_ready"
        runtime.conversation_mode = "ready_to_progress"
    return runtime


def _runtime_state_payload(runtime: RuntimeContext) -> dict[str, str]:
    payload = {
        "current_topic": runtime.current_topic,
        "conversation_mode": runtime.conversation_mode,
        "speech_act": runtime.speech_act,
    }
    if runtime.last_agent_commitment:
        payload["last_agent_commitment"] = runtime.last_agent_commitment
    if runtime.pending_user_request:
        payload["pending_user_request"] = runtime.pending_user_request
    if runtime.slots.get("phone") and runtime.current_topic == "simulation_delivery":
        payload["preferred_delivery_channel"] = "whatsapp"
    return payload


def _has_previous_assistant_turn(request: LangGraphTurnRequest) -> bool:
    return any(item.get("role") == "assistant" for item in request.conversation_history)


def _build_runtime_response(
    decision: PolicyDecision,
    *,
    slots: dict[str, str],
    runtime: RuntimeContext,
) -> LangGraphTurnResponse:
    if decision.updated_last_agent_commitment:
        runtime.last_agent_commitment = decision.updated_last_agent_commitment
    runtime_metadata = _runtime_state_payload(runtime)
    return LangGraphTurnResponse(
        reply_text="\n\n".join(decision.fragments) if len(decision.fragments) > 1 else decision.fragments[0],
        reply_fragments=decision.fragments,
        follow_up_suggestion=decision.follow_up_suggestion,
        handoff_requested=decision.handoff_requested,
        slot_projection=slots,
        runtime_metadata=runtime_metadata,
        flow_stage=decision.flow_stage,
    )


def _compose_langgraph_reply(runtime: RuntimeContext, request: LangGraphTurnRequest) -> LangGraphTurnResponse:
    slots = runtime.slots
    policy_context = _policy_context(request)
    confirmation = slot_confirmation(runtime.new_slots)
    runtime = _refresh_runtime_semantics(runtime, request)
    runtime_metadata = _runtime_state_payload(runtime)
    if detect_closing_signal(request.message_text, request.conversation_history):
        return _build_runtime_response(closing_decision(policy_context), slots=slots, runtime=runtime)
    if detect_human_request(request.message_text):
        return _build_runtime_response(human_handoff_decision(policy_context), slots=slots, runtime=runtime)

    if runtime.pipeline_status == "handoff":
        return _build_runtime_response(active_handoff_decision(policy_context), slots=slots, runtime=runtime)

    if runtime.current_topic == "simulation_delivery":
        decision = simulation_delivery_decision(
            slots=runtime.slots,
            pending_user_request=runtime.pending_user_request,
            last_agent_commitment=runtime.last_agent_commitment,
            message_text=request.message_text,
        )
        if decision:
            return _build_runtime_response(decision, slots=slots, runtime=runtime)

    if runtime.proposal_commitment_state == "simulacao_em_andamento":
        missing_profile = missing_profile_slots(
            missing_profile_fields=runtime.missing_profile_fields,
            slots=runtime.slots,
        )
        next_slot = missing_profile[0] if missing_profile else None
        decision = proposal_in_progress_decision(
            slots=runtime.slots,
            adjustment_type=runtime.adjustment_type,
            budget_follow_up_text=follow_up_for_slot("budget_monthly", policy_context),
            missing_profile_prompt=slot_prompt(next_slot, greeted=True, policy_context=policy_context)[0] if next_slot else None,
            missing_profile_follow_up=follow_up_for_slot(next_slot, policy_context) if next_slot else None,
            restart_question_detected=looks_like_restart_question(request.message_text),
        )
        if decision:
            return _build_runtime_response(decision, slots=slots, runtime=runtime)

    objection_type = runtime.objection_type
    if objection_type:
        missing_business = missing_business_slots(slots)
        base = objection_reply(objection_type, runtime.slots, policy_context)
        if missing_business:
            next_slot = runtime.expected_slot or missing_business[0]
            if next_slot not in missing_business:
                next_slot = missing_business[0]
            return _build_runtime_response(
                objection_decision(
                    base_reply=base,
                    confirmation=confirmation,
                    next_prompt=slot_prompt(next_slot, greeted=True, policy_context=policy_context)[0],
                    next_follow_up=follow_up_for_slot(next_slot, policy_context),
                ),
                slots=slots,
                runtime=runtime,
            )
        profile_missing = missing_profile_slots(
            missing_profile_fields=runtime.missing_profile_fields,
            slots=runtime.slots,
        )
        if profile_missing:
            next_slot = profile_missing[0]
            return _build_runtime_response(
                objection_decision(
                    base_reply=base,
                    confirmation=confirmation,
                    next_prompt=slot_prompt(next_slot, greeted=True, policy_context=policy_context)[0],
                    next_follow_up=follow_up_for_slot(next_slot, policy_context),
                ),
                slots=slots,
                runtime=runtime,
            )
        return _build_runtime_response(
            objection_decision(
                base_reply=base,
                confirmation=confirmation,
                next_prompt=None,
                next_follow_up=None,
            ),
            slots=slots,
            runtime=runtime,
        )

    missing_business = missing_business_slots(slots)
    greeted = _has_previous_assistant_turn(request)
    if missing_business:
        next_slot = runtime.expected_slot or missing_business[0]
        if next_slot not in missing_business:
            next_slot = missing_business[0]
        return _build_runtime_response(
            qualification_decision(
                prompt_fragments=slot_prompt(next_slot, greeted=greeted, policy_context=policy_context),
                follow_up_suggestion=follow_up_for_slot(next_slot, policy_context),
                confirmation=confirmation,
            ),
            slots=slots,
            runtime=runtime,
        )

    missing_profile = missing_profile_slots(
        missing_profile_fields=runtime.missing_profile_fields,
        slots=runtime.slots,
    )
    if missing_profile:
        next_slot = runtime.expected_slot or missing_profile[0]
        if next_slot not in missing_profile:
            next_slot = missing_profile[0]
        return _build_runtime_response(
            registration_decision(
                prompt_fragments=slot_prompt(next_slot, greeted=True, policy_context=policy_context),
                follow_up_suggestion=follow_up_for_slot(next_slot, policy_context),
                confirmation=confirmation,
                next_slot=next_slot,
            ),
            slots=slots,
            runtime=runtime,
        )

    summary = f"Lead pronto para simulacao com valor {slots['asset_value']} e prazo {slots['timeline']}."
    if runtime.summary:
        summary = f"{summary} Contexto consolidado: {runtime.summary}."
    return _build_runtime_response(
        proposal_ready_decision(
            slots=slots,
            confirmation=confirmation,
            summary=summary,
        ),
        slots=slots,
        runtime=runtime,
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
    seed_runtime = _build_runtime_context(request)
    semantic_interpretation = await interpret_turn_semantics(
        message_text=request.message_text,
        history=request.conversation_history,
        known_slots=seed_runtime.slots,
        current_topic=seed_runtime.current_topic,
        last_agent_commitment=seed_runtime.last_agent_commitment,
        expected_slot=seed_runtime.expected_slot or infer_runtime_expected_slot(request.conversation_history),
    )
    enriched_request = LangGraphTurnRequest(
        tenant_id=request.tenant_id,
        conversation_id=request.conversation_id,
        message_text=request.message_text,
        conversation_history=list(request.conversation_history),
        lead_name=request.lead_name,
        lead_phone=request.lead_phone,
        lead_cpf=request.lead_cpf,
        lead_metadata=dict(request.lead_metadata),
        conversation_context=dict(request.conversation_context),
        channel=request.channel,
        metadata={**request.metadata, "semantic_interpretation": semantic_interpretation},
    )
    if _compiled_graph is None:
        return _run_deterministic_flow(enriched_request)
    result = _compiled_graph.invoke({"request": enriched_request})
    return result["response"]
