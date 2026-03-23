import asyncio

from app.agents.nodes import _build_conversation_memory
from app.agents.nodes import classify_intent
from app.agents.state import AgentState


def test_build_conversation_memory_tracks_latest_property_details() -> None:
    history = [
        {"role": "user", "content": "quero ver para uma casa"},
        {"role": "assistant", "content": "Ótimo!"},
        {"role": "user", "content": "uns 500mil..quero comprar a casa em até 6 meses"},
        {"role": "assistant", "content": "Entendi."},
        {"role": "user", "content": "tenho 200mil para dar de lance"},
        {"role": "assistant", "content": "Perfeito."},
    ]

    memory = _build_conversation_memory(history, "400mil")

    assert memory["property_type"] == "casa"
    assert memory["property_value"] == "R$ 400mil"
    assert memory["timeline"] == "6 meses"
    assert memory["lance"] == "R$ 200mil"
    assert "quero comprar a casa em até 6 meses" in memory["summary"]


def test_build_conversation_memory_ignores_lance_as_property_value() -> None:
    history = [{"role": "user", "content": "tenho 200mil para dar de lance"}]

    memory = _build_conversation_memory(history, "qual o prazo?")

    assert memory["property_type"] == "nao informado"
    assert memory["property_value"] == "nao informado"
    assert memory["lance"] == "R$ 200mil"


def test_classify_intent_detects_investment_question() -> None:
    state = AgentState(tenant_id="tenant-1", message_text="quero entender se vale a pena investir em consorcio")

    classified = asyncio.run(classify_intent(state))

    assert classified.intent == "investment"
