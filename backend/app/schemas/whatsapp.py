from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WhatsAppGatewayStatusPayload(BaseModel):
    connected: bool = False
    session_status: str = "idle"
    paired_phone: str | None = None
    qr_code_data_url: str | None = None
    qr_code_text: str | None = None
    last_event: str | None = None
    last_error: str | None = None
    last_inbound_at: datetime | None = None
    last_inbound_chat: str | None = None
    last_inbound_preview: str | None = None
    last_callback_status: str | None = None
    last_outbound_at: datetime | None = None
    last_outbound_chat: str | None = None
    last_outbound_preview: str | None = None
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
    message_type: str = Field(default="text", max_length=40)
    media_kind: str | None = Field(default=None, max_length=40)
    media_mime_type: str | None = Field(default=None, max_length=120)
    media_filename: str | None = Field(default=None, max_length=255)
    media_caption: str | None = Field(default=None, max_length=4000)
    media_base64: str | None = None
    push_name: str | None = Field(default=None, max_length=140)
    sent_at: datetime | None = None


class WhatsAppInboundResponse(BaseModel):
    duplicate: bool = False
    lead_id: str
    conversation_id: str
    reply_text: str
    reply_fragments: list[str] = Field(default_factory=list)
    follow_up_suggestion: str | None = None
