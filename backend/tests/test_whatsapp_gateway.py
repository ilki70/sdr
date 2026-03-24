from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.schemas.whatsapp import WhatsAppInboundRequest
from app.services import conversation_context
from app.services import whatsapp_gateway


class DummyDB:
    async def execute(self, *_args, **_kwargs):
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


def test_process_whatsapp_inbound_uses_message_id_as_external_message_id(monkeypatch) -> None:
    integration = SimpleNamespace(id="integration-1", webhook_secret_enc=b"secret", agent_id="agent-1")
    lead = SimpleNamespace(id="lead-1")
    conversation = SimpleNamespace(id="conv-1", agent_id="agent-1")
    saved_messages: list[dict] = []

    async def fake_get_integration(_db, tenant_id: str):
        assert tenant_id == "tenant-1"
        return integration

    async def fake_duplicate_execute(*_args, **_kwargs):
        class Result:
            def scalar_one_or_none(self):
                return None

        return Result()

    async def fake_ensure_lead(_db, payload, phone: str):
        assert payload.sender_id == "5511999999999@s.whatsapp.net"
        assert phone == "5511999999999"
        return lead

    async def fake_ensure_conversation(_db, payload, ensured_lead, ensured_integration):
        assert ensured_lead is lead
        assert ensured_integration is integration
        assert payload.chat_id == "5511888888888@s.whatsapp.net"
        return conversation

    async def fake_refresh_context(*_args, **_kwargs):
        return SimpleNamespace(model_dump=lambda: {"summary": "ctx"})

    async def fake_summarize_media(*_args, **_kwargs):
        return []

    async def fake_load_cached_context(*_args, **_kwargs):
        return None

    async def fake_store_cached_context(*_args, **_kwargs):
        return None

    async def fake_load_history(*_args, **_kwargs):
        return []

    async def fake_save_message(**kwargs):
        saved_messages.append(kwargs)
        return SimpleNamespace()

    async def fake_run_sales_agent(state):
        state.draft_reply = "ok"
        state.reply_fragments = ["ok"]
        state.follow_up_suggestion = None
        state.intent = "generic"
        state.confidence_score = 0.9
        return state

    monkeypatch.setattr(whatsapp_gateway.settings, "whatsapp_gateway_secret", "secret")
    monkeypatch.setattr(whatsapp_gateway, "get_whatsapp_integration_or_none", fake_get_integration)
    monkeypatch.setattr(whatsapp_gateway, "summarize_media_attachments", fake_summarize_media)
    monkeypatch.setattr(whatsapp_gateway, "load_cached_conversation_context", fake_load_cached_context)
    monkeypatch.setattr(whatsapp_gateway, "refresh_conversation_context_from_db", fake_refresh_context)
    monkeypatch.setattr(
        whatsapp_gateway,
        "resolve_fragmented_inbound_text",
        lambda snapshot, text: (snapshot, text, False),
    )
    monkeypatch.setattr(whatsapp_gateway, "store_cached_conversation_context", fake_store_cached_context)
    monkeypatch.setattr(whatsapp_gateway, "_ensure_whatsapp_lead", fake_ensure_lead)
    monkeypatch.setattr(whatsapp_gateway, "_ensure_whatsapp_conversation", fake_ensure_conversation)
    monkeypatch.setattr(whatsapp_gateway, "_load_history_for_agent", fake_load_history)
    monkeypatch.setattr(whatsapp_gateway, "save_message", fake_save_message)
    monkeypatch.setattr(whatsapp_gateway, "run_sales_agent", fake_run_sales_agent)

    db = DummyDB()
    monkeypatch.setattr(db, "execute", fake_duplicate_execute)

    payload = WhatsAppInboundRequest(
        tenant_id="tenant-1",
        integration_id="integration-1",
        chat_id="5511888888888@s.whatsapp.net",
        sender_id="5511999999999@s.whatsapp.net",
        sender_name="Lead Teste",
        message_id="wamid-123",
        message_text="ola",
        push_name="Lead Teste",
        attachments=[],
    )

    response = asyncio.run(whatsapp_gateway.process_whatsapp_inbound(db, payload))

    assert response.reply_text == "ok"
    assert saved_messages[0]["external_message_id"] == "wamid-123"
    assert saved_messages[0]["direction"] == "inbound"


def test_process_whatsapp_inbound_survives_redis_cache_outage(monkeypatch) -> None:
    integration = SimpleNamespace(id="integration-1", webhook_secret_enc=b"secret", agent_id="agent-1")
    lead = SimpleNamespace(id="lead-1")
    conversation = SimpleNamespace(id="conv-1", agent_id="agent-1")
    saved_messages: list[dict] = []

    class FailingRedis:
        async def get(self, _key: str):
            raise ConnectionError("redis unavailable")

        async def setex(self, _key: str, _ttl: int, _value: str):
            raise ConnectionError("redis unavailable")

    async def fake_get_integration(_db, tenant_id: str):
        assert tenant_id == "tenant-1"
        return integration

    async def fake_duplicate_execute(*_args, **_kwargs):
        class Result:
            def scalar_one_or_none(self):
                return None

        return Result()

    async def fake_ensure_lead(_db, payload, phone: str):
        return lead

    async def fake_ensure_conversation(_db, payload, ensured_lead, ensured_integration):
        return conversation

    async def fake_refresh_context(*_args, **_kwargs):
        return SimpleNamespace(model_dump=lambda: {"summary": "ctx"})

    async def fake_summarize_media(*_args, **_kwargs):
        return []

    async def fake_load_history(*_args, **_kwargs):
        return []

    async def fake_save_message(**kwargs):
        saved_messages.append(kwargs)
        return SimpleNamespace()

    async def fake_run_sales_agent(state):
        state.draft_reply = "ok"
        state.reply_fragments = []
        state.follow_up_suggestion = None
        state.intent = "generic"
        state.confidence_score = 0.9
        return state

    monkeypatch.setattr(whatsapp_gateway.settings, "whatsapp_gateway_secret", "secret")
    monkeypatch.setattr(conversation_context, "get_redis_client", lambda: FailingRedis())
    monkeypatch.setattr(whatsapp_gateway, "get_whatsapp_integration_or_none", fake_get_integration)
    monkeypatch.setattr(whatsapp_gateway, "summarize_media_attachments", fake_summarize_media)
    monkeypatch.setattr(whatsapp_gateway, "_ensure_whatsapp_lead", fake_ensure_lead)
    monkeypatch.setattr(whatsapp_gateway, "_ensure_whatsapp_conversation", fake_ensure_conversation)
    monkeypatch.setattr(whatsapp_gateway, "refresh_conversation_context_from_db", fake_refresh_context)
    monkeypatch.setattr(whatsapp_gateway, "save_message", fake_save_message)
    monkeypatch.setattr(whatsapp_gateway, "_load_history_for_agent", fake_load_history)
    monkeypatch.setattr(whatsapp_gateway, "run_sales_agent", fake_run_sales_agent)

    db = DummyDB()
    monkeypatch.setattr(db, "execute", fake_duplicate_execute)

    payload = WhatsAppInboundRequest(
        tenant_id="tenant-1",
        integration_id="integration-1",
        chat_id="5511888888888@s.whatsapp.net",
        sender_id="5511999999999@s.whatsapp.net",
        sender_name="Lead Teste",
        message_id="wamid-456",
        message_text="ola",
        push_name="Lead Teste",
        attachments=[],
    )

    response = asyncio.run(whatsapp_gateway.process_whatsapp_inbound(db, payload))

    assert response.reply_text == "ok"
    assert saved_messages[0]["external_message_id"] == "wamid-456"
