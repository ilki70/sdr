from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageSimulateRequest(BaseModel):
    message_text: str = Field(min_length=1, max_length=4000)
    lead_id: str | None = Field(default=None, max_length=36)
    conversation_id: str | None = Field(default=None, max_length=36)
    channel: str = Field(default="chatwoot", max_length=24)


class MessageSimulateResponse(BaseModel):
    conversation_id: str
    intent: str
    confidence_score: float
    reply: str
    reply_fragments: list[str] = Field(default_factory=list)
    follow_up_suggestion: str | None = None


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    channel: str = Field(default="lab", max_length=24)


class ConversationSummaryResponse(BaseModel):
    id: str
    title: str
    channel: str
    status: str
    lead_id: str
    started_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None
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
