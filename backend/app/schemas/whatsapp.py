from typing import Any

from pydantic import BaseModel, Field


class WhatsAppInboundWebhookRequest(BaseModel):
    inbox_ref: str = Field(min_length=2, max_length=128)
    webhook_secret: str = Field(min_length=4, max_length=255)
    message_text: str = Field(min_length=1, max_length=4000)
    contact_id: str = Field(min_length=1, max_length=128)
    contact_name: str | None = Field(default=None, max_length=140)
    contact_phone: str | None = Field(default=None, max_length=40)
    external_message_id: str | None = Field(default=None, max_length=128)
    external_conversation_id: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None


class WhatsAppInboundWebhookResponse(BaseModel):
    tenant_id: str
    integration_id: str
    lead_id: str
    conversation_id: str
    reply_text: str
    intent: str
    confidence_score: float
    follow_up_suggestion: str | None = None
    reply_fragments: list[str] = Field(default_factory=list)
    duplicate_message: bool = False
