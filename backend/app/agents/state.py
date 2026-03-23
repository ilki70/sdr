from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    tenant_id: str
    agent_id: str | None = None
    lead_id: str | None = None
    conversation_id: str | None = None
    channel: str = "chatwoot"
    message_text: str = ""
    intent: str = "unknown"
    lead_stage: str = "new"
    objections: list[str] = field(default_factory=list)
    retrieved_context: list[str] = field(default_factory=list)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    conversation_context: dict[str, Any] = field(default_factory=dict)
    media_context: list[str] = field(default_factory=list)
    next_action: str = "respond"
    draft_reply: str = ""
    reply_fragments: list[str] = field(default_factory=list)
    follow_up_suggestion: str | None = None
    confidence_score: float = 0.0
