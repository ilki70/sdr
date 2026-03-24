from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field


class MessageSimulateRequest(BaseModel):
    message_text: str = Field(default="", max_length=4000)
    agent_id: str | None = Field(default=None, max_length=36)
    lead_id: str | None = Field(default=None, max_length=36)
    conversation_id: str | None = Field(default=None, max_length=36)
    channel: str = Field(default="chatwoot", max_length=24)
    attachments: list["MessageSimulateAttachment"] = Field(default_factory=list)


class MessageSimulateResponse(BaseModel):
    conversation_id: str
    intent: str
    confidence_score: float
    reply: str
    reply_fragments: list[str] = Field(default_factory=list)
    follow_up_suggestion: str | None = None


class MessageSimulateAttachment(BaseModel):
    kind: Literal["audio", "image", "document", "video", "file"] = "file"
    file_ref: str = Field(min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, max_length=80)
    caption: str | None = Field(default=None, max_length=500)
    filename: str | None = Field(default=None, max_length=255)


class ConversationCreateRequest(BaseModel):
    agent_id: str | None = Field(default=None, max_length=36)
    title: str | None = Field(default=None, min_length=1, max_length=140)
    channel: str = Field(default="lab", max_length=24)


class ConversationPipelineStatusUpdateRequest(BaseModel):
    pipeline_status: Literal["new", "qualifying", "handoff", "scheduled", "disqualified"]


class ConversationSummaryResponse(BaseModel):
    id: str
    agent_id: str | None = None
    title: str
    channel: str
    status: str
    lead_id: str
    lead_name: str | None = None
    lead_phone: str | None = None
    lead_cpf: str | None = None
    lead_profile_missing_fields: list[str] = Field(default_factory=list)
    agent_paused: bool = False
    started_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None
    summary: str | None = None
    pipeline_status: str | None = None
    next_step: str | None = None
    message_count: int = 0


class ConversationMessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    direction: str
    content: str
    model_name: str | None = None
    metadata_json: dict[str, Any] | None = None
    sent_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationSummaryResponse
    messages: list[ConversationMessageResponse]
