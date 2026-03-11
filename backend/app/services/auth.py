from dataclasses import dataclass
from uuid import uuid4

from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Tenant, TenantUser, User
from app.schemas.auth import RegisterRequest
from app.services.agents import ensure_default_agent_for_tenant

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    tenant_id: str
    role: str
    email: str
    full_name: str


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(raw_password, password_hash)
    except (ValueError, UnknownHashError):
        return False


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    tenant_id: str,
) -> AuthenticatedUser | None:
    tenant_result = await db.execute(select(Tenant).where((Tenant.id == tenant_id) | (Tenant.slug == tenant_id)))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        return None

    user_result = await db.execute(select(User).where(User.email == email, User.is_active.is_(True)))
    user = user_result.scalar_one_or_none()
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    link_result = await db.execute(
        select(TenantUser).where(TenantUser.user_id == user.id, TenantUser.tenant_id == tenant.id)
    )
    membership = link_result.scalar_one_or_none()
    if not membership:
        return None

    return AuthenticatedUser(
        user_id=user.id,
        tenant_id=tenant.id,
        role=membership.role,
        email=user.email,
        full_name=user.full_name,
    )


async def register_user(db: AsyncSession, payload: RegisterRequest) -> AuthenticatedUser:
    tenant_result = await db.execute(
        select(Tenant).where((Tenant.id == payload.tenant_id) | (Tenant.slug == payload.tenant_id))
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            id=str(uuid4()),
            name=f"Tenant {payload.tenant_id}",
            slug=payload.tenant_id.lower().replace(" ", "-"),
            status="active",
        )
        db.add(tenant)
        await db.flush()

    existing_result = await db.execute(select(User).where(User.email == payload.email))
    user = existing_result.scalar_one_or_none()
    if not user:
        user = User(
            id=str(uuid4()),
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            is_active=True,
        )
        db.add(user)
        await db.flush()

    link_result = await db.execute(
        select(TenantUser).where(TenantUser.user_id == user.id, TenantUser.tenant_id == tenant.id)
    )
    membership = link_result.scalar_one_or_none()
    if not membership:
        membership = TenantUser(
            id=str(uuid4()),
            tenant_id=tenant.id,
            user_id=user.id,
            role=payload.role,
        )
        db.add(membership)

    await db.flush()
    await ensure_default_agent_for_tenant(db, tenant.id, user.id)
    await db.commit()
    return AuthenticatedUser(
        user_id=user.id,
        tenant_id=tenant.id,
        role=membership.role,
        email=user.email,
        full_name=user.full_name,
    )
