from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.api.v1.messages import routes
from app.schemas.messages import MessageSimulateRequest
from app.services import runtime_router


class DummyDB:
    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


def test_apply_runtime_slot_projection_updates_lead_fields() -> None:
    lead = SimpleNamespace(name=None, phone=None, cpf=None, metadata_json={})

    runtime_router.apply_runtime_slot_projection(
        lead,
        {
            "lead_name": "Ilki Amaro",
            "phone": "12988162249",
            "cpf": "002.752.307-16",
            "asset_type": "imovel",
        },
        source="langgraph",
    )

    assert lead.name == "Ilki Amaro"
    assert lead.phone == "12988162249"
    assert lead.cpf == "002.752.307-16"
    assert lead.metadata_json["langgraph_slot_projection"]["asset_type"] == "imovel"


def test_run_lab_runtime_uses_langgraph_when_feature_flag_is_enabled(monkeypatch) -> None:
    db = DummyDB()
    context = SimpleNamespace(tenant_id="tenant-1")
    payload = MessageSimulateRequest(message_text="quero um imovel", channel="lab", attachments=[])

    prepared_state = SimpleNamespace(
        message_text="quero um imovel",
        media_context=[],
        conversation_history=[],
        conversation_id="conv-1",
    )
    conversation = SimpleNamespace(id="conv-1", agent_id="agent-1", lead_id="lead-1")
    lead = SimpleNamespace(id="lead-1", name=None, phone=None, cpf=None, metadata_json={})

    async def fake_prepare_state(_db, _context, _payload):
        return prepared_state, "conv-1"

    async def fake_ensure_conversation(**_kwargs):
        return conversation

    async def fake_get_lead(_db, _conversation):
        return lead

    async def fake_run_configured_sales_runtime(**kwargs):
        assert kwargs["state"].conversation_id == "conv-1"
        kwargs["lead"].name = "Ilki"
        return SimpleNamespace(
            message_text=kwargs["state"].message_text,
            draft_reply="Você está buscando imóvel ou veículo?",
            reply_fragments=["Você está buscando imóvel ou veículo?"],
            follow_up_suggestion="Capturar asset_type.",
            handoff_requested=False,
            slot_projection={"lead_name": "Ilki"},
            intent="langgraph_flow",
            confidence_score=1.0,
            media_context=[],
        ), "langgraph"

    monkeypatch.setattr(routes, "_prepare_state", fake_prepare_state)
    monkeypatch.setattr(routes, "ensure_lab_conversation", fake_ensure_conversation)
    monkeypatch.setattr(routes, "get_lead_for_conversation", fake_get_lead)
    monkeypatch.setattr(routes, "run_configured_sales_runtime", fake_run_configured_sales_runtime)

    state, ensured_conversation, model_name = asyncio.run(routes._run_lab_runtime(db, context, payload))

    assert ensured_conversation is conversation
    assert model_name == "langgraph"
    assert state.intent == "langgraph_flow"
    assert state.reply_fragments == ["Você está buscando imóvel ou veículo?"]
    assert lead.name == "Ilki"
