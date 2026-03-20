import secrets
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_sales_agent
from app.agents.state import AgentState
from app.core.time import utcnow_naive
from app.models.entities import ChannelIntegration, Conversation, Lead, Message
from app.schemas.whatsapp import WhatsAppInboundWebhookRequest, WhatsAppInboundWebhookResponse
from app.services.conversation_media import summarize_media_attachments
from app.services.conversation_context import (
    load_cached_conversation_context,
    refresh_conversation_context_from_db,
    resolve_fragmented_inbound_text,
    store_cached_conversation_context,
)
from app.services.messages import list_recent_conversation_messages, save_message


async def _get_integration_for_webhook(
    db: AsyncSession,
    inbox_ref: str,
    webhook_secret: str,
) -> ChannelIntegration | None:
    result = await db.execute(
        select(ChannelIntegration).where(
            ChannelIntegration.provider == "whatsapp-service",
            ChannelIntegration.inbox_ref == inbox_ref,
            ChannelIntegration.deleted_at.is_(None),
            ChannelIntegration.status.in_(("active", "test")),
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return None

    expected_secret = integration.webhook_secret_enc.decode("utf-8")
    if not secrets.compare_digest(expected_secret, webhook_secret):
        return None
    return integration


async def _get_existing_message(
    db: AsyncSession,
    tenant_id: str,
    external_message_id: str | None,
) -> Message | None:
    if not external_message_id:
        return None
    result = await db.execute(
        select(Message).where(
            Message.tenant_id == tenant_id,
            Message.external_message_id == external_message_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_conversation_or_none(db: AsyncSession, tenant_id: str, conversation_id: str) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.id == conversation_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_or_create_lead(
    db: AsyncSession,
    integration: ChannelIntegration,
    payload: WhatsAppInboundWebhookRequest,
) -> Lead:
    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == integration.tenant_id,
            Lead.integration_id == integration.id,
            Lead.external_contact_id == payload.contact_id,
            Lead.deleted_at.is_(None),
        )
    )
    lead = result.scalar_one_or_none()
    if lead:
        updates = {
            "last_seen_at": utcnow_naive(),
            "updated_at": utcnow_naive(),
        }
        if payload.contact_name and payload.contact_name != lead.name:
            updates["name"] = payload.contact_name
        if payload.contact_phone and payload.contact_phone != lead.phone:
            updates["phone"] = payload.contact_phone
        if updates:
            await db.execute(update(Lead).where(Lead.id == lead.id).values(**updates))
            await db.flush()
        return lead

    lead = Lead(
        id=str(uuid4()),
        tenant_id=integration.tenant_id,
        integration_id=integration.id,
        external_contact_id=payload.contact_id,
        name=payload.contact_name,
        phone=payload.contact_phone,
        source_channel="whatsapp",
        lifecycle_status="engaged",
        last_seen_at=utcnow_naive(),
        metadata_json=payload.metadata_json or {"source": "whatsapp-service"},
    )
    db.add(lead)
    await db.flush()
    return lead


async def _get_or_create_conversation(
    db: AsyncSession,
    integration: ChannelIntegration,
    lead: Lead,
    payload: WhatsAppInboundWebhookRequest,
) -> Conversation:
    if payload.external_conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.tenant_id == integration.tenant_id,
                Conversation.integration_id == integration.id,
                Conversation.external_conversation_id == payload.external_conversation_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            return conversation

    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.tenant_id == integration.tenant_id,
            Conversation.integration_id == integration.id,
            Conversation.lead_id == lead.id,
            Conversation.status == "open",
        )
        .order_by(Conversation.updated_at.desc(), Conversation.started_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation

    conversation = Conversation(
        id=str(uuid4()),
        tenant_id=integration.tenant_id,
        agent_id=integration.agent_id,
        lead_id=lead.id,
        integration_id=integration.id,
        external_conversation_id=payload.external_conversation_id,
        channel="whatsapp",
        status="open",
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def handle_inbound_whatsapp_message(
    db: AsyncSession,
    payload: WhatsAppInboundWebhookRequest,
) -> WhatsAppInboundWebhookResponse | None:
    integration = await _get_integration_for_webhook(db, payload.inbox_ref, payload.webhook_secret)
    if not integration:
        return None

    duplicate = await _get_existing_message(db, integration.tenant_id, payload.external_message_id)
    if duplicate:
        conversation = await _get_conversation_or_none(db, integration.tenant_id, duplicate.conversation_id)
        return WhatsAppInboundWebhookResponse(
            tenant_id=integration.tenant_id,
            integration_id=integration.id,
            lead_id=conversation.lead_id if conversation else "",
            conversation_id=duplicate.conversation_id,
            reply_text="",
            intent="duplicate",
            confidence_score=1.0,
            duplicate_message=True,
        )

    media_notes = await summarize_media_attachments([attachment.model_dump() for attachment in payload.attachments])
    incoming_text = payload.message_text.strip()
    if not incoming_text and not media_notes:
        raise HTTPException(status_code=400, detail="Empty inbound message")

    lead = await _get_or_create_lead(db, integration, payload)
    conversation = await _get_or_create_conversation(db, integration, lead, payload)

    conversation_context = await load_cached_conversation_context(integration.tenant_id, conversation.id)
    if conversation_context is None:
        conversation_context = await refresh_conversation_context_from_db(
            db,
            tenant_id=integration.tenant_id,
            conversation_id=conversation.id,
        )

    deferred = False
    if not media_notes:
        conversation_context, effective_message_text, deferred = resolve_fragmented_inbound_text(
            conversation_context,
            incoming_text,
        )
        await store_cached_conversation_context(conversation_context)
        if deferred:
            await db.commit()
            return WhatsAppInboundWebhookResponse(
                tenant_id=integration.tenant_id,
                integration_id=integration.id,
                lead_id=lead.id,
                conversation_id=conversation.id,
                reply_text="",
                intent="fragment_buffered",
                confidence_score=0.0,
                follow_up_suggestion=None,
                reply_fragments=[],
                deferred=True,
            )
    else:
        effective_message_text = incoming_text
        media_note_text = " | ".join(media_notes)
        effective_message_text = f"{effective_message_text}\n{media_note_text}".strip()

    await save_message(
        db=db,
        tenant_id=integration.tenant_id,
        conversation_id=conversation.id,
        sender_type="lead",
        direction="inbound",
        content=effective_message_text,
        external_message_id=payload.external_message_id,
        metadata_json={
            "source": "whatsapp-service",
            "contact_id": payload.contact_id,
            "contact_phone": payload.contact_phone,
            "attachments": [attachment.model_dump() for attachment in payload.attachments],
            "media_notes": media_notes,
            **(payload.metadata_json or {}),
        },
    )

    conversation_context = await refresh_conversation_context_from_db(
        db,
        tenant_id=integration.tenant_id,
        conversation_id=conversation.id,
        media_notes=media_notes,
    )
    history = await list_recent_conversation_messages(db, integration.tenant_id, conversation.id)
    state = AgentState(
        tenant_id=integration.tenant_id,
        agent_id=conversation.agent_id or integration.agent_id,
        lead_id=lead.id,
        conversation_id=conversation.id,
        channel="whatsapp",
        message_text=effective_message_text,
        conversation_context=conversation_context.model_dump(),
        media_context=media_notes,
        conversation_history=[
            {
                "role": "assistant" if message.sender_type == "assistant" else "user",
                "content": message.content,
            }
            for message in history[:-1]
        ],
    )
    state = await run_sales_agent(state)

    await save_message(
        db=db,
        tenant_id=integration.tenant_id,
        conversation_id=conversation.id,
        sender_type="assistant",
        direction="outbound",
        content=state.draft_reply,
        metadata_json={
            "source": "whatsapp-service",
            "intent": state.intent,
            "confidence_score": state.confidence_score,
            "reply_fragments": state.reply_fragments,
            "follow_up_suggestion": state.follow_up_suggestion,
        },
    )
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation.id)
        .values(status="open", updated_at=utcnow_naive())
    )
    await db.execute(
        update(Lead)
        .where(Lead.id == lead.id)
        .values(last_seen_at=utcnow_naive(), lifecycle_status="engaged", updated_at=utcnow_naive())
    )
    await refresh_conversation_context_from_db(
        db,
        tenant_id=integration.tenant_id,
        conversation_id=conversation.id,
        last_intent=state.intent,
    )
    await db.commit()

    return WhatsAppInboundWebhookResponse(
        tenant_id=integration.tenant_id,
        integration_id=integration.id,
        lead_id=lead.id,
        conversation_id=conversation.id,
        reply_text=state.draft_reply,
        intent=state.intent,
        confidence_score=state.confidence_score,
        follow_up_suggestion=state.follow_up_suggestion,
        reply_fragments=state.reply_fragments,
    )
