import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.schemas.public import (
    PublicDemoStreamRequest,
    PublicMarketingLeadRequest,
    PublicMarketingLeadResponse,
)
from app.services.public_site import (
    capture_marketing_lead,
    derive_qualification_signals,
    ensure_public_demo_conversation,
    get_public_tenant,
    run_public_demo_exchange,
)

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/marketing/leads", response_model=PublicMarketingLeadResponse)
async def post_marketing_lead(
    payload: PublicMarketingLeadRequest,
    db: AsyncSession = Depends(get_db_session),
) -> PublicMarketingLeadResponse:
    tenant = await get_public_tenant(db)
    lead_id, conversation_id = await capture_marketing_lead(db, tenant.id, payload)
    return PublicMarketingLeadResponse(
        lead_id=lead_id,
        conversation_id=conversation_id,
        status="captured",
        message="Lead capturado com sucesso.",
    )


@router.post("/demo/stream")
async def public_demo_stream(
    payload: PublicDemoStreamRequest,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    tenant = await get_public_tenant(db)
    conversation = await ensure_public_demo_conversation(
        db=db,
        tenant_id=tenant.id,
        conversation_id=payload.conversation_id,
        channel=payload.channel,
    )
    state = await run_public_demo_exchange(
        db=db,
        tenant_id=tenant.id,
        conversation=conversation,
        message_text=payload.message_text,
        channel=payload.channel,
    )
    qualification = derive_qualification_signals(payload.message_text)

    async def event_generator():
        for chunk in state.draft_reply.split(" "):
            yield f"data: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.03)
        yield (
            "data: "
            f"{json.dumps({'done': True, 'conversation_id': conversation.id, 'intent': state.intent, 'reply_fragments': state.reply_fragments, 'follow_up_suggestion': state.follow_up_suggestion, 'qualification_signals': qualification})}\n\n"
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
