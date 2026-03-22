from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Agent, AgentVersion, BotPersona, PersonaVersion
from app.schemas.agents import (
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentVersionCreateRequest,
    ConsorcioKnowledgeBlock,
    ConsorcioPlaybookBlock,
    ConsorcioStudioUpdateRequest,
)


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


def _default_playbook_data() -> dict:
    return {
        "positioning": (
            "Voce conduz a qualificacao de consorcio com postura consultiva, "
            "explicando o processo com clareza, sem prometer contemplacao e preparando o handoff humano."
        ),
        "tone": "consultivo",
        "qualification": {
            "intent": "qualificar lead de consorcio",
            "questions": [
                "Qual bem ou objetivo voce quer viabilizar com consorcio?",
                "Qual faixa de parcela cabe no seu planejamento hoje?",
                "Voce quer entrada mais rapida, menor parcela ou maior previsibilidade?",
            ],
            "disqualifiers": [
                "Sem interesse real no planejamento",
                "Apenas curiosidade sem prazo ou objetivo",
            ],
            "required_fields": ["objetivo", "faixa_parcela", "prazo", "urgencia"],
        },
        "objections": [
            {
                "objection": "tempo de contemplacao",
                "response": "Explique que contemplacao nao e garantida e que o foco e alinhar expectativa, prazo e estrategia comercial oficial.",
            },
            {
                "objection": "taxa ou custo",
                "response": "Explique que o custo precisa ser confirmado na proposta oficial e que a comparacao correta considera parcela, prazo e objetivo.",
            },
        ],
        "compliance_rules": [
            "Nao prometer contemplacao",
            "Nao afirmar retorno financeiro",
            "Nao inventar taxa, entrada ou prazo",
            "Escalar para humano quando houver duvida contratual",
        ],
        "handoff_rules": [
            "Encaminhar para humano quando o lead estiver pronto para simulacao",
            "Escalar leads com exigencia de proposta formal",
            "Manter registro do motivo do handoff",
        ],
        "follow_up_rules": [
            "Retomar leads com prazo definido e sem resposta",
            "Reforcar proximo passo objetivo em ate 24 horas",
            "Usar follow-up consultivo, nao insistente",
        ],
    }


def _default_knowledge_data() -> dict:
    return {
        "product_focus": ["consorcio", "turn2c", "operacao comercial interna"],
        "priority_sources": [],
        "official_domains": [],
        "youtube_sources": [],
        "tags": ["consorcio", "playbook", "hand-off", "qualificacao"],
    }


def _default_tool_config() -> dict:
    return {"rag_enabled": True, "web_allowlist_enabled": True, "consorcio_mode": True}


def _default_channel_config() -> dict:
    return {"default_channel": "whatsapp", "allowed_channels": ["whatsapp", "lab"]}


def _merge_consorcio_data(base: dict, override: dict) -> dict:
    merged = dict(base)
    merged.update({key: value for key, value in override.items() if value is not None})
    return merged


def _build_playbook_model(version: AgentVersion | None) -> ConsorcioPlaybookBlock:
    payload = _merge_consorcio_data(_default_playbook_data(), version.policy_json if version else {})
    payload["qualification"] = _merge_consorcio_data(
        _default_playbook_data()["qualification"],
        payload.get("qualification") or {},
    )
    payload["objections"] = payload.get("objections") or []
    payload["compliance_rules"] = payload.get("compliance_rules") or []
    payload["handoff_rules"] = payload.get("handoff_rules") or []
    payload["follow_up_rules"] = payload.get("follow_up_rules") or []
    return ConsorcioPlaybookBlock.model_validate(payload)


def _build_knowledge_model(version: AgentVersion | None) -> ConsorcioKnowledgeBlock:
    payload = _merge_consorcio_data(_default_knowledge_data(), version.knowledge_config_json if version else {})
    payload["product_focus"] = payload.get("product_focus") or []
    payload["priority_sources"] = payload.get("priority_sources") or []
    payload["official_domains"] = payload.get("official_domains") or []
    payload["youtube_sources"] = payload.get("youtube_sources") or []
    payload["tags"] = payload.get("tags") or []
    return ConsorcioKnowledgeBlock.model_validate(payload)


