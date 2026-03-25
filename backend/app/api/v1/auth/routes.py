from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context, resolve_request_context
from app.schemas.auth import (
    AdminResetUserPasswordRequest,
    AdminResetUserPasswordResponse,
    GoogleLoginRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    SessionResponse,
)
from app.services.auth import authenticate_google_user, authenticate_user, register_user, reset_user_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db_session)) -> LoginResponse:
    try:
        authenticated = await authenticate_user(
            db=db,
            email=payload.email,
            password=payload.password,
            tenant_id=payload.tenant_id,
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or tenant access")
    return LoginResponse(
        user_id=authenticated.user_id,
        tenant_id=authenticated.tenant_id,
        role=authenticated.role,
        email=authenticated.email,
        full_name=authenticated.full_name,
        message="Authenticated",
    )


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db_session)) -> LoginResponse:
    try:
        registered = await register_user(db, payload)
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    return LoginResponse(
        user_id=registered.user_id,
        tenant_id=registered.tenant_id,
        role=registered.role,
        email=registered.email,
        full_name=registered.full_name,
        message="Registered",
    )


@router.post("/google/login", response_model=LoginResponse)
async def google_login(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db_session)) -> LoginResponse:
    try:
        authenticated = await authenticate_google_user(db, payload)
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    return LoginResponse(
        user_id=authenticated.user_id,
        tenant_id=authenticated.tenant_id,
        role=authenticated.role,
        email=authenticated.email,
        full_name=authenticated.full_name,
        message="Authenticated with Google",
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(context: RequestContext = Depends(get_request_context)) -> MessageResponse:
    _ = context
    return MessageResponse(message="Logout acknowledged")


@router.get("/session", response_model=SessionResponse)
async def get_session(context: RequestContext = Depends(get_request_context)) -> SessionResponse:
    return SessionResponse(
        user_id=context.user_id,
        tenant_id=context.tenant_id,
        role=context.role,
        request_id=context.request_id,
    )


@router.post("/admin/reset-user-password", response_model=AdminResetUserPasswordResponse)
async def reset_user_password_admin(
    payload: AdminResetUserPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    x_admin_reset_key: str | None = Header(default=None, alias="X-Admin-Reset-Key"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_request_id: str | None = Header(default="generated-locally", alias="X-Request-Id"),
) -> AdminResetUserPasswordResponse:
    if settings.admin_reset_secret:
        if not x_admin_reset_key or x_admin_reset_key != settings.admin_reset_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin reset key")
    else:
        context = await resolve_request_context(db, x_user_id, x_tenant_id, x_request_id)
        if context.role not in {"owner", "admin"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        if context.tenant_id != payload.tenant_id and context.role != "owner":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    try:
        reset = await reset_user_password(db, payload)
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    return AdminResetUserPasswordResponse(
        tenant_id=reset.tenant_id,
        email=reset.email,
        user_id=reset.user_id,
        role=reset.role,
        status="reset",
    )
