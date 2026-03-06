from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.auth import LoginRequest, LoginResponse, MessageResponse, RegisterRequest, SessionResponse
from app.services.auth import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


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
