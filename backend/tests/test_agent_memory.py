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


def test_build_conversation_memory_maps_short_numeric_reply_to_lance_when_prompted() -> None:
    history = [
        {"role": "user", "content": "quero uma moto"},
        {"role": "assistant", "content": "Qual seria o valor aproximado da moto que voce tem em mente?"},
        {"role": "user", "content": "25mil"},
        {"role": "assistant", "content": "Qual o prazo ideal para voce realizar esse consorcio?"},
        {"role": "user", "content": "80 meses"},
        {"role": "assistant", "content": "Voce ja tem em mente qual valor de lance pretende oferecer no consorcio?"},
    ]

    memory = _build_conversation_memory(history, "10mil")

    assert memory["property_type"] == "moto"
    assert memory["property_value"] == "R$ 25mil"
    assert memory["timeline"] == "80 meses"
    assert memory["lance"] == "R$ 10mil"
