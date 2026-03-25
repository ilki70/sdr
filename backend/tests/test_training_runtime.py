from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services import training


class _FakeDB:
    def __init__(self) -> None:
        self.flush_calls = 0

    async def flush(self) -> None:
        self.flush_calls += 1


def test_run_training_turn_uses_configured_runtime_and_projects_slots(monkeypatch) -> None:
    db = _FakeDB()
    lead = SimpleNamespace(id="lead-1", phone=None, name=None, cpf=None, metadata_json={})
    conversation = SimpleNamespace(id="conv-1", lead_id="lead-1")
    history = [
        SimpleNamespace(sender_type="assistant", content="Ola"),
        SimpleNamespace(sender_type="lead", content="Quero um imovel"),
    ]
    observed: dict[str, object] = {}

    def fake_apply_lead_capture(lead_obj, *, text: str, fallback_phone: str | None) -> None:
        observed["captured_text"] = text
        observed["fallback_phone"] = fallback_phone

    async def fake_run_configured_sales_runtime(**kwargs):
        observed["runtime_call"] = kwargs
        return (
            SimpleNamespace(
                draft_reply="Perfeito. Qual valor faz sentido para voce?",
                intent="langgraph_flow",
                confidence_score=1.0,
                reply_fragments=["Perfeito.", "Qual valor faz sentido para voce?"],
                follow_up_suggestion="Perguntar faixa de valor",
                slot_projection={"asset_type": "imovel"},
                runtime_metadata={"current_topic": "qualification"},
            ),
            "langgraph",
        )

    def fake_apply_runtime_slot_projection(lead_obj, slot_projection, *, source: str, runtime_metadata=None) -> None:
        observed["slot_projection"] = dict(slot_projection)
        observed["runtime_metadata"] = dict(runtime_metadata or {})
        observed["slot_source"] = source
        lead_obj.metadata_json = {"langgraph_slot_projection": dict(slot_projection)}

    monkeypatch.setattr(training, "apply_lead_capture", fake_apply_lead_capture)
    monkeypatch.setattr(training, "run_configured_sales_runtime", fake_run_configured_sales_runtime)
    monkeypatch.setattr(training, "apply_runtime_slot_projection", fake_apply_runtime_slot_projection)

    state, model_name = asyncio.run(
        training._run_training_turn(
            db=db,
            tenant_id="tenant-1",
            agent_id="agent-1",
            conversation=conversation,
            lead=lead,
            message_text="Quero um imovel",
            history=history,
        )
    )

    assert model_name == "langgraph"
    assert state.draft_reply.startswith("Perfeito.")
    assert observed["captured_text"] == "Quero um imovel"
    assert observed["slot_projection"] == {"asset_type": "imovel"}
    assert observed["runtime_metadata"] == {"current_topic": "qualification"}
    assert observed["slot_source"] == "langgraph"
    assert observed["runtime_call"]["agent_id"] == "agent-1"
    assert observed["runtime_call"]["channel"] == "lab"
    assert db.flush_calls == 2
