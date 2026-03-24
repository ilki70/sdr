from app.services.conversation_runtime_state import get_runtime_state, store_runtime_state


def test_store_runtime_state_persists_generic_and_scoped_keys() -> None:
    metadata = store_runtime_state(
        {"source": "agent-lab"},
        {"current_topic": "qualification", "conversation_mode": "collecting"},
        source="langgraph",
    )

    assert metadata["conversation_runtime_state"]["current_topic"] == "qualification"
    assert metadata["langgraph_runtime_state"]["conversation_mode"] == "collecting"


def test_get_runtime_state_prefers_scoped_value() -> None:
    metadata = {
        "conversation_runtime_state": {"current_topic": "generic"},
        "langgraph_runtime_state": {"current_topic": "scoped"},
    }

    assert get_runtime_state(metadata, source="langgraph") == {"current_topic": "scoped"}


def test_get_runtime_state_falls_back_to_generic_value() -> None:
    metadata = {
        "conversation_runtime_state": {"current_topic": "generic"},
    }

    assert get_runtime_state(metadata, source="langgraph") == {"current_topic": "generic"}