async def _resolve_persona_version_no(
    db: AsyncSession,
    tenant_id: str,
    persona_id: str | None,
    persona_version_no: int | None,
) -> int | None:
    if not persona_id:
        return None

    result = await db.execute(
        select(BotPersona).where(
            BotPersona.tenant_id == tenant_id,
            BotPersona.id == persona_id,
            BotPersona.deleted_at.is_(None),
            BotPersona.is_active.is_(True),
        )
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise ValueError("Persona not found")
    if persona_version_no is not None:
        version_result = await db.execute(
            select(PersonaVersion).where(
                PersonaVersion.tenant_id == tenant_id,
                PersonaVersion.persona_id == persona_id,
                PersonaVersion.version_no == persona_version_no,
            )
        )
        version = version_result.scalar_one_or_none()
        if not version:
            raise ValueError("Persona version not found")
        return version.version_no
    if persona.active_version_no is None:
        raise ValueError("Persona has no published version")
    return persona.active_version_no


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
        name="Consorcios Operacao",
        slug="consorcios-operacao",
        description="Agente inicial da operacao interna de consorcios.",
        persona_id=persona.id if persona else None,
        persona_version_no=persona.active_version_no if persona else None,
        prompt_system=(
            "Voce e o agente comercial inicial deste tenant para operacao interna de consorcios. "
            "Atenda com tom consultivo, claro, sustentado pelo contexto oficial e orientado a proximo passo."
        ),
        policy_json={
            "positioning": "qualificacao e handoff de leads de consorcio",
            "rules": ["use contexto oficial", "nao invente fatos", "sempre proponha proximo passo"],
        },
        tool_config_json={"rag_enabled": True, "web_allowlist_enabled": True, "consorcio_mode": True},
        knowledge_config_json={"scope": "consorcio_default"},
        channel_config_json={"default_channel": "whatsapp"},
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


async def delete_agent(
    db: AsyncSession,
    agent: Agent,
) -> Agent:
    agent.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    agent.status = "archived"
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


async def count_active_agents(db: AsyncSession, tenant_id: str, exclude_agent_id: str | None = None) -> int:
    conditions = [Agent.tenant_id == tenant_id, Agent.deleted_at.is_(None)]
    if exclude_agent_id:
        conditions.append(Agent.id != exclude_agent_id)
    result = await db.execute(select(func.count()).select_from(Agent).where(*conditions))
    return int(result.scalar_one())


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


async def get_consorcio_studio_state(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
) -> tuple[Agent, AgentVersion | None, ConsorcioPlaybookBlock, ConsorcioKnowledgeBlock]:
    agent = await get_agent_or_none(db, tenant_id, agent_id)
    if not agent:
        raise ValueError("Agent not found")
    active_version = None
    if agent.active_version_no is not None:
        result = await db.execute(
            select(AgentVersion).where(
                AgentVersion.tenant_id == tenant_id,
                AgentVersion.agent_id == agent.id,
                AgentVersion.version_no == agent.active_version_no,
            )
        )
        active_version = result.scalar_one_or_none()
    return agent, active_version, _build_playbook_model(active_version), _build_knowledge_model(active_version)


async def update_consorcio_studio(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    agent: Agent,
    payload: ConsorcioStudioUpdateRequest,
) -> AgentVersion:
    current_version = await get_published_agent_version_or_none(db, tenant_id, agent.id)
    if payload.name or payload.description is not None:
        await update_agent(
            db,
            agent,
            AgentUpdateRequest(
                name=payload.name,
                description=payload.description,
                slug=None,
                status=None,
            ),
        )

    playbook_json = payload.playbook.model_dump()
    knowledge_json = _merge_consorcio_data(
        _default_knowledge_data() if current_version is None else current_version.knowledge_config_json,
        payload.knowledge.model_dump(),
    )
    tool_config_json = _merge_consorcio_data(
        _default_tool_config() if current_version is None else current_version.tool_config_json,
        payload.tool_config_json,
    )
    channel_config_json = _merge_consorcio_data(
        _default_channel_config() if current_version is None else current_version.channel_config_json,
        payload.channel_config_json,
    )
    version_payload = AgentVersionCreateRequest(
        persona_id=current_version.persona_id if current_version else None,
        persona_version_no=current_version.persona_version_no if current_version else None,
        prompt_system=payload.prompt_system,
        policy_json=playbook_json,
        tool_config_json=tool_config_json,
        knowledge_config_json=knowledge_json,
        channel_config_json=channel_config_json,
        publish=payload.publish,
    )
    return await create_agent_version(db, tenant_id, user_id, agent, version_payload)
