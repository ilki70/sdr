from __future__ import annotations

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
from app.schemas.training import AgentTrainingRequest, AgentTrainingResponse
from app.schemas.training import AgentImprovementResponse, ConversationImprovementRequest, ConversationImprovementResponse
from app.services.agent_improvements import get_agent_improvement_or_none, revert_agent_improvement
from app.services.agents import (
    count_active_agents,
    create_agent,
    create_agent_version,
    delete_agent,
    get_consorcio_studio_state,
    get_agent_or_none,
    list_agents,
    list_agent_versions,
    publish_agent_version,
    update_consorcio_studio,
    update_agent,
)
from app.services.training import get_agent_improvement_history, run_agent_training, run_conversation_improvement_review

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
    try:
        agent = await create_agent(db, context.tenant_id, context.user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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
    try:
        version = await create_agent_version(db, context.tenant_id, context.user_id, agent, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AgentVersionResponse.model_validate(version)


@router.delete("/{agent_id}", response_model=AgentResponse)
async def delete_agent_route(
    agent_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    remaining = await count_active_agents(db, context.tenant_id, exclude_agent_id=agent.id)
    if remaining == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keep at least one active agent in the tenant",
        )
    deleted = await delete_agent(db, agent)
    return AgentResponse.model_validate(deleted)


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


@router.post("/{agent_id}/training", response_model=AgentTrainingResponse)
async def post_agent_training(
    agent_id: str,
    payload: AgentTrainingRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentTrainingResponse:
    try:
        return await run_agent_training(db, context.tenant_id, context.user_id, agent_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{agent_id}/conversation-improvements", response_model=ConversationImprovementResponse)
async def post_conversation_improvements(
    agent_id: str,
    payload: ConversationImprovementRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationImprovementResponse:
    try:
        return await run_conversation_improvement_review(db, context.tenant_id, context.user_id, agent_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{agent_id}/improvements", response_model=list[AgentImprovementResponse])
async def get_agent_improvements(
    agent_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[AgentImprovementResponse]:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return await get_agent_improvement_history(db, context.tenant_id, agent.id)


@router.post("/{agent_id}/improvements/{improvement_id}/revert", response_model=AgentImprovementResponse)
async def post_revert_agent_improvement(
    agent_id: str,
    improvement_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentImprovementResponse:
    agent = await get_agent_or_none(db, context.tenant_id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    improvement = await get_agent_improvement_or_none(db, context.tenant_id, agent.id, improvement_id)
    if not improvement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Improvement not found")
    reverted = await revert_agent_improvement(
        db,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        agent=agent,
        improvement=improvement,
    )
    return AgentImprovementResponse.model_validate(reverted)
