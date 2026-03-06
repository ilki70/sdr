from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ChannelIntegration
from app.schemas.integrations import IntegrationCreateRequest, IntegrationUpdateRequest


async def list_integrations(db: AsyncSession, tenant_id: str) -> list[ChannelIntegration]:
    result = await db.execute(
        select(ChannelIntegration)
        .where(ChannelIntegration.tenant_id == tenant_id, ChannelIntegration.deleted_at.is_(None))
        .order_by(ChannelIntegration.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_integration_or_none(
    db: AsyncSession,
    tenant_id: str,
    integration_id: str,
) -> ChannelIntegration | None:
    result = await db.execute(
        select(ChannelIntegration).where(
            ChannelIntegration.tenant_id == tenant_id,
            ChannelIntegration.id == integration_id,
            ChannelIntegration.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_integration(
    db: AsyncSession,
    tenant_id: str,
    payload: IntegrationCreateRequest,
) -> ChannelIntegration:
    integration = ChannelIntegration(
        id=str(uuid4()),
        tenant_id=tenant_id,
        provider=payload.provider,
        inbox_ref=payload.inbox_ref,
        api_base_url=payload.api_base_url.rstrip("/"),
        webhook_secret_enc=payload.webhook_secret.encode("utf-8"),
        config_json=payload.config_json,
        status=payload.status,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


async def update_integration(
    db: AsyncSession,
    integration: ChannelIntegration,
    payload: IntegrationUpdateRequest,
) -> ChannelIntegration:
    changes = payload.model_dump(exclude_unset=True)
    if "inbox_ref" in changes and payload.inbox_ref:
        integration.inbox_ref = payload.inbox_ref
    if "api_base_url" in changes and payload.api_base_url:
        integration.api_base_url = payload.api_base_url.rstrip("/")
    if "webhook_secret" in changes and payload.webhook_secret:
        integration.webhook_secret_enc = payload.webhook_secret.encode("utf-8")
    if "config_json" in changes:
        integration.config_json = payload.config_json
    if "status" in changes and payload.status:
        integration.status = payload.status
    await db.commit()
    await db.refresh(integration)
    return integration
