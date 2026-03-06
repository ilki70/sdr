from dataclasses import dataclass, field


@dataclass
class AgentState:
    tenant_id: str
    lead_id: str | None = None
    conversation_id: str | None = None
    channel: str = "chatwoot"
    message_text: str = ""
    attachment_context: list[str] = field(default_factory=list)
    intent: str = "unknown"
    lead_stage: str = "new"
    funnel_stage: str = "discovery"
    objections: list[str] = field(default_factory=list)
    retrieved_context: list[str] = field(default_factory=list)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    next_action: str = "respond"
    draft_reply: str = ""
    reply_fragments: list[str] = field(default_factory=list)
    follow_up_suggestion: str | None = None
    handoff_required: bool = False
    handoff_reason: str | None = None
    confidence_score: float = 0.0
