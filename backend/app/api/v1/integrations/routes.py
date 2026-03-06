from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.integrations import IntegrationCreateRequest, IntegrationResponse, IntegrationUpdateRequest
from app.services.integrations import create_integration, get_integration_or_none, list_integrations, update_integration

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=list[IntegrationResponse])
async def get_integrations(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[IntegrationResponse]:
    integrations = await list_integrations(db, context.tenant_id)
    return [IntegrationResponse.model_validate(item) for item in integrations]


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def post_integration(
    payload: IntegrationCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> IntegrationResponse:
    integration = await create_integration(db, context.tenant_id, payload)
    return IntegrationResponse.model_validate(integration)


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def patch_integration(
    integration_id: str,
    payload: IntegrationUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> IntegrationResponse:
    integration = await get_integration_or_none(db, context.tenant_id, integration_id)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    updated = await update_integration(db, integration, payload)
    return IntegrationResponse.model_validate(updated)
