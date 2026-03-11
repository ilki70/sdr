from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Agent, AgentVersion, BotPersona, PersonaVersion
from app.schemas.agents import AgentCreateRequest, AgentUpdateRequest, AgentVersionCreateRequest


async def list_agents(db: AsyncSession, tenant_id: str) -> list[Agent]:
    result = await db.execute(
        select(Agent)
        .where(Agent.tenant_id == tenant_id, Agent.deleted_at.is_(None))
        .order_by(Agent.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_agent_or_none(db: AsyncSession, tenant_id: str, agent_id: str) -> Agent | None:
    result = await db.execute(
        select(Agent).where(
            Agent.tenant_id == tenant_id,
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_agent_by_slug_or_none(db: AsyncSession, tenant_id: str, slug: str) -> Agent | None:
    result = await db.execute(
        select(Agent).where(
            Agent.tenant_id == tenant_id,
            Agent.slug == slug,
            Agent.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_agent_versions(db: AsyncSession, tenant_id: str, agent_id: str) -> list[AgentVersion]:
    result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.tenant_id == tenant_id, AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version_no.desc())
    )
    return list(result.scalars().all())


async def _resolve_persona_version_no(
    db: AsyncSession,
    tenant_id: str,
    persona_id: str | None,
    persona_version_no: int | None,
) -> int | None:
    if not persona_id:
        return None
    if persona_version_no is not None:
        return persona_version_no

    result = await db.execute(
        select(BotPersona).where(
            BotPersona.tenant_id == tenant_id,
            BotPersona.id == persona_id,
            BotPersona.deleted_at.is_(None),
        )
    )
    persona = result.scalar_one_or_none()
    return persona.active_version_no if persona else None


async def _create_agent_version(
    db: AsyncSession,
    tenant_id: str,
    agent: Agent,
    user_id: str,
    payload: AgentVersionCreateRequest,
    version_no: int,
) -> AgentVersion:
    resolved_persona_version_no = await _resolve_persona_version_no(
        db,
        tenant_id,
        payload.persona_id,
        payload.persona_version_no,
    )
    version = AgentVersion(
        id=str(uuid4()),
        tenant_id=tenant_id,
        agent_id=agent.id,
        version_no=version_no,
        persona_id=payload.persona_id,
        persona_version_no=resolved_persona_version_no,
        prompt_system=payload.prompt_system,
        policy_json=payload.policy_json or {},
        tool_config_json=payload.tool_config_json or {},
        knowledge_config_json=payload.knowledge_config_json or {},
        channel_config_json=payload.channel_config_json or {},
        is_published=payload.publish,
        created_by_user_id=user_id,
    )
    db.add(version)
    await db.flush()
    if payload.publish:
        agent.active_version_no = version.version_no
    return version


async def ensure_default_agent_for_tenant(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
) -> Agent:
    existing = await get_default_agent_or_none(db, tenant_id)
    if existing:
        return existing

    result = await db.execute(
        select(BotPersona)
        .where(BotPersona.tenant_id == tenant_id, BotPersona.deleted_at.is_(None), BotPersona.is_active.is_(True))
        .order_by(BotPersona.created_at.asc())
        .limit(1)
    )
    persona = result.scalar_one_or_none()
    payload = AgentCreateRequest(
        name="Vinac Consorcios",
        slug="vinac-consorcios",
        description="Agente inicial migrado do tenant atual.",
        persona_id=persona.id if persona else None,
        persona_version_no=persona.active_version_no if persona else None,
        prompt_system=(
            "Voce e o agente comercial inicial deste tenant. "
            "Atenda com tom consultivo, claro, sustentado pelo contexto oficial e orientado a proximo passo."
        ),
        policy_json={"rules": ["use contexto oficial", "nao invente fatos", "sempre proponha proximo passo"]},
        tool_config_json={"rag_enabled": True, "web_allowlist_enabled": True},
        knowledge_config_json={"scope": "tenant_default"},
        channel_config_json={"default_channel": "lab"},
        publish=True,
    )
    return await create_agent(db, tenant_id, user_id, payload)


async def create_agent(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    payload: AgentCreateRequest,
) -> Agent:
    agent = Agent(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        active_version_no=1 if payload.publish else None,
        status="active",
        created_by_user_id=user_id,
    )
    db.add(agent)
    await db.flush()
    await _create_agent_version(
        db,
        tenant_id=tenant_id,
        agent=agent,
        user_id=user_id,
        payload=AgentVersionCreateRequest(
            persona_id=payload.persona_id,
            persona_version_no=payload.persona_version_no,
            prompt_system=payload.prompt_system,
            policy_json=payload.policy_json,
            tool_config_json=payload.tool_config_json,
            knowledge_config_json=payload.knowledge_config_json,
            channel_config_json=payload.channel_config_json,
            publish=payload.publish,
        ),
        version_no=1,
    )
    await db.commit()
    await db.refresh(agent)
    return agent


async def update_agent(db: AsyncSession, agent: Agent, payload: AgentUpdateRequest) -> Agent:
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and payload.name:
        agent.name = payload.name
    if "slug" in changes and payload.slug:
        agent.slug = payload.slug
    if "description" in changes:
        agent.description = payload.description
    if "status" in changes and payload.status:
        agent.status = payload.status
    await db.commit()
    await db.refresh(agent)
    return agent


async def create_agent_version(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    agent: Agent,
    payload: AgentVersionCreateRequest,
) -> AgentVersion:
    versions = await list_agent_versions(db, tenant_id, agent.id)
    next_version_no = (versions[0].version_no if versions else 0) + 1
    version = await _create_agent_version(db, tenant_id, agent, user_id, payload, next_version_no)
    await db.commit()
    await db.refresh(version)
    return version


async def publish_agent_version(
    db: AsyncSession,
    tenant_id: str,
    agent: Agent,
    version_no: int,
) -> AgentVersion | None:
    result = await db.execute(
        select(AgentVersion).where(
            AgentVersion.tenant_id == tenant_id,
            AgentVersion.agent_id == agent.id,
            AgentVersion.version_no == version_no,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        return None

    version.is_published = True
    agent.active_version_no = version.version_no
    versions = await list_agent_versions(db, tenant_id, agent.id)
    for item in versions:
        item.is_published = item.id == version.id
    await db.commit()
    await db.refresh(version)
    return version


async def get_published_agent_version_or_none(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
) -> AgentVersion | None:
    agent = await get_agent_or_none(db, tenant_id, agent_id)
    if not agent or agent.active_version_no is None:
        return None
    result = await db.execute(
        select(AgentVersion).where(
            AgentVersion.tenant_id == tenant_id,
            AgentVersion.agent_id == agent_id,
            AgentVersion.version_no == agent.active_version_no,
        )
    )
    return result.scalar_one_or_none()


async def get_default_agent_or_none(db: AsyncSession, tenant_id: str) -> Agent | None:
    result = await db.execute(
        select(Agent)
        .where(Agent.tenant_id == tenant_id, Agent.deleted_at.is_(None), Agent.status == "active")
        .order_by(Agent.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def resolve_agent_for_conversation(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str | None = None,
) -> Agent | None:
    if agent_id:
        return await get_agent_or_none(db, tenant_id, agent_id)
    return await get_default_agent_or_none(db, tenant_id)


async def get_persona_version_for_agent(
    db: AsyncSession,
    tenant_id: str,
    agent_version: AgentVersion,
) -> PersonaVersion | None:
    if not agent_version.persona_id or agent_version.persona_version_no is None:
        return None
    result = await db.execute(
        select(PersonaVersion).where(
            PersonaVersion.tenant_id == tenant_id,
            PersonaVersion.persona_id == agent_version.persona_id,
            PersonaVersion.version_no == agent_version.persona_version_no,
        )
    )
    return result.scalar_one_or_none()
