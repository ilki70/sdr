from __future__ import annotations

import asyncio

from app.services import conversation_context


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttls[key] = ttl


class FailingRedis:
    async def get(self, _key: str) -> str | None:
        raise ConnectionError("redis unavailable")

    async def setex(self, _key: str, _ttl: int, _value: str) -> None:
        raise ConnectionError("redis unavailable")


def test_build_conversation_context_snapshot_tracks_property_slots() -> None:
    messages = [
        {"role": "assistant", "content": "Posso saber seu nome?"},
        {"role": "user", "content": "Ilki"},
        {"role": "assistant", "content": "Qual e o seu objetivo com o consorcio?"},
        {"role": "user", "content": "quero ver para uma casa para investir"},
        {"role": "assistant", "content": "Ótimo."},
        {"role": "user", "content": "uns 500mil..quero comprar a casa em até 6 meses"},
        {"role": "assistant", "content": "Entendi."},
        {"role": "user", "content": "tenho 200mil para dar de lance"},
        {"role": "user", "content": "400mil"},
    ]

    snapshot = conversation_context.build_conversation_context_snapshot(
        messages,
        tenant_id="tenant-1",
        conversation_id="conv-1",
        last_intent="property",
    )

    assert snapshot.lead_name == "Ilki"
    assert snapshot.asset_type == "casa"
    assert snapshot.asset_value == "R$ 400mil"
    assert snapshot.target_use_case == "investimento"
    assert snapshot.timeline == "6 meses"
    assert snapshot.lance == "R$ 200mil"
    assert snapshot.last_intent == "property"
    assert snapshot.extracted_slots["asset_type"] == "casa"
    assert "lead_name=Ilki" in snapshot.summary


def test_context_cache_roundtrip(monkeypatch) -> None:
    fake = FakeRedis()
    monkeypatch.setattr(conversation_context, "get_redis_client", lambda: fake)

    snapshot = conversation_context.ConversationContextSnapshot(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        lead_name="Ilki",
        asset_type="casa",
        asset_value="R$ 400mil",
        target_use_case="investimento",
        goal="quero investir em uma casa",
        timeline="6 meses",
        lance="R$ 200mil",
        last_intent="property",
        current_question_slot="nao informado",
        last_confirmed_slot="lance",
        extracted_slots={"lead_name": "Ilki", "asset_type": "casa", "asset_value": "R$ 400mil", "timeline": "6 meses", "lance": "R$ 200mil"},
        summary="lead_name=Ilki; asset_type=casa; asset_value=R$ 400mil; prazo=6 meses; lance=R$ 200mil",
        turn_count=3,
    )

    async def roundtrip() -> conversation_context.ConversationContextSnapshot | None:
        await conversation_context.store_cached_conversation_context(snapshot)
        return await conversation_context.load_cached_conversation_context("tenant-1", "conv-1")

    loaded = asyncio.run(roundtrip())

    assert loaded is not None
    assert loaded.asset_value == "R$ 400mil"
    assert fake.ttls[conversation_context.conversation_context_cache_key("tenant-1", "conv-1")] >= 60


def test_format_conversation_context_includes_long_term_memory_notes() -> None:
    snapshot = conversation_context.ConversationContextSnapshot(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        lead_name="Ilki",
        asset_type="casa",
        asset_value="R$ 400mil",
        timeline="6 meses",
        memory_notes=[
            "lead_name=Ilki",
            "asset_type=casa",
            "asset_value=R$ 400mil",
            "prazo=6 meses",
            "ultima_intencao=property",
        ],
    )

    prompt_block = conversation_context.format_conversation_context_for_prompt(snapshot)

    assert "memoria_longa=lead_name=Ilki | asset_type=casa | asset_value=R$ 400mil | prazo=6 meses | ultima_intencao=property" in prompt_block


