from app.services.conversation_runtime_context import (
    infer_conversation_mode,
    infer_current_topic,
    infer_last_agent_commitment,
    proposal_commitment_state,
)


def test_proposal_commitment_state_detects_scheduled_pipeline() -> None:
    assert proposal_commitment_state([], "scheduled") == "simulacao_em_andamento"


def test_proposal_commitment_state_detects_simulation_commitment_from_history() -> None:
    history = [{"role": "assistant", "content": "Perfeito. Com esses dados, eu sigo para a simulação."}]

    assert proposal_commitment_state(history, None) == "simulacao_em_andamento"


def test_infer_last_agent_commitment_prefers_persisted_value() -> None:
    assert infer_last_agent_commitment([], "send_simulation") == "send_simulation"


def test_infer_last_agent_commitment_reads_last_assistant_message() -> None:
    history = [{"role": "assistant", "content": "Vou enviar a simulação pelo WhatsApp."}]

    assert infer_last_agent_commitment(history, None) == "send_simulation"


def test_infer_current_topic_returns_registration_when_profile_is_missing_during_simulation() -> None:
    topic = infer_current_topic(
        persisted_topic=None,
        pipeline_status="scheduled",
        proposal_commitment_state_value="simulacao_em_andamento",
        missing_profile_fields=["cpf"],
        slots={"lead_name": "Ilki"},
        expected_slot=None,
        history=[],
    )

    assert topic == "registration"


def test_infer_current_topic_returns_objection_handling_from_last_assistant_message() -> None:
    topic = infer_current_topic(
        persisted_topic=None,
        pipeline_status=None,
        proposal_commitment_state_value="nenhum",
        missing_profile_fields=[],
        slots={"asset_type": "imovel"},
        expected_slot=None,
        history=[{"role": "assistant", "content": "Tenho receio da taxa, como isso funciona?"}],
    )

    assert topic == "objection_handling"


def test_infer_conversation_mode_prefers_persisted_value() -> None:
    mode = infer_conversation_mode(
        current_topic="qualification",
        last_agent_commitment=None,
        persisted_mode="collecting_profile",
    )

    assert mode == "collecting_profile"


def test_infer_conversation_mode_maps_simulation_delivery_to_delivering() -> None:
    mode = infer_conversation_mode(
        current_topic="simulation_delivery",
        last_agent_commitment="send_simulation",
        persisted_mode=None,
    )

    assert mode == "delivering"
