from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow_naive
from app.services.agents import resolve_agent_for_conversation
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
    agent_id: str | None = None,
    channel: str = "lab",
    title: str | None = None,
) -> Conversation:
    agent = await resolve_agent_for_conversation(db, tenant_id, agent_id)
    integration = await _get_or_create_lab_integration(db, tenant_id, channel)
    if integration.agent_id != (agent.id if agent else None):
        integration.agent_id = agent.id if agent else None
    lead_title = title or f"Sessao {utcnow_naive().strftime('%d/%m %H:%M')}"
    lead = await _create_lab_lead(db, tenant_id, integration.id, channel, lead_title)
    conversation = Conversation(
        id=str(uuid4()),
        tenant_id=tenant_id,
        agent_id=agent.id if agent else None,
        lead_id=lead.id,
        integration_id=integration.id,
        channel=channel,
        status="open",
        pipeline_status="new",
        summary=f"Conversa iniciada no canal {channel}.",
        next_step="Fazer primeira qualificacao e captar contexto basico do lead.",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def ensure_lab_conversation(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str | None,
    agent_id: str | None,
    channel: str,
) -> Conversation:
    if conversation_id:
        conversation = await get_conversation_or_none(db, tenant_id, conversation_id)
        if conversation:
            return conversation
    return await create_lab_conversation(db, tenant_id=tenant_id, agent_id=agent_id, channel=channel)


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
    limit: int = 20,
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
        sent_at=utcnow_naive(),
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
    pipeline_status = conversation.pipeline_status or "qualifying"
    next_step = follow_up_suggestion or _derive_next_step(pipeline_status, None)
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation.id)
        .values(
            status="open",
            pipeline_status=pipeline_status,
            summary=_preview_text(user_text, max_length=160),
            next_step=next_step,
            updated_at=func.now(),
        )
    )
    await db.execute(
        update(Lead)
        .where(Lead.id == conversation.lead_id)
        .values(last_seen_at=func.now(), lifecycle_status="engaged", updated_at=func.now())
    )
    await db.commit()


async def _get_lead_for_conversation(db: AsyncSession, conversation: Conversation) -> Lead:
    result = await db.execute(
        select(Lead).where(Lead.id == conversation.lead_id, Lead.tenant_id == conversation.tenant_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise ValueError(f"Lead not found for conversation {conversation.id}")
    return lead


def _preview_text(content: str, max_length: int = 72) -> str:
    compact = " ".join(content.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 1]}…"


def _derive_pipeline_status(conversation: Conversation, lead: Lead, latest_message: Message | None) -> str:
    if conversation.pipeline_status:
        return conversation.pipeline_status
    status = (conversation.status or "").lower()
    lifecycle = (lead.lifecycle_status or "").lower()
    preview = (latest_message.content if latest_message else "").lower()

    if status in {"waiting_human", "handoff"} or lifecycle in {"handoff", "waiting_human"}:
        return "handoff"
    if status == "closed" or lifecycle in {"lost", "disqualified", "invalid"}:
        return "disqualified"
    if "agend" in preview or "reuni" in preview or "visita" in preview:
        return "scheduled"
    if latest_message is None:
        return "new"
    return "qualifying"


def _derive_summary(conversation: Conversation, lead: Lead, latest_message: Message | None) -> str | None:
    if conversation.summary:
        return conversation.summary
    if latest_message and latest_message.content:
        return _preview_text(latest_message.content, max_length=160)
    if lead.name:
        return f"Lead {lead.name} entrou pelo canal {conversation.channel} e ainda nao tem resumo operacional."
    return f"Lead entrou pelo canal {conversation.channel} e ainda nao tem resumo operacional."


def _derive_next_step(pipeline_status: str, latest_message: Message | None) -> str:
    if latest_message and latest_message.metadata_json:
        suggestion = latest_message.metadata_json.get("follow_up_suggestion")
        if isinstance(suggestion, str) and suggestion.strip():
            return suggestion.strip()

    if pipeline_status == "handoff":
        return "Assumir atendimento humano e revisar contexto da conversa."
    if pipeline_status == "scheduled":
        return "Confirmar horario, responsavel e preparar follow-up."
    if pipeline_status == "disqualified":
        return "Registrar motivo da perda e encerrar no funil."
    if pipeline_status == "new":
        return "Fazer primeira qualificacao e captar contexto basico do lead."
    return "Aprofundar necessidade, objeções e conduzir para o proximo passo."


async def persist_conversation_pipeline_fields(
    db: AsyncSession,
    conversation_id: str,
    tenant_id: str,
    *,
    pipeline_status: str,
    summary: str | None,
    next_step: str | None,
    status: str | None = None,
    agent_id: str | None = None,
) -> None:
    values: dict[str, object] = {
        "pipeline_status": pipeline_status,
        "summary": summary,
        "next_step": next_step,
        "updated_at": func.now(),
    }
    if status is not None:
        values["status"] = status
    if agent_id is not None:
        values["agent_id"] = agent_id
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        .values(**values)
    )


async def list_conversations(db: AsyncSession, tenant_id: str) -> list[ConversationSummaryResponse]:
    conversations_result = await db.execute(
        select(Conversation, Lead)
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
            agent_id=conversation.agent_id,
            title=lead.name or lead.phone or lead.external_contact_id or f"Conversa {conversation.id[:8]}",
            channel=conversation.channel,
            status=conversation.status,
            lead_id=conversation.lead_id,
            started_at=conversation.started_at,
            updated_at=conversation.updated_at,
            last_message_preview=(_preview_text(latest_message.content) if latest_message else None),
            summary=_derive_summary(conversation, lead, latest_message),
            pipeline_status=conversation.pipeline_status or pipeline_status,
            next_step=conversation.next_step or _derive_next_step(conversation.pipeline_status or pipeline_status, latest_message),
            message_count=int(count_map.get(conversation.id, 0)),
        )
        for conversation, lead in rows
        for latest_message in [latest_by_conversation.get(conversation.id)]
        for pipeline_status in [_derive_pipeline_status(conversation, lead, latest_message)]
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


async def update_conversation_pipeline_status(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str,
    pipeline_status: str,
) -> ConversationDetailResponse | None:
    conversation = await get_conversation_or_none(db, tenant_id, conversation_id)
    if not conversation:
        return None
    lead = await _get_lead_for_conversation(db, conversation)

    conversation_status = "open"
    lead_lifecycle_status = "engaged"
    if pipeline_status == "handoff":
        conversation_status = "waiting_human"
        lead_lifecycle_status = "handoff"
    elif pipeline_status == "scheduled":
        conversation_status = "open"
        lead_lifecycle_status = "scheduled"
    elif pipeline_status == "disqualified":
        conversation_status = "closed"
        lead_lifecycle_status = "disqualified"
    elif pipeline_status == "new":
        conversation_status = "open"
        lead_lifecycle_status = "new"

    next_step = _derive_next_step(pipeline_status, None)
    await persist_conversation_pipeline_fields(
        db=db,
        conversation_id=conversation.id,
        tenant_id=tenant_id,
        pipeline_status=pipeline_status,
        summary=conversation.summary or _derive_summary(conversation, lead, None),
        next_step=next_step,
        status=conversation_status,
    )
    await db.execute(
        update(Lead)
        .where(Lead.id == conversation.lead_id, Lead.tenant_id == tenant_id)
        .values(lifecycle_status=lead_lifecycle_status, updated_at=func.now())
    )
    await db.commit()
    return await get_conversation_detail(db, tenant_id, conversation_id)
