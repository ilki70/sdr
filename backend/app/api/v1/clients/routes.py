from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.clients import ClientCreateRequest, ClientResponse, ClientUpdateRequest
from app.services.clients import create_client, get_client_or_none, list_clients, soft_delete_client, update_client

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientResponse])
async def get_clients(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ClientResponse]:
    return [ClientResponse.model_validate(item) for item in await list_clients(db, context.tenant_id)]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def post_client(
    payload: ClientCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ClientResponse:
    client = await create_client(db, context.tenant_id, payload)
    return ClientResponse.model_validate(client)


@router.patch("/{client_id}", response_model=ClientResponse)
async def patch_client(
    client_id: str,
    payload: ClientUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ClientResponse:
    client = await get_client_or_none(db, context.tenant_id, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    updated = await update_client(db, client, payload)
    return ClientResponse.model_validate(updated)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    client = await get_client_or_none(db, context.tenant_id, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    await soft_delete_client(db, client)
