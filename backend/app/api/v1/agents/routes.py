from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.agents import (
    AgentCreateRequest,
    AgentDetailResponse,
    AgentResponse,
    AgentUpdateRequest,
    AgentVersionCreateRequest,
    AgentVersionResponse,
    ConsorcioStudioResponse,
    ConsorcioStudioUpdateRequest,
)
from app.services.agents import (
    create_agent,
    create_agent_version,
    get_consorcio_studio_state,
    get_agent_or_none,
    list_agents,
    list_agent_versions,
    publish_agent_version,
    update_consorcio_studio,
    update_agent,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def get_agents(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[AgentResponse]:
    agents = await list_agents(db, context.tenant_id)
    return [AgentResponse.model_validate(item) for item in agents]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def post_agent(
    payload: AgentCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    agent = await create_agent(db, context.tenant_id, context.user_id, payload)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent_detail(
    agent_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentDetailResponse:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    versions = await list_agent_versions(db, context.tenant_id, agent.id)
    return AgentDetailResponse(
        agent=AgentResponse.model_validate(agent),
        versions=[AgentVersionResponse.model_validate(item) for item in versions],
    )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def patch_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    updated = await update_agent(db, agent, payload)
    return AgentResponse.model_validate(updated)


@router.post("/{agent_id}/versions", response_model=AgentVersionResponse, status_code=status.HTTP_201_CREATED)
async def post_agent_version(
    agent_id: str,
    payload: AgentVersionCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentVersionResponse:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    version = await create_agent_version(db, context.tenant_id, context.user_id, agent, payload)
    return AgentVersionResponse.model_validate(version)


@router.post("/{agent_id}/versions/{version_no}/publish", response_model=AgentVersionResponse)
async def post_publish_agent_version(
    agent_id: str,
    version_no: int,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentVersionResponse:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    version = await publish_agent_version(db, context.tenant_id, agent, version_no)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
    return AgentVersionResponse.model_validate(version)


@router.get("/{agent_id}/consorcio-studio", response_model=ConsorcioStudioResponse)
async def get_consorcio_studio(
    agent_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ConsorcioStudioResponse:
    try:
        agent, active_version, playbook, knowledge = await get_consorcio_studio_state(db, context.tenant_id, agent_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found") from None
    return ConsorcioStudioResponse(
        agent=AgentResponse.model_validate(agent),
        active_version=AgentVersionResponse.model_validate(active_version) if active_version else None,
        playbook=playbook,
        knowledge=knowledge,
    )


@router.patch("/{agent_id}/consorcio-studio", response_model=ConsorcioStudioResponse)
async def patch_consorcio_studio(
    agent_id: str,
    payload: ConsorcioStudioUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ConsorcioStudioResponse:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    version = await update_consorcio_studio(db, context.tenant_id, context.user_id, agent, payload)
    refreshed = await get_consorcio_studio_state(db, context.tenant_id, agent_id)
    agent_ref, active_version, playbook, knowledge = refreshed
    if not active_version:
        active_version = version
    return ConsorcioStudioResponse(
        agent=AgentResponse.model_validate(agent_ref),
        active_version=AgentVersionResponse.model_validate(active_version) if active_version else None,
        playbook=playbook,
        knowledge=knowledge,
    )
