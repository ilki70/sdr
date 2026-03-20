from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field


class WhatsAppGatewayStatusPayload(BaseModel):
    connected: bool = False
    session_status: str = "idle"
    paired_phone: str | None = None
    qr_code_data_url: str | None = None
    qr_code_text: str | None = None
    last_event: str | None = None
    last_error: str | None = None
    updated_at: datetime | None = None


class WhatsAppSessionStatusResponse(BaseModel):
    integration_exists: bool
    integration_id: str | None = None
    provider: str = "whatsapp"
    integration_status: str = "missing"
    inbox_ref: str | None = None
    api_base_url: str | None = None
    config_json: dict[str, Any] | None = None
    gateway: WhatsAppGatewayStatusPayload


class WhatsAppInboundRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    integration_id: str = Field(min_length=1, max_length=36)
    chat_id: str = Field(min_length=1, max_length=160)
    sender_id: str = Field(min_length=1, max_length=80)
    sender_name: str | None = Field(default=None, max_length=140)
    message_id: str = Field(min_length=1, max_length=128)
    message_text: str = Field(default="", max_length=4000)
    push_name: str | None = Field(default=None, max_length=140)
    sent_at: datetime | None = None
    attachments: list["WhatsAppInboundAttachment"] = Field(default_factory=list)


class WhatsAppInboundResponse(BaseModel):
    duplicate: bool = False
    deferred: bool = False
    lead_id: str
    conversation_id: str
    reply_text: str
    reply_fragments: list[str] = Field(default_factory=list)
    follow_up_suggestion: str | None = None


class WhatsAppInboundAttachment(BaseModel):
    kind: Literal["audio", "image", "document", "video", "file"] = "file"
    file_ref: str = Field(min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, max_length=80)
    caption: str | None = Field(default=None, max_length=500)
    filename: str | None = Field(default=None, max_length=255)


class WhatsAppInboundWebhookRequest(BaseModel):
    inbox_ref: str = Field(min_length=2, max_length=128)
    webhook_secret: str = Field(min_length=4, max_length=255)
    message_text: str = Field(default="", max_length=4000)
    contact_id: str = Field(min_length=1, max_length=128)
    contact_name: str | None = Field(default=None, max_length=140)
    contact_phone: str | None = Field(default=None, max_length=40)
    external_message_id: str | None = Field(default=None, max_length=128)
    external_conversation_id: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None
    attachments: list[WhatsAppInboundAttachment] = Field(default_factory=list)


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
    deferred: bool = False
