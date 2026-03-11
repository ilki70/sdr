from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ChannelIntegration, Conversation, Lead, Message
from app.schemas.messages import ConversationDetailResponse, ConversationMessageResponse, ConversationSummaryResponse


LAB_INBOX_REF = "agent-lab"


async def get_conversation_or_none(db: AsyncSession, tenant_id: str, conversation_id: str) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def _get_or_create_lab_integration(db: AsyncSession, tenant_id: str, channel: str) -> ChannelIntegration:
    result = await db.execute(
        select(ChannelIntegration).where(
            ChannelIntegration.tenant_id == tenant_id,
            ChannelIntegration.provider == "agent_lab",
            ChannelIntegration.inbox_ref == f"{LAB_INBOX_REF}:{channel}",
            ChannelIntegration.deleted_at.is_(None),
        )
    )
    integration = result.scalar_one_or_none()
    if integration:
        return integration

    integration = ChannelIntegration(
        id=str(uuid4()),
        tenant_id=tenant_id,
        provider="agent_lab",
        inbox_ref=f"{LAB_INBOX_REF}:{channel}",
        api_base_url="http://127.0.0.1:3000/agent-lab",
        webhook_secret_enc=b"agent-lab-local",
        config_json={"channel": channel, "mode": "local"},
        status="active",
    )
    db.add(integration)
    await db.flush()
    return integration


async def _create_lab_lead(
    db: AsyncSession,
    tenant_id: str,
    integration_id: str,
    channel: str,
    title: str,
) -> Lead:
    lead = Lead(
        id=str(uuid4()),
        tenant_id=tenant_id,
        integration_id=integration_id,
        name=title,
        source_channel=channel,
        lifecycle_status="new",
        metadata_json={"source": "agent-lab"},
    )
    db.add(lead)
    await db.flush()
    return lead


async def create_lab_conversation(
    db: AsyncSession,
    tenant_id: str,
    channel: str = "lab",
    title: str | None = None,
) -> Conversation:
    integration = await _get_or_create_lab_integration(db, tenant_id, channel)
    lead_title = title or f"Sessao {datetime.now(timezone.utc).strftime('%d/%m %H:%M')}"
    lead = await _create_lab_lead(db, tenant_id, integration.id, channel, lead_title)
    conversation = Conversation(
        id=str(uuid4()),
        tenant_id=tenant_id,
        lead_id=lead.id,
        integration_id=integration.id,
        channel=channel,
        status="open",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def ensure_lab_conversation(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str | None,
    channel: str,
) -> Conversation:
    if conversation_id:
        conversation = await get_conversation_or_none(db, tenant_id, conversation_id)
        if conversation:
            return conversation
    return await create_lab_conversation(db, tenant_id=tenant_id, channel=channel)


async def list_conversation_messages(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str,
) -> list[Message]:
    direction_order = case((Message.direction == "inbound", 0), else_=1)
    result = await db.execute(
        select(Message)
        .where(Message.tenant_id == tenant_id, Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.asc(), direction_order.asc(), Message.created_at.asc(), Message.id.asc())
    )
    return list(result.scalars().all())


async def list_recent_conversation_messages(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str,
    limit: int = 10,
) -> list[Message]:
    direction_order = case((Message.direction == "outbound", 0), else_=1)
    result = await db.execute(
        select(Message)
        .where(Message.tenant_id == tenant_id, Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.desc(), direction_order.asc(), Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def save_message(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str,
    sender_type: str,
    direction: str,
    content: str,
    external_message_id: str | None = None,
    model_name: str | None = None,
    metadata_json: dict | None = None,
) -> Message:
    message = Message(
        id=str(uuid4()),
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        external_message_id=external_message_id,
        sender_type=sender_type,
        direction=direction,
        content=content,
        model_name=model_name,
        metadata_json=metadata_json,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(message)
    await db.flush()
    return message


async def persist_conversation_exchange(
    db: AsyncSession,
    conversation: Conversation,
    user_text: str,
    assistant_text: str,
    intent: str,
    confidence_score: float,
    model_name: str | None = None,
    reply_fragments: list[str] | None = None,
    follow_up_suggestion: str | None = None,
) -> None:
    await save_message(
        db=db,
        tenant_id=conversation.tenant_id,
        conversation_id=conversation.id,
        sender_type="lead",
        direction="inbound",
        content=user_text,
        metadata_json={"source": "agent-lab"},
    )
    await save_message(
        db=db,
        tenant_id=conversation.tenant_id,
        conversation_id=conversation.id,
        sender_type="assistant",
        direction="outbound",
        content=assistant_text,
        model_name=model_name,
        metadata_json={
            "intent": intent,
            "confidence_score": confidence_score,
            "reply_fragments": reply_fragments or [],
            "follow_up_suggestion": follow_up_suggestion,
        },
    )
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation.id)
        .values(status="open", updated_at=func.now())
    )
    await db.execute(
        update(Lead)
        .where(Lead.id == conversation.lead_id)
        .values(last_seen_at=func.now(), lifecycle_status="engaged", updated_at=func.now())
    )
    await db.commit()


def _preview_text(content: str, max_length: int = 72) -> str:
    compact = " ".join(content.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 1]}…"


async def list_conversations(db: AsyncSession, tenant_id: str) -> list[ConversationSummaryResponse]:
    conversations_result = await db.execute(
        select(Conversation, Lead.name)
        .join(Lead, Lead.id == Conversation.lead_id)
        .where(Conversation.tenant_id == tenant_id)
        .order_by(Conversation.updated_at.desc(), Conversation.started_at.desc())
    )
    rows = list(conversations_result.all())
    if not rows:
        return []

    conversation_ids = [conversation.id for conversation, _lead_name in rows]
    counts_result = await db.execute(
        select(Message.conversation_id, func.count(Message.id))
        .where(Message.tenant_id == tenant_id, Message.conversation_id.in_(conversation_ids))
        .group_by(Message.conversation_id)
    )
    count_map = {conversation_id: count for conversation_id, count in counts_result.all()}

    latest_result = await db.execute(
        select(Message)
        .where(Message.tenant_id == tenant_id, Message.conversation_id.in_(conversation_ids))
        .order_by(Message.conversation_id.asc(), Message.sent_at.desc(), Message.created_at.desc())
    )
    latest_by_conversation: dict[str, Message] = {}
    for message in latest_result.scalars().all():
        latest_by_conversation.setdefault(message.conversation_id, message)

    return [
        ConversationSummaryResponse(
            id=conversation.id,
            title=lead_name or f"Conversa {conversation.id[:8]}",
            channel=conversation.channel,
            status=conversation.status,
            lead_id=conversation.lead_id,
            started_at=conversation.started_at,
            updated_at=conversation.updated_at,
            last_message_preview=(
                _preview_text(latest_by_conversation[conversation.id].content)
                if conversation.id in latest_by_conversation
                else None
            ),
            message_count=int(count_map.get(conversation.id, 0)),
        )
        for conversation, lead_name in rows
    ]


async def get_conversation_detail(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str,
) -> ConversationDetailResponse | None:
    conversations = await list_conversations(db, tenant_id)
    summary = next((item for item in conversations if item.id == conversation_id), None)
    if not summary:
        return None

    messages = await list_conversation_messages(db, tenant_id, conversation_id)
    return ConversationDetailResponse(
        conversation=summary,
        messages=[
            ConversationMessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                sender_type=message.sender_type,
                direction=message.direction,
                content=message.content,
                model_name=message.model_name,
                metadata_json=message.metadata_json,
                sent_at=message.sent_at,
            )
            for message in messages
        ],
    )
