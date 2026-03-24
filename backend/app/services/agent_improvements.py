from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow_naive
from app.models.entities import Agent, AgentImprovement
from app.services.agents import publish_agent_version
from app.services.personas import get_persona_or_none, publish_persona_version


async def create_agent_improvement(
    db: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
    created_by_user_id: str,
    source_type: str,
    title: str,
    status: str,
    summary_text: str | None,
    findings_json: dict | None,
    recommendations_json: dict | None,
    sample_conversation_ids_json: dict | None,
    evaluation_run_id: str | None = None,
    base_agent_version_no: int | None = None,
    applied_agent_version_no: int | None = None,
    base_persona_id: str | None = None,
    base_persona_version_no: int | None = None,
    applied_persona_version_no: int | None = None,
) -> AgentImprovement:
    improvement = AgentImprovement(
        id=str(uuid4()),
        tenant_id=tenant_id,
        agent_id=agent_id,
        evaluation_run_id=evaluation_run_id,
        source_type=source_type,
        title=title,
        status=status,
        summary_text=summary_text,
        findings_json=findings_json or {},
        recommendations_json=recommendations_json or {},
        sample_conversation_ids_json=sample_conversation_ids_json or {},
        base_agent_version_no=base_agent_version_no,
        applied_agent_version_no=applied_agent_version_no,
        base_persona_id=base_persona_id,
        base_persona_version_no=base_persona_version_no,
        applied_persona_version_no=applied_persona_version_no,
        created_by_user_id=created_by_user_id,
    )
    db.add(improvement)
    await db.commit()
    await db.refresh(improvement)
    return improvement


async def list_agent_improvements(db: AsyncSession, tenant_id: str, agent_id: str) -> list[AgentImprovement]:
    result = await db.execute(
        select(AgentImprovement)
        .where(
            AgentImprovement.tenant_id == tenant_id,
            AgentImprovement.agent_id == agent_id,
        )
        .order_by(AgentImprovement.created_at.desc())
    )
    return list(result.scalars().all())


async def get_agent_improvement_or_none(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
    improvement_id: str,
) -> AgentImprovement | None:
    result = await db.execute(
        select(AgentImprovement).where(
            AgentImprovement.tenant_id == tenant_id,
            AgentImprovement.agent_id == agent_id,
            AgentImprovement.id == improvement_id,
        )
    )
    return result.scalar_one_or_none()


async def revert_agent_improvement(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    agent: Agent,
    improvement: AgentImprovement,
) -> AgentImprovement:
    if improvement.status == "reverted":
        return improvement

    if improvement.base_persona_id and improvement.base_persona_version_no:
        persona = await get_persona_or_none(db, tenant_id, improvement.base_persona_id)
        if persona:
            reverted_persona = await publish_persona_version(db, tenant_id, persona, improvement.base_persona_version_no)
            if reverted_persona:
                improvement.reverted_persona_version_no = reverted_persona.version_no

    if improvement.base_agent_version_no:
        reverted_agent = await publish_agent_version(db, tenant_id, agent, improvement.base_agent_version_no)
        if reverted_agent:
            improvement.reverted_agent_version_no = reverted_agent.version_no

    improvement.status = "reverted"
    improvement.reverted_by_user_id = user_id
    improvement.reverted_at = utcnow_naive()
    await db.commit()
    await db.refresh(improvement)
    return improvement
