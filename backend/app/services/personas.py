from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.db import SessionLocal
from app.models.entities import AgentVersion, BotPersona, PersonaVersion
from app.schemas.personas import PersonaCreateRequest, PersonaVersionCreateRequest
from app.services.agents import get_default_agent_or_none, get_persona_version_for_agent, get_published_agent_version_or_none


async def list_personas(db: AsyncSession, tenant_id: str) -> list[BotPersona]:
    result = await db.execute(
        select(BotPersona).where(BotPersona.tenant_id == tenant_id, BotPersona.deleted_at.is_(None)).order_by(BotPersona.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_persona_or_none(db: AsyncSession, tenant_id: str, persona_id: str) -> BotPersona | None:
    result = await db.execute(
        select(BotPersona).where(
            BotPersona.tenant_id == tenant_id,
            BotPersona.id == persona_id,
            BotPersona.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_persona_versions(db: AsyncSession, tenant_id: str, persona_id: str) -> list[PersonaVersion]:
    result = await db.execute(
        select(PersonaVersion)
        .where(PersonaVersion.tenant_id == tenant_id, PersonaVersion.persona_id == persona_id)
        .order_by(PersonaVersion.version_no.desc())
    )
    return list(result.scalars().all())


async def _create_persona_version(
    db: AsyncSession,
    tenant_id: str,
    persona: BotPersona,
    user_id: str,
    payload: PersonaVersionCreateRequest,
    version_no: int,
) -> PersonaVersion:
    version = PersonaVersion(
        id=str(uuid4()),
        tenant_id=tenant_id,
        persona_id=persona.id,
        version_no=version_no,
        tone=payload.tone,
        approach_rules_json={"rules": payload.approach_rules},
        objection_playbook_json=payload.objection_playbook,
        prompt_system=payload.prompt_system,
        is_published=payload.publish,
        created_by_user_id=user_id,
    )
    db.add(version)
    await db.flush()
    if payload.publish:
        persona.active_version_no = version.version_no
    return version


async def create_persona(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    payload: PersonaCreateRequest,
) -> BotPersona:
    persona = BotPersona(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        active_version_no=1 if payload.publish else None,
        is_active=True,
    )
    db.add(persona)
    await db.flush()
    await _create_persona_version(
        db,
        tenant_id=tenant_id,
        persona=persona,
        user_id=user_id,
        payload=PersonaVersionCreateRequest(
            tone=payload.tone,
            prompt_system=payload.prompt_system,
            approach_rules=payload.approach_rules,
            objection_playbook=payload.objection_playbook,
            publish=payload.publish,
        ),
        version_no=1,
    )
    await db.commit()
    await db.refresh(persona)
    return persona


async def create_persona_version(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    persona: BotPersona,
    payload: PersonaVersionCreateRequest,
) -> PersonaVersion:
    versions = await list_persona_versions(db, tenant_id, persona.id)
    next_version_no = (versions[0].version_no if versions else 0) + 1
    version = await _create_persona_version(db, tenant_id, persona, user_id, payload, next_version_no)
    await db.commit()
    await db.refresh(version)
    return version


async def publish_persona_version(
    db: AsyncSession,
    tenant_id: str,
    persona: BotPersona,
    version_no: int,
) -> PersonaVersion | None:
    result = await db.execute(
        select(PersonaVersion).where(
            PersonaVersion.tenant_id == tenant_id,
            PersonaVersion.persona_id == persona.id,
            PersonaVersion.version_no == version_no,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        return None

    version.is_published = True
    persona.active_version_no = version.version_no
    await db.execute(
        select(PersonaVersion).where(
            PersonaVersion.tenant_id == tenant_id,
            PersonaVersion.persona_id == persona.id,
        )
    )
    versions = await list_persona_versions(db, tenant_id, persona.id)
    for item in versions:
        item.is_published = item.id == version.id
    await db.commit()
    await db.refresh(version)
    return version


async def get_persona_context_for_agent(
    tenant_id: str,
    agent_id: str | None,
) -> dict[str, str] | None:
    async with SessionLocal() as session:
        agent_version: AgentVersion | None = None
        if agent_id:
            agent_version = await get_published_agent_version_or_none(session, tenant_id, agent_id)
        if not agent_version:
            default_agent = await get_default_agent_or_none(session, tenant_id)
            if default_agent:
                agent_version = await get_published_agent_version_or_none(session, tenant_id, default_agent.id)
        if not agent_version:
            return None
        version = await get_persona_version_for_agent(session, tenant_id, agent_version)
        if not version:
            return None
        persona = await get_persona_or_none(session, tenant_id, version.persona_id)
        if not persona:
            return None
        return {
            "persona_name": persona.name,
            "tone": version.tone,
            "prompt_system": version.prompt_system,
            "approach_rules": "; ".join(version.approach_rules_json.get("rules", [])),
            "objection_playbook": "; ".join(
                [f"{key}: {value}" for key, value in version.objection_playbook_json.items()]
            ),
        }


async def get_active_persona_context(tenant_id: str) -> dict[str, str] | None:
    return await get_persona_context_for_agent(tenant_id, None)
