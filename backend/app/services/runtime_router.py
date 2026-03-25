from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.agents.graph import run_sales_agent
from app.agents.state import AgentState
from app.services.channel_formatter import format_reply
from app.services.conversation_policy_config import get_conversation_policy_context
from app.services.conversation_runtime_state import get_runtime_state as load_runtime_state
from app.services.conversation_runtime_state import store_runtime_state
from app.services.langgraph_runtime import (
    LangGraphTurnRequest,
    is_langgraph_runtime_enabled,
    run_message_through_langgraph,
)


def get_runtime_state(lead, *, source: str | None = None) -> dict[str, object]:
    metadata = dict(getattr(lead, "metadata_json", {}) or {})
    return load_runtime_state(metadata, source=source)


def apply_runtime_slot_projection(
    lead,
    slot_projection: dict[str, object],
    *,
    source: str,
    runtime_metadata: dict[str, object] | None = None,
) -> None:
    if not isinstance(slot_projection, dict):
        return

    lead_name = slot_projection.get("lead_name")
    if isinstance(lead_name, str) and lead_name.strip():
        lead.name = lead_name.strip()

    phone = slot_projection.get("phone")
    if isinstance(phone, str) and phone.strip():
        lead.phone = phone.strip()

    cpf = slot_projection.get("cpf")
    if isinstance(cpf, str) and cpf.strip():
        lead.cpf = cpf.strip()

    metadata = dict(lead.metadata_json or {})
    metadata[f"{source}_slot_projection"] = {
        key: value for key, value in slot_projection.items() if isinstance(key, str)
    }
    if isinstance(runtime_metadata, dict) and runtime_metadata:
        metadata = store_runtime_state(metadata, runtime_metadata, source=source)
    lead.metadata_json = metadata


async def run_configured_sales_runtime(
    *,
    state: AgentState,
    tenant_id: str,
    agent_id: str | None,
    lead,
    channel: str,
    attachments: list[dict[str, Any]] | None = None,
) -> tuple[SimpleNamespace | AgentState, str]:
    attachment_payload = attachments or []

    if is_langgraph_runtime_enabled():
        policy_context = await get_conversation_policy_context(tenant_id, agent_id)
        langgraph_response = await run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id=tenant_id,
                conversation_id=state.conversation_id or "",
                message_text=state.message_text,
                conversation_history=state.conversation_history,
                lead_name=getattr(lead, "name", None),
                lead_phone=getattr(lead, "phone", None),
                lead_cpf=getattr(lead, "cpf", None),
                lead_metadata=dict(getattr(lead, "metadata_json", {}) or {}),
                conversation_context=dict(state.conversation_context or {}),
                channel=channel,
                metadata={"agent_id": agent_id, "attachments": attachment_payload, "policy_context": policy_context},
            )
        )
        apply_runtime_slot_projection(
            lead,
            langgraph_response.slot_projection,
            source="langgraph",
            runtime_metadata=langgraph_response.runtime_metadata,
        )
        formatted_reply_text, formatted_fragments = format_reply(channel, langgraph_response.reply_fragments)
        runtime_state = SimpleNamespace(
            message_text=state.message_text,
            draft_reply=formatted_reply_text,
            reply_fragments=formatted_fragments,
            follow_up_suggestion=langgraph_response.follow_up_suggestion,
            intent="langgraph_flow",
            confidence_score=1.0,
            media_context=state.media_context,
            handoff_requested=langgraph_response.handoff_requested,
            slot_projection=langgraph_response.slot_projection,
            runtime_metadata=langgraph_response.runtime_metadata,
        )
        return runtime_state, langgraph_response.runtime_label

    legacy_state = await run_sales_agent(state)
    legacy_state.handoff_requested = False
    legacy_state.slot_projection = {}
    return legacy_state, "mock-llm"
