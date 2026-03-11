from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.schemas.whatsapp import WhatsAppInboundWebhookRequest, WhatsAppInboundWebhookResponse
from app.services.whatsapp import handle_inbound_whatsapp_message

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/webhook", response_model=WhatsAppInboundWebhookResponse)
async def post_whatsapp_webhook(
    payload: WhatsAppInboundWebhookRequest,
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppInboundWebhookResponse:
    response = await handle_inbound_whatsapp_message(db, payload)
    if not response:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid WhatsApp integration credentials")
    return response
