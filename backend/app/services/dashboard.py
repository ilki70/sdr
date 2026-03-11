from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Agent, ChannelIntegration, Client, Conversation, Product, Sale
from app.schemas.dashboard import (
    DashboardAgentMetricResponse,
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


async def _list_agent_metrics(db: AsyncSession, tenant_id: str) -> list[DashboardAgentMetricResponse]:
    agents_result = await db.execute(
        select(Agent)
        .where(Agent.tenant_id == tenant_id, Agent.deleted_at.is_(None))
        .order_by(Agent.created_at.asc())
    )
    agents = list(agents_result.scalars().all())
    if not agents:
        return []

    conversations_result = await db.execute(
        select(
            Conversation.agent_id,
            func.count(Conversation.id),
            func.sum(case((Conversation.status == "open", 1), else_=0)),
            func.max(Conversation.updated_at),
        )
        .where(Conversation.tenant_id == tenant_id, Conversation.agent_id.is_not(None))
        .group_by(Conversation.agent_id)
    )
    conversation_map = {
        agent_id: {
            "conversation_count": int(conversation_count or 0),
            "open_conversation_count": int(open_conversation_count or 0),
            "last_activity_at": last_activity_at,
        }
        for agent_id, conversation_count, open_conversation_count, last_activity_at in conversations_result.all()
    }

    integrations_result = await db.execute(
        select(ChannelIntegration.agent_id, func.count(ChannelIntegration.id))
        .where(
            ChannelIntegration.tenant_id == tenant_id,
            ChannelIntegration.deleted_at.is_(None),
            ChannelIntegration.agent_id.is_not(None),
        )
        .group_by(ChannelIntegration.agent_id)
    )
    integration_map = {
        agent_id: int(integration_count or 0) for agent_id, integration_count in integrations_result.all()
    }

    metrics = [
        DashboardAgentMetricResponse(
            agent_id=agent.id,
            name=agent.name,
            slug=agent.slug,
            conversation_count=conversation_map.get(agent.id, {}).get("conversation_count", 0),
            open_conversation_count=conversation_map.get(agent.id, {}).get("open_conversation_count", 0),
            integration_count=integration_map.get(agent.id, 0),
            last_activity_at=conversation_map.get(agent.id, {}).get("last_activity_at"),
        )
        for agent in agents
    ]
    metrics.sort(
        key=lambda item: (
            item.conversation_count,
            item.integration_count,
            item.last_activity_at or datetime.min,
        ),
        reverse=True,
    )
    return metrics


async def get_dashboard_overview(db: AsyncSession, tenant_id: str) -> DashboardOverviewResponse:
    client_count = await _count_rows(db, Client, tenant_id)
    product_count = await _count_rows(db, Product, tenant_id)
    conversation_count = await _count_rows(db, Conversation, tenant_id, include_deleted=True)
    active_integration_count = await _count_rows(db, ChannelIntegration, tenant_id)
    rules = await list_rules(db, tenant_id)
    recent_jobs = await list_knowledge_jobs(db, tenant_id, limit=6)
    recent_conversations = (await list_conversations(db, tenant_id))[:5]
    agent_metrics = await _list_agent_metrics(db, tenant_id)
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
                agent_id=item.agent_id,
                title=item.title,
                status=item.status,
                updated_at=item.updated_at,
                message_count=item.message_count,
                last_message_preview=item.last_message_preview,
            )
            for item in recent_conversations
        ],
        agent_metrics=agent_metrics,
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