def test_context_cache_is_best_effort_when_redis_is_down(monkeypatch) -> None:
    monkeypatch.setattr(conversation_context, "get_redis_client", lambda: FailingRedis())

    snapshot = conversation_context.ConversationContextSnapshot(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        lead_name="Ilki",
    )

    async def roundtrip() -> conversation_context.ConversationContextSnapshot | None:
        stored = await conversation_context.store_cached_conversation_context(snapshot)
        loaded = await conversation_context.load_cached_conversation_context("tenant-1", "conv-1")
        return stored if loaded is None else loaded

    loaded = asyncio.run(roundtrip())

    assert loaded is not None
    assert loaded.lead_name == "Ilki"


def test_infer_turn_intent_detects_property_lance_and_investment() -> None:
    assert conversation_context.infer_turn_intent("quero ver para uma casa") == "property"
    assert conversation_context.infer_turn_intent("tenho 200mil para dar de lance") == "lance"
    assert conversation_context.infer_turn_intent("quero entender se vale a pena investir em consorcio") == "investment"


def test_fragment_buffer_roundtrip() -> None:
    snapshot = conversation_context.ConversationContextSnapshot(
        tenant_id="tenant-1",
        conversation_id="conv-1",
    )

    snapshot, resolved, deferred = conversation_context.resolve_fragmented_inbound_text(snapshot, "quero ver")
    assert deferred is True
    assert resolved == ""
    assert snapshot.pending_fragment_text == "quero ver"

    snapshot, resolved, deferred = conversation_context.resolve_fragmented_inbound_text(snapshot, "para uma casa")
    assert deferred is False
    assert resolved == "quero ver para uma casa"
    assert snapshot.pending_fragment_text == ""

    assert conversation_context.is_fragment_like("quero ver")
    assert not conversation_context.is_fragment_like("quero ver para uma casa")
    assert not conversation_context.is_fragment_like("oi")
    assert not conversation_context.is_fragment_like("casa")


def test_build_conversation_context_snapshot_maps_short_numeric_reply_to_lance_when_prompted() -> None:
    messages = [
        {"role": "user", "content": "quero uma moto"},
        {"role": "assistant", "content": "Qual seria o valor aproximado da moto que voce tem em mente?"},
        {"role": "user", "content": "25mil"},
        {"role": "assistant", "content": "Qual o prazo ideal para voce realizar esse consorcio?"},
        {"role": "user", "content": "80 meses"},
        {"role": "assistant", "content": "Voce ja tem em mente qual valor de lance pretende oferecer no consorcio?"},
        {"role": "user", "content": "10mil"},
    ]

    snapshot = conversation_context.build_conversation_context_snapshot(
        messages,
        tenant_id="tenant-1",
        conversation_id="conv-2",
        last_intent="property",
    )

    assert snapshot.asset_type == "moto"
    assert snapshot.asset_value == "R$ 25mil"
    assert snapshot.timeline == "80 meses"
    assert snapshot.lance == "R$ 10mil"
    assert snapshot.last_confirmed_slot == "lance"
    assert snapshot.current_question_slot == "nao informado"


def test_build_conversation_context_snapshot_keeps_asset_value_and_lance_from_same_message() -> None:
    messages = [
        {"role": "assistant", "content": "Me conta: voce esta buscando imovel ou veiculo?"},
        {
            "role": "user",
            "content": "quero uma simulacao de imovel valor de 500mil, prazo 180 meses, lance de 100mil. meu nome e ilki amaro junior e cpf 00275230716",
        },
    ]

    snapshot = conversation_context.build_conversation_context_snapshot(
        messages,
        tenant_id="tenant-1",
        conversation_id="conv-3",
        last_intent="property",
    )

    assert snapshot.asset_type == "imovel"
    assert snapshot.asset_value == "R$ 500mil"
    assert snapshot.timeline == "180 meses"
    assert snapshot.lance == "R$ 100mil"
    assert snapshot.lead_name == "Ilki Amaro Junior"
