from uuid import uuid4

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow_naive
from app.models.entities import Client
from app.schemas.clients import ClientCreateRequest, ClientUpdateRequest


def _client_select(tenant_id: str) -> Select[tuple[Client]]:
    return select(Client).where(Client.tenant_id == tenant_id, Client.deleted_at.is_(None))


async def list_clients(db: AsyncSession, tenant_id: str) -> list[Client]:
    result = await db.execute(_client_select(tenant_id).order_by(Client.created_at.desc()))
    return list(result.scalars().all())


async def create_client(db: AsyncSession, tenant_id: str, payload: ClientCreateRequest) -> Client:
    client = Client(id=str(uuid4()), tenant_id=tenant_id, **payload.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def get_client_or_none(db: AsyncSession, tenant_id: str, client_id: str) -> Client | None:
    result = await db.execute(_client_select(tenant_id).where(Client.id == client_id))
    return result.scalar_one_or_none()


async def update_client(db: AsyncSession, client: Client, payload: ClientUpdateRequest) -> Client:
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(client, key, value)
    await db.commit()
    await db.refresh(client)
    return client


async def soft_delete_client(db: AsyncSession, client: Client) -> None:
    client.deleted_at = utcnow_naive()
    await db.commit()
