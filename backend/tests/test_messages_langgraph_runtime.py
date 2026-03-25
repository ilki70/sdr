from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.agents.state import AgentState
from app.api.v1.messages import routes
from app.schemas.messages import MessageSimulateRequest
from app.services import runtime_router
from app.services.langgraph_runtime import LangGraphTurnResponse


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
        runtime_metadata={
            "current_topic": "qualification",
            "conversation_mode": "collecting",
        },
    )

    assert lead.name == "Ilki Amaro"
    assert lead.phone == "12988162249"
    assert lead.cpf == "002.752.307-16"
    assert lead.metadata_json["langgraph_slot_projection"]["asset_type"] == "imovel"
    assert lead.metadata_json["conversation_runtime_state"]["current_topic"] == "qualification"
    assert lead.metadata_json["langgraph_runtime_state"]["current_topic"] == "qualification"


def test_runtime_router_get_runtime_state_uses_central_helper() -> None:
    lead = SimpleNamespace(
        metadata_json={
            "conversation_runtime_state": {"current_topic": "generic"},
            "langgraph_runtime_state": {"current_topic": "scoped"},
        }
    )

    assert runtime_router.get_runtime_state(lead, source="langgraph") == {"current_topic": "scoped"}


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


def test_runtime_router_formats_long_whatsapp_reply(monkeypatch) -> None:
    lead = SimpleNamespace(name=None, phone=None, cpf=None, metadata_json={})
    long_fragment = (
        "Perfeito. Vou seguir com a simulação usando o contexto que você já me passou, "
        "sem reiniciar a conversa, e se surgir qualquer ajuste no valor, no prazo ou na parcela "
        "você pode me chamar por aqui que eu continuo exatamente deste ponto."
    )
    state = AgentState(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        message_text="quero um imovel",
        conversation_history=[],
        media_context=[],
    )

    async def fake_run_message_through_langgraph(_request):
        return LangGraphTurnResponse(
            reply_text=long_fragment,
            reply_fragments=[long_fragment],
            follow_up_suggestion="Seguir com simulacao.",
            slot_projection={"lead_name": "Ilki"},
            runtime_metadata={},
        )

    async def fake_get_conversation_policy_context(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(runtime_router, "is_langgraph_runtime_enabled", lambda: True)
    monkeypatch.setattr(runtime_router, "get_conversation_policy_context", fake_get_conversation_policy_context)
    monkeypatch.setattr(runtime_router, "run_message_through_langgraph", fake_run_message_through_langgraph)

    runtime_state, model_name = asyncio.run(
        runtime_router.run_configured_sales_runtime(
            state=state,
            tenant_id="tenant-1",
            agent_id="agent-1",
            lead=lead,
            channel="whatsapp",
        )
    )

    assert model_name == "langgraph"
    assert len(runtime_state.reply_fragments) >= 2
    assert runtime_state.draft_reply == "\n\n".join(runtime_state.reply_fragments)


def test_runtime_router_injects_policy_context_into_langgraph_request(monkeypatch) -> None:
    lead = SimpleNamespace(name=None, phone=None, cpf=None, metadata_json={})
    state = AgentState(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        message_text="oi",
        conversation_history=[],
        media_context=[],
    )
    observed: dict[str, object] = {}

    async def fake_get_conversation_policy_context(tenant_id: str, agent_id: str | None):
        observed["policy_lookup"] = (tenant_id, agent_id)
        return {"persona_tone": "consultivo e objetivo", "objection_playbook": {"preco": "reposicione pelo valor"}}

    async def fake_run_message_through_langgraph(request):
        observed["request_metadata"] = dict(request.metadata)
        return LangGraphTurnResponse(
            reply_text="Olá! Aqui é da Orfi Consórcios.",
            reply_fragments=["Olá! Aqui é da Orfi Consórcios."],
            follow_up_suggestion="Capturar nome do lead.",
            slot_projection={},
            runtime_metadata={},
        )

    monkeypatch.setattr(runtime_router, "is_langgraph_runtime_enabled", lambda: True)
    monkeypatch.setattr(runtime_router, "get_conversation_policy_context", fake_get_conversation_policy_context)
    monkeypatch.setattr(runtime_router, "run_message_through_langgraph", fake_run_message_through_langgraph)

    runtime_state, model_name = asyncio.run(
        runtime_router.run_configured_sales_runtime(
            state=state,
            tenant_id="tenant-1",
            agent_id="agent-1",
            lead=lead,
            channel="lab",
        )
    )

    assert model_name == "langgraph"
    assert observed["policy_lookup"] == ("tenant-1", "agent-1")
    assert observed["request_metadata"]["policy_context"]["persona_tone"] == "consultivo e objetivo"
    assert runtime_state.follow_up_suggestion == "Capturar nome do lead."
