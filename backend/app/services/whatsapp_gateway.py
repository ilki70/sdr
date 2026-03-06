from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_sales_agent
from app.agents.state import AgentState
from app.core.config import get_settings
from app.models.entities import ChannelIntegration, Conversation, Lead, Message
from app.schemas.whatsapp import (
    WhatsAppGatewayStatusPayload,
    WhatsAppInboundRequest,
    WhatsAppInboundResponse,
    WhatsAppSessionStatusResponse,
)
from app.services.messages import list_recent_conversation_messages, save_message

settings = get_settings()



def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)



def _clean_phone(sender_id: str) -> str:
    return "".join(char for char in sender_id if char.isdigit())[:40]



def _gateway_headers() -> dict[str, str]:
    return {"X-WhatsApp-Gateway-Secret": settings.whatsapp_gateway_secret}


async def get_whatsapp_integration_or_none(db: AsyncSession, tenant_id: str) -> ChannelIntegration | None:
    result = await db.execute(
        select(ChannelIntegration)
        .where(
            ChannelIntegration.tenant_id == tenant_id,
            ChannelIntegration.provider == "whatsapp",
            ChannelIntegration.deleted_at.is_(None),
        )
        .order_by(ChannelIntegration.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def ensure_whatsapp_integration(db: AsyncSession, tenant_id: str) -> ChannelIntegration:
    integration = await get_whatsapp_integration_or_none(db, tenant_id)
    if integration:
        return integration

    integration = ChannelIntegration(
        id=str(uuid4()),
        tenant_id=tenant_id,
        provider="whatsapp",
        inbox_ref="whatsapp-primary",
        api_base_url=settings.whatsapp_gateway_base_url.rstrip("/"),
        webhook_secret_enc=settings.whatsapp_gateway_secret.encode("utf-8"),
        config_json={"channel": "whatsapp", "mode": "whatsmeow"},
        status="draft",
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


async def _call_gateway(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url = settings.whatsapp_gateway_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.request(
                method,
                f"{base_url}{path}",
                headers=_gateway_headers(),
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"WhatsApp gateway unavailable: {exc}",
        ) from exc

    if response.status_code >= 400:
        detail = response.text or "Gateway error"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

    if not response.content:
        return {}
    return response.json()


async def _configure_gateway(tenant_id: str, integration: ChannelIntegration) -> None:
    await _call_gateway(
        "PUT",
        "/api/v1/session/config",
        {
            "tenant_id": tenant_id,
            "integration_id": integration.id,
            "callback_url": f"{settings.backend_internal_url.rstrip('/')}/api/v1/whatsapp/inbound",
            "callback_secret": settings.whatsapp_gateway_secret,
        },
    )


async def build_whatsapp_session_status(
    db: AsyncSession,
    tenant_id: str,
    ensure_integration: bool = False,
) -> WhatsAppSessionStatusResponse:
    integration = await ensure_whatsapp_integration(db, tenant_id) if ensure_integration else await get_whatsapp_integration_or_none(db, tenant_id)
    if not integration:
        return WhatsAppSessionStatusResponse(
            integration_exists=False,
            gateway=WhatsAppGatewayStatusPayload(),
        )

    try:
        gateway_payload = await _call_gateway("GET", "/api/v1/session/status")
        gateway = WhatsAppGatewayStatusPayload.model_validate(gateway_payload)
    except HTTPException as exc:
        gateway = WhatsAppGatewayStatusPayload(
            connected=False,
            session_status="gateway_unavailable",
            last_error=str(exc.detail),
        )
    return WhatsAppSessionStatusResponse(
        integration_exists=True,
        integration_id=integration.id,
        integration_status=integration.status,
        inbox_ref=integration.inbox_ref,
        api_base_url=integration.api_base_url,
        config_json=integration.config_json,
        gateway=gateway,
    )


async def bootstrap_whatsapp_gateway(db: AsyncSession, tenant_id: str) -> WhatsAppSessionStatusResponse:
    integration = await ensure_whatsapp_integration(db, tenant_id)
    await _configure_gateway(tenant_id, integration)
    if integration.status == "draft":
        integration.status = "active"
        await db.commit()
        await db.refresh(integration)
    return await build_whatsapp_session_status(db, tenant_id)


async def connect_whatsapp_gateway(db: AsyncSession, tenant_id: str) -> WhatsAppSessionStatusResponse:
    integration = await ensure_whatsapp_integration(db, tenant_id)
    await _configure_gateway(tenant_id, integration)
    await _call_gateway("POST", "/api/v1/session/connect")
    integration.status = "active"
    await db.commit()
    return await build_whatsapp_session_status(db, tenant_id)


async def disconnect_whatsapp_gateway(db: AsyncSession, tenant_id: str) -> WhatsAppSessionStatusResponse:
    integration = await get_whatsapp_integration_or_none(db, tenant_id)
    if not integration:
        return WhatsAppSessionStatusResponse(integration_exists=False, gateway=WhatsAppGatewayStatusPayload())
    await _configure_gateway(tenant_id, integration)
    await _call_gateway("POST", "/api/v1/session/disconnect")
    integration.status = "paused"
    await db.commit()
    return await build_whatsapp_session_status(db, tenant_id)


async def _get_lead_by_external_contact(
    db: AsyncSession,
    tenant_id: str,
    integration_id: str,
    sender_id: str,
) -> Lead | None:
    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.integration_id == integration_id,
            Lead.external_contact_id == sender_id,
            Lead.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _ensure_whatsapp_lead(
    db: AsyncSession,
    payload: WhatsAppInboundRequest,
    phone: str,
) -> Lead:
    lead = await _get_lead_by_external_contact(db, payload.tenant_id, payload.integration_id, payload.sender_id)
    if lead:
        lead.name = payload.sender_name or payload.push_name or lead.name
        lead.phone = phone or lead.phone
        lead.last_seen_at = _utcnow_naive()
        lead.lifecycle_status = "engaged"
        if lead.metadata_json is None:
            lead.metadata_json = {}
        lead.metadata_json.update({"last_channel": "whatsapp", "last_chat_id": payload.chat_id})
        await db.flush()
        return lead

    lead = Lead(
        id=str(uuid4()),
        tenant_id=payload.tenant_id,
        integration_id=payload.integration_id,
        external_contact_id=payload.sender_id,
        name=payload.sender_name or payload.push_name or phone or "Lead WhatsApp",
        phone=phone or None,
        source_channel="whatsapp",
        lifecycle_status="engaged",
        first_seen_at=_utcnow_naive(),
        last_seen_at=_utcnow_naive(),
        metadata_json={"source": "whatsapp_gateway", "last_chat_id": payload.chat_id},
    )
    db.add(lead)
    await db.flush()
    return lead


async def _ensure_whatsapp_conversation(
    db: AsyncSession,
    payload: WhatsAppInboundRequest,
    lead: Lead,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == payload.tenant_id,
            Conversation.integration_id == payload.integration_id,
            Conversation.external_conversation_id == payload.chat_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation

    conversation = Conversation(
        id=str(uuid4()),
        tenant_id=payload.tenant_id,
        lead_id=lead.id,
        integration_id=payload.integration_id,
        external_conversation_id=payload.chat_id,
        channel="whatsapp",
        status="open",
        started_at=_utcnow_naive(),
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def _load_history_for_agent(db: AsyncSession, tenant_id: str, conversation_id: str) -> list[dict[str, str]]:
    history = await list_recent_conversation_messages(db, tenant_id, conversation_id)
    return [
        {
            "role": "assistant" if message.sender_type == "assistant" else "user",
            "content": message.content,
        }
        for message in history
    ]


async def process_whatsapp_inbound(db: AsyncSession, payload: WhatsAppInboundRequest) -> WhatsAppInboundResponse:
    integration = await get_whatsapp_integration_or_none(db, payload.tenant_id)
    if not integration or integration.id != payload.integration_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp integration not found")

    duplicate_result = await db.execute(
        select(Message).where(
            Message.tenant_id == payload.tenant_id,
            Message.external_message_id == payload.message_id,
        )
    )
    if duplicate_result.scalar_one_or_none():
        lead = await _get_lead_by_external_contact(db, payload.tenant_id, payload.integration_id, payload.sender_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate message without lead context")
        conversation = await _ensure_whatsapp_conversation(db, payload, lead)
        return WhatsAppInboundResponse(
            duplicate=True,
            lead_id=lead.id,
            conversation_id=conversation.id,
            reply_text="",
            reply_fragments=[],
            follow_up_suggestion=None,
        )

    phone = _clean_phone(payload.sender_id)
    lead = await _ensure_whatsapp_lead(db, payload, phone)
    conversation = await _ensure_whatsapp_conversation(db, payload, lead)
    history = await _load_history_for_agent(db, payload.tenant_id, conversation.id)

    state = AgentState(
        tenant_id=payload.tenant_id,
        lead_id=lead.id,
        conversation_id=conversation.id,
        channel="whatsapp",
        message_text=payload.message_text,
        conversation_history=history,
    )
    state = await run_sales_agent(state)

    await save_message(
        db=db,
        tenant_id=payload.tenant_id,
        conversation_id=conversation.id,
        sender_type="lead",
        direction="inbound",
        content=payload.message_text,
        external_message_id=payload.message_id,
        metadata_json={
            "source": "whatsapp_gateway",
            "chat_id": payload.chat_id,
            "sender_id": payload.sender_id,
        },
    )
    await save_message(
        db=db,
        tenant_id=payload.tenant_id,
        conversation_id=conversation.id,
        sender_type="assistant",
        direction="outbound",
        content=state.draft_reply,
        model_name=settings.openai_model if settings.openai_api_key else "mock-llm",
        metadata_json={
            "source": "whatsapp_gateway",
            "intent": state.intent,
            "confidence_score": state.confidence_score,
            "reply_fragments": state.reply_fragments,
            "follow_up_suggestion": state.follow_up_suggestion,
        },
    )
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation.id)
        .values(status="open", updated_at=func.now())
    )
    await db.execute(
        update(Lead)
        .where(Lead.id == lead.id)
        .values(last_seen_at=func.now(), lifecycle_status="engaged", updated_at=func.now())
    )
    await db.commit()

    return WhatsAppInboundResponse(
        duplicate=False,
        lead_id=lead.id,
        conversation_id=conversation.id,
        reply_text=state.draft_reply,
        reply_fragments=state.reply_fragments,
        follow_up_suggestion=state.follow_up_suggestion,
    )
