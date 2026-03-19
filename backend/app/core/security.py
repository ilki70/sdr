from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db_session
from app.models.entities import TenantUser

settings = get_settings()


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    tenant_id: str
    role: str
    request_id: str


def _ensure_header(value: str | None, name: str) -> str:
    if value and value.strip():
        return value.strip()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Missing required header: {name}",
    )


async def get_request_context(
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_request_id: str | None = Header(default="generated-locally"),
    db: AsyncSession = Depends(get_db_session),
) -> RequestContext:
    return await resolve_request_context(db, x_user_id, x_tenant_id, x_request_id)


async def resolve_request_context(
    db: AsyncSession,
    x_user_id: str | None,
    x_tenant_id: str | None,
    x_request_id: str = "generated-locally",
) -> RequestContext:
    user_id = _ensure_header(x_user_id, "X-User-Id")
    tenant_id = _ensure_header(x_tenant_id, "X-Tenant-Id")
    request_id = _ensure_header(x_request_id, "X-Request-Id")

    if settings.auth_dev_bypass:
        return RequestContext(user_id=user_id, tenant_id=tenant_id, role="owner", request_id=request_id)

    try:
        result = await db.execute(
            select(TenantUser).where(TenantUser.user_id == user_id, TenantUser.tenant_id == tenant_id)
        )
        membership = result.scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no access to tenant")

    return RequestContext(user_id=user_id, tenant_id=tenant_id, role=membership.role, request_id=request_id)
