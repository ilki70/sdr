from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.whatsapp import WhatsAppInboundWebhookRequest, WhatsAppInboundWebhookResponse
from app.schemas.whatsapp import WhatsAppInboundRequest, WhatsAppInboundResponse, WhatsAppSessionStatusResponse
from app.services.whatsapp import handle_inbound_whatsapp_message
from app.services.whatsapp_gateway import (
    bootstrap_whatsapp_gateway,
    build_whatsapp_session_status,
    connect_whatsapp_gateway,
    disconnect_whatsapp_gateway,
    process_whatsapp_inbound,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
settings = get_settings()


@router.post("/bootstrap", response_model=WhatsAppSessionStatusResponse)
async def bootstrap_whatsapp(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppSessionStatusResponse:
    return await bootstrap_whatsapp_gateway(db, context.tenant_id)


@router.get("/session", response_model=WhatsAppSessionStatusResponse)
async def get_whatsapp_session(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppSessionStatusResponse:
    return await build_whatsapp_session_status(db, context.tenant_id)


@router.post("/session/connect", response_model=WhatsAppSessionStatusResponse)
async def connect_whatsapp(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppSessionStatusResponse:
    return await connect_whatsapp_gateway(db, context.tenant_id)


@router.post("/session/disconnect", response_model=WhatsAppSessionStatusResponse)
async def disconnect_whatsapp(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppSessionStatusResponse:
    return await disconnect_whatsapp_gateway(db, context.tenant_id)


@router.post("/inbound", response_model=WhatsAppInboundResponse)
async def post_whatsapp_inbound(
    payload: WhatsAppInboundRequest,
    gateway_secret: str | None = Header(default=None, alias="X-WhatsApp-Gateway-Secret"),
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppInboundResponse:
    if gateway_secret != settings.whatsapp_gateway_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid WhatsApp gateway secret")
    return await process_whatsapp_inbound(db, payload)


@router.post("/webhook", response_model=WhatsAppInboundWebhookResponse)
async def post_whatsapp_webhook(
    payload: WhatsAppInboundWebhookRequest,
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppInboundWebhookResponse:
    response = await handle_inbound_whatsapp_message(db, payload)
    if not response:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid WhatsApp integration credentials")
    return response
