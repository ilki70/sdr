from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services import messages


class DummyDB:
    def __init__(self) -> None:
        self.executed: list[object] = []
        self.committed = False

    async def execute(self, statement, *_args, **_kwargs):
        self.executed.append(statement)
        return None

    async def commit(self) -> None:
        self.committed = True


def test_derive_pipeline_status_prefers_persisted_value() -> None:
    conversation = SimpleNamespace(status="open", pipeline_status="handoff")
    lead = SimpleNamespace(lifecycle_status="engaged")

    pipeline_status = messages._derive_pipeline_status(conversation, lead, None)

    assert pipeline_status == "handoff"


def test_derive_next_step_uses_follow_up_suggestion_when_available() -> None:
    latest_message = SimpleNamespace(metadata_json={"follow_up_suggestion": "Confirmar renda e prazo com o lead."})

    next_step = messages._derive_next_step("qualifying", latest_message)

    assert next_step == "Confirmar renda e prazo com o lead."


def test_derive_summary_prefers_persisted_summary() -> None:
    conversation = SimpleNamespace(channel="whatsapp", summary="Lead quer imovel de R$ 400 mil.")
    lead = SimpleNamespace(name="Amaro")

    summary = messages._derive_summary(conversation, lead, None)

    assert summary == "Lead quer imovel de R$ 400 mil."


def test_update_conversation_pipeline_status_persists_explicit_fields(monkeypatch) -> None:
    db = DummyDB()
    conversation = SimpleNamespace(id="conv-1", tenant_id="tenant-1", lead_id="lead-1", summary="Resumo atual")
    lead = SimpleNamespace(id="lead-1", tenant_id="tenant-1", lifecycle_status="engaged", name="Amaro")
    captured: dict[str, object] = {}

    async def fake_get_conversation(_db, tenant_id: str, conversation_id: str):
        assert tenant_id == "tenant-1"
        assert conversation_id == "conv-1"
        return conversation

    async def fake_get_lead(_db, ensured_conversation):
        assert ensured_conversation is conversation
        return lead

    async def fake_persist_pipeline_fields(**kwargs):
        captured.update(kwargs)

    async def fake_get_detail(_db, tenant_id: str, conversation_id: str):
        assert tenant_id == "tenant-1"
        assert conversation_id == "conv-1"
        return SimpleNamespace(conversation=SimpleNamespace(id="conv-1", pipeline_status="handoff"))

    monkeypatch.setattr(messages, "get_conversation_or_none", fake_get_conversation)
    monkeypatch.setattr(messages, "_get_lead_for_conversation", fake_get_lead)
    monkeypatch.setattr(messages, "persist_conversation_pipeline_fields", fake_persist_pipeline_fields)
    monkeypatch.setattr(messages, "get_conversation_detail", fake_get_detail)

    detail = asyncio.run(
        messages.update_conversation_pipeline_status(
            db=db,
            tenant_id="tenant-1",
            conversation_id="conv-1",
            pipeline_status="handoff",
        )
    )

    assert detail is not None
    assert captured["conversation_id"] == "conv-1"
    assert captured["tenant_id"] == "tenant-1"
    assert captured["pipeline_status"] == "handoff"
    assert captured["status"] == "waiting_human"
    assert captured["summary"] == "Resumo atual"
    assert "Assumir atendimento humano" in str(captured["next_step"])
    assert db.committed is True
