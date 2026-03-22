from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.personas import (
    PersonaCreateRequest,
    PersonaDetailResponse,
    PersonaResponse,
    PersonaUpdateRequest,
    PersonaVersionCreateRequest,
    PersonaVersionResponse,
)
from app.services.personas import (
    count_agents_using_persona,
    create_persona,
    create_persona_version,
    delete_persona,
    get_persona_or_none,
    list_persona_versions,
    list_personas,
    publish_persona_version,
    update_persona,
)

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[PersonaResponse])
async def get_personas(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[PersonaResponse]:
    personas = await list_personas(db, context.tenant_id)
    return [PersonaResponse.model_validate(item) for item in personas]


@router.post("", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def post_persona(
    payload: PersonaCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> PersonaResponse:
    persona = await create_persona(db, context.tenant_id, context.user_id, payload)
    return PersonaResponse.model_validate(persona)


@router.get("/{persona_id}", response_model=PersonaDetailResponse)
async def get_persona_detail(
    persona_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> PersonaDetailResponse:
    persona = await get_persona_or_none(db, context.tenant_id, persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    versions = await list_persona_versions(db, context.tenant_id, persona.id)
    return PersonaDetailResponse(
        persona=PersonaResponse.model_validate(persona),
        versions=[PersonaVersionResponse.model_validate(item) for item in versions],
    )


@router.patch("/{persona_id}", response_model=PersonaResponse)
async def patch_persona(
    persona_id: str,
    payload: PersonaUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> PersonaResponse:
    persona = await get_persona_or_none(db, context.tenant_id, persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    updated = await update_persona(db, persona, payload)
    return PersonaResponse.model_validate(updated)


@router.post("/{persona_id}/versions", response_model=PersonaVersionResponse, status_code=status.HTTP_201_CREATED)
async def post_persona_version(
    persona_id: str,
    payload: PersonaVersionCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> PersonaVersionResponse:
    persona = await get_persona_or_none(db, context.tenant_id, persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    version = await create_persona_version(db, context.tenant_id, context.user_id, persona, payload)
    return PersonaVersionResponse.model_validate(version)


@router.post("/{persona_id}/versions/{version_no}/publish", response_model=PersonaVersionResponse)
async def post_publish_persona_version(
    persona_id: str,
    version_no: int,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> PersonaVersionResponse:
    persona = await get_persona_or_none(db, context.tenant_id, persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    version = await publish_persona_version(db, context.tenant_id, persona, version_no)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona version not found")
    return PersonaVersionResponse.model_validate(version)


@router.delete("/{persona_id}", response_model=PersonaResponse)
async def delete_persona_route(
    persona_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> PersonaResponse:
    persona = await get_persona_or_none(db, context.tenant_id, persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    linked_agents = await count_agents_using_persona(db, context.tenant_id, persona.id)
    if linked_agents > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unlink this persona from active agents before deleting it",
        )
    deleted = await delete_persona(db, persona)
    return PersonaResponse.model_validate(deleted)
