from __future__ import annotations

from app.services.conversation_policy import last_assistant_message
from app.services.conversation_semantics import detect_objection_type, missing_profile_slots


def proposal_commitment_state(history: list[dict[str, str]], pipeline_status: str | None) -> str:
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


def infer_last_agent_commitment(history: list[dict[str, str]], persisted_value: str | None) -> str | None:
    if persisted_value:
        return persisted_value
    last_assistant = last_assistant_message(history).lower()
    if any(token in last_assistant for token in ("vou enviar a simulação", "vou enviar a simulacao", "me envie", "enviar pelo whatsapp")):
        return "send_simulation"
    if any(token in last_assistant for token in ("vou preparar a simulação", "vou preparar a simulacao", "sigo com a simulação", "sigo com a simulacao")):
        return "prepare_simulation"
    if any(token in last_assistant for token in ("consultor humano", "atendimento humano")):
        return "handoff"
    return None


def infer_current_topic(
    *,
    persisted_topic: str | None,
    pipeline_status: str | None,
    proposal_commitment_state_value: str,
    missing_profile_fields: list[str],
    slots: dict[str, str],
    expected_slot: str | None,
    history: list[dict[str, str]],
) -> str:
    if persisted_topic:
        return persisted_topic
    if pipeline_status == "handoff":
        return "handoff"
    if proposal_commitment_state_value == "simulacao_em_andamento":
        if missing_profile_fields or missing_profile_slots(
            missing_profile_fields=missing_profile_fields,
            slots=slots,
        ):
            return "registration"
        return "simulation_delivery"
    if expected_slot in {"cpf", "phone", "lead_name"}:
        return "registration"
    if detect_objection_type(last_assistant_message(history)):
        return "objection_handling"
    return "qualification"


def infer_conversation_mode(
    *,
    current_topic: str,
    last_agent_commitment: str | None,
    persisted_mode: str | None,
) -> str:
    if persisted_mode:
        return persisted_mode
    if current_topic == "closing":
        return "closing"
    if current_topic == "handoff":
        return "handoff"
    if current_topic == "simulation_delivery" and last_agent_commitment == "send_simulation":
        return "delivering"
    if current_topic == "registration":
        return "collecting_profile"
    if current_topic == "objection_handling":
        return "handling_objection"
    return "collecting"
