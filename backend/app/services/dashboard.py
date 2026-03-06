from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ChannelIntegration, Client, Conversation, Lead, Message, Product, Sale
from app.schemas.dashboard import (
    DashboardLatestEvaluationResponse,
    DashboardOverviewResponse,
    DashboardRecentConversationResponse,
    DashboardRecentJobResponse,
)
from app.services.commissions import list_rules
from app.services.knowledge_ops import get_latest_evaluation_run, list_knowledge_jobs
from app.services.messages import list_conversations


async def _count_rows(db: AsyncSession, entity, tenant_id: str, include_deleted: bool = False) -> int:
    query = select(func.count(entity.id)).where(entity.tenant_id == tenant_id)
    if not include_deleted and hasattr(entity, "deleted_at"):
        query = query.where(entity.deleted_at.is_(None))
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def _sales_totals(db: AsyncSession, tenant_id: str) -> tuple[int, Decimal]:
    result = await db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.amount), 0))
        .where(Sale.tenant_id == tenant_id, Sale.deleted_at.is_(None))
    )
    sales_count, revenue_total = result.one()
    return int(sales_count or 0), Decimal(revenue_total or 0)


async def _conversation_health_metrics(db: AsyncSession, tenant_id: str) -> tuple[int, int, float]:
    conversation_result = await db.execute(
        select(Conversation.id).where(Conversation.tenant_id == tenant_id)
    )
    conversation_ids = [conversation_id for conversation_id in conversation_result.scalars().all()]
    if not conversation_ids:
        return 0, 0, 0.0

    counts_result = await db.execute(
        select(Message.conversation_id, func.count(Message.id))
        .where(Message.tenant_id == tenant_id, Message.conversation_id.in_(conversation_ids))
        .group_by(Message.conversation_id)
    )
    count_map = {conversation_id: int(count) for conversation_id, count in counts_result.all()}

    result = await db.execute(
        select(Message.conversation_id, Message.metadata_json)
        .where(
            Message.tenant_id == tenant_id,
            Message.sender_type == "assistant",
            Message.conversation_id.in_(conversation_ids),
        )
        .order_by(Message.sent_at.desc(), Message.created_at.desc())
    )

    latest_assistant_meta: dict[str, dict | None] = {}
    for conversation_id, metadata_json in result.all():
        latest_assistant_meta.setdefault(conversation_id, metadata_json or {})

    qualification_started_count = sum(1 for conversation_id in conversation_ids if count_map.get(conversation_id, 0) >= 2)
    handoff_ready_count = sum(
        1
        for conversation_id in conversation_ids
        if count_map.get(conversation_id, 0) >= 4
        or bool((latest_assistant_meta.get(conversation_id) or {}).get("follow_up_suggestion"))
    )
    total_messages = sum(count_map.values())
    avg_messages_per_conversation = round(
        total_messages / max(len(conversation_ids), 1),
        2,
    )
    return qualification_started_count, handoff_ready_count, avg_messages_per_conversation


async def get_dashboard_overview(db: AsyncSession, tenant_id: str) -> DashboardOverviewResponse:
    lead_count = await _count_rows(db, Lead, tenant_id)
    client_count = await _count_rows(db, Client, tenant_id)
    product_count = await _count_rows(db, Product, tenant_id)
    conversation_count = await _count_rows(db, Conversation, tenant_id, include_deleted=True)
    active_integration_count = await _count_rows(db, ChannelIntegration, tenant_id)
    rules = await list_rules(db, tenant_id)
    recent_jobs = await list_knowledge_jobs(db, tenant_id, limit=6)
    recent_conversations = (await list_conversations(db, tenant_id))[:5]
    qualification_started_count, handoff_ready_count, avg_messages_per_conversation = await _conversation_health_metrics(db, tenant_id)
    latest_evaluation = await get_latest_evaluation_run(db, tenant_id)
    sales_count, revenue_total = await _sales_totals(db, tenant_id)
    engaged_result = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id,
            Lead.deleted_at.is_(None),
            Lead.lifecycle_status.in_(["engaged", "qualified", "proposal", "won"]),
        )
    )
    engaged_lead_count = int(engaged_result.scalar() or 0)

    return DashboardOverviewResponse(
        lead_count=lead_count,
        engaged_lead_count=engaged_lead_count,
        client_count=client_count,
        product_count=product_count,
        conversation_count=conversation_count,
        qualification_started_count=qualification_started_count,
        handoff_ready_count=handoff_ready_count,
        avg_messages_per_conversation=avg_messages_per_conversation,
        active_rule_count=sum(1 for rule in rules if rule.is_active),
        active_integration_count=active_integration_count,
        sales_count=sales_count,
        revenue_total=revenue_total,
        recent_jobs=[
            DashboardRecentJobResponse(
                id=job.id,
                job_type=job.job_type,
                status=job.status,
                created_at=job.created_at,
                product_id=job.product_id,
            )
            for job in recent_jobs
        ],
        recent_conversations=[
            DashboardRecentConversationResponse(
                id=item.id,
                title=item.title,
                status=item.status,
                updated_at=item.updated_at,
                message_count=item.message_count,
                last_message_preview=item.last_message_preview,
            )
            for item in recent_conversations
        ],
        latest_evaluation=(
            DashboardLatestEvaluationResponse(
                id=latest_evaluation.id,
                evaluation_type=latest_evaluation.evaluation_type,
                status=latest_evaluation.status,
                summary_json=latest_evaluation.summary_json,
                created_at=latest_evaluation.created_at,
            )
            if latest_evaluation
            else None
        ),
    )
