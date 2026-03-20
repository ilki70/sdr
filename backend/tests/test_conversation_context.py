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


def test_build_conversation_context_snapshot_tracks_property_slots() -> None:
    messages = [
        {"role": "user", "content": "quero ver para uma casa"},
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

    assert snapshot.property_type == "casa"
    assert snapshot.property_value == "R$ 400mil"
    assert snapshot.timeline == "6 meses"
    assert snapshot.lance == "R$ 200mil"
    assert snapshot.last_intent == "property"
    assert "tipo_de_imovel=casa" in snapshot.summary


def test_context_cache_roundtrip(monkeypatch) -> None:
    fake = FakeRedis()
    monkeypatch.setattr(conversation_context, "get_redis_client", lambda: fake)

    snapshot = conversation_context.ConversationContextSnapshot(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        property_type="casa",
        property_value="R$ 400mil",
        timeline="6 meses",
        lance="R$ 200mil",
        last_intent="property",
        summary="tipo_de_imovel=casa; valor_do_imovel=R$ 400mil; prazo=6 meses; lance=R$ 200mil",
        turn_count=3,
    )

    async def roundtrip() -> conversation_context.ConversationContextSnapshot | None:
        await conversation_context.store_cached_conversation_context(snapshot)
        return await conversation_context.load_cached_conversation_context("tenant-1", "conv-1")

    loaded = asyncio.run(roundtrip())

    assert loaded is not None
    assert loaded.property_value == "R$ 400mil"
    assert fake.ttls[conversation_context.conversation_context_cache_key("tenant-1", "conv-1")] >= 60


def test_infer_turn_intent_detects_property_and_lance() -> None:
    assert conversation_context.infer_turn_intent("quero ver para uma casa") == "property"
    assert conversation_context.infer_turn_intent("tenho 200mil para dar de lance") == "lance"


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
