import asyncio

from app.agents.nodes import _build_conversation_memory
from app.agents.nodes import _build_initial_opening_fragments
from app.agents.nodes import _limit_emojis
from app.agents.nodes import classify_intent
from app.agents.nodes import compose_reply
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

    assert memory["asset_type"] == "casa"
    assert memory["asset_value"] == "R$ 400mil"
    assert memory["timeline"] == "6 meses"
    assert memory["lance"] == "R$ 200mil"
    assert "goal=uns 500mil..quero comprar a casa em até 6 meses" in memory["summary"]


def test_build_conversation_memory_ignores_lance_as_property_value() -> None:
    history = [{"role": "user", "content": "tenho 200mil para dar de lance"}]

    memory = _build_conversation_memory(history, "qual o prazo?")

    assert memory["asset_type"] == "nao informado"
    assert memory["asset_value"] == "nao informado"
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

    assert memory["asset_type"] == "moto"
    assert memory["asset_value"] == "R$ 25mil"
    assert memory["timeline"] == "80 meses"
    assert memory["lance"] == "R$ 10mil"
    assert memory["current_question_slot"] == "nao informado"
    assert memory["last_confirmed_slot"] == "lance"


def test_build_initial_opening_fragments_are_fixed() -> None:
    assert _build_initial_opening_fragments() == [
        "Olá! Aqui é da Orfi Consórcios 👋",
        "Me conta: você está buscando imóvel ou veículo?",
    ]


def test_compose_reply_uses_fixed_opening_for_first_touch() -> None:
    state = AgentState(tenant_id="tenant-1", message_text="oi")

    result = asyncio.run(compose_reply(state))

    assert result.reply_fragments == [
        "Olá! Aqui é da Orfi Consórcios 👋",
        "Me conta: você está buscando imóvel ou veículo?",
    ]
    assert result.draft_reply == "Olá! Aqui é da Orfi Consórcios 👋\n\nMe conta: você está buscando imóvel ou veículo?"
    assert result.follow_up_suggestion == "Perguntar se o lead busca imóvel ou veículo."
    assert result.next_action == "send"


def test_limit_emojis_keeps_reply_discreet() -> None:
    text = _limit_emojis("Oi 👋 tudo bem ✅? 🚀", max_emojis=1)

    assert "👋" in text
    assert "✅" not in text
    assert "🚀" not in text
