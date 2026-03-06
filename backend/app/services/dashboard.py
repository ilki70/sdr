from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ChannelIntegration, Client, Conversation, Product, Sale
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


async def get_dashboard_overview(db: AsyncSession, tenant_id: str) -> DashboardOverviewResponse:
    client_count = await _count_rows(db, Client, tenant_id)
    product_count = await _count_rows(db, Product, tenant_id)
    conversation_count = await _count_rows(db, Conversation, tenant_id, include_deleted=True)
    active_integration_count = await _count_rows(db, ChannelIntegration, tenant_id)
    rules = await list_rules(db, tenant_id)
    recent_jobs = await list_knowledge_jobs(db, tenant_id, limit=6)
    recent_conversations = (await list_conversations(db, tenant_id))[:5]
    latest_evaluation = await get_latest_evaluation_run(db, tenant_id)
    sales_count, revenue_total = await _sales_totals(db, tenant_id)

    return DashboardOverviewResponse(
        client_count=client_count,
        product_count=product_count,
        conversation_count=conversation_count,
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
