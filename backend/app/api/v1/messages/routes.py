import asyncio
import json
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_sales_agent
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.messages import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationPipelineStatusUpdateRequest,
    ConversationSummaryResponse,
    MessageSimulateRequest,
    MessageSimulateResponse,
)
from app.services.conversation_context import refresh_conversation_context_from_db
from app.services.conversation_media import summarize_media_attachments
from app.services.lead_capture import apply_lead_capture
from app.services.messages import (
    create_lab_conversation,
    ensure_lab_conversation,
    get_lead_for_conversation,
    get_conversation_detail,
    list_conversations,
    list_recent_conversation_messages,
    persist_conversation_exchange,
    persist_conversation_pipeline_fields,
    update_conversation_pipeline_status,
)
from app.services.runtime_router import apply_runtime_slot_projection, run_configured_sales_runtime

router = APIRouter(prefix="/messages", tags=["messages"])
settings = get_settings()


async def _prepare_state(
    db: AsyncSession,
    context: RequestContext,
    payload: MessageSimulateRequest,
) -> tuple[AgentState, str]:
    conversation = await ensure_lab_conversation(
        db=db,
        tenant_id=context.tenant_id,
        conversation_id=payload.conversation_id,
        agent_id=payload.agent_id,
        channel=payload.channel,
    )
    history = await list_recent_conversation_messages(db, context.tenant_id, conversation.id)
    media_notes = await summarize_media_attachments([attachment.model_dump() for attachment in payload.attachments])
    effective_message_text = payload.message_text.strip()
    if media_notes:
        effective_message_text = f"{effective_message_text}\n{' | '.join(media_notes)}".strip()
    lead = await get_lead_for_conversation(db, conversation)
    apply_lead_capture(lead, text=effective_message_text, fallback_phone=lead.phone)
    await db.flush()
    state = AgentState(
        tenant_id=context.tenant_id,
        agent_id=conversation.agent_id,
        lead_id=conversation.lead_id,
        conversation_id=conversation.id,
        channel=payload.channel,
        message_text=effective_message_text,
        conversation_history=[
            {
                "role": "assistant" if message.sender_type == "assistant" else "user",
                "content": message.content,
            }
            for message in history
        ],
        media_context=media_notes,
        lead_profile=lead,
    )
    return state, conversation.id


async def _run_lab_runtime(
    db: AsyncSession,
    context: RequestContext,
    payload: MessageSimulateRequest,
) -> tuple[SimpleNamespace, object, str]:
    state, conversation_id = await _prepare_state(db, context, payload)
    conversation = await ensure_lab_conversation(
        db=db,
        tenant_id=context.tenant_id,
        conversation_id=conversation_id,
        agent_id=payload.agent_id,
        channel=payload.channel,
    )
    lead = await get_lead_for_conversation(db, conversation)

    runtime_state, model_name = await run_configured_sales_runtime(
        state=state,
        tenant_id=context.tenant_id,
        agent_id=conversation.agent_id,
        lead=lead,
        channel=payload.channel,
        attachments=[attachment.model_dump() for attachment in payload.attachments],
    )
    await db.flush()
    if model_name == "mock-llm" and settings.resolved_openai_api_key:
        model_name = settings.openai_model
    return runtime_state, conversation, model_name


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
async def get_conversations(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ConversationSummaryResponse]:
    return await list_conversations(db, context.tenant_id)


@router.post("/conversations", response_model=ConversationSummaryResponse, status_code=status.HTTP_201_CREATED)
async def post_conversation(
    payload: ConversationCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationSummaryResponse:
    conversation = await create_lab_conversation(
        db,
        tenant_id=context.tenant_id,
        agent_id=payload.agent_id,
        channel=payload.channel,
        title=payload.title,
    )
    detail = await get_conversation_detail(db, context.tenant_id, conversation.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Conversation creation failed")
    return detail.conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    detail = await get_conversation_detail(db, context.tenant_id, conversation_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return detail


@router.patch("/conversations/{conversation_id}/pipeline-status", response_model=ConversationDetailResponse)
async def patch_conversation_pipeline_status(
    conversation_id: str,
    payload: ConversationPipelineStatusUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    detail = await update_conversation_pipeline_status(
        db=db,
        tenant_id=context.tenant_id,
        conversation_id=conversation_id,
        pipeline_status=payload.pipeline_status,
    )
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return detail


@router.post("/simulate", response_model=MessageSimulateResponse)
async def simulate_message(
    payload: MessageSimulateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> MessageSimulateResponse:
    state, conversation, model_name = await _run_lab_runtime(db, context, payload)
    await persist_conversation_exchange(
        db=db,
        conversation=conversation,
        user_text=state.message_text,
        assistant_text=state.draft_reply,
        intent=state.intent,
        confidence_score=state.confidence_score,
        model_name=model_name,
        reply_fragments=state.reply_fragments,
        follow_up_suggestion=state.follow_up_suggestion,
    )
    if getattr(state, "handoff_requested", False):
        await persist_conversation_pipeline_fields(
            db=db,
            conversation_id=conversation.id,
            tenant_id=context.tenant_id,
            pipeline_status="handoff",
            summary=state.message_text[:160],
            next_step="Assumir atendimento humano e revisar contexto da conversa.",
            status="waiting_human",
            agent_id=conversation.agent_id,
        )
        await db.commit()
    await refresh_conversation_context_from_db(
        db,
        tenant_id=context.tenant_id,
        conversation_id=conversation.id,
        last_intent=state.intent,
        media_notes=state.media_context,
    )
    return MessageSimulateResponse(
        conversation_id=conversation.id,
        intent=state.intent,
        confidence_score=state.confidence_score,
        reply=state.draft_reply,
        reply_fragments=state.reply_fragments,
        follow_up_suggestion=state.follow_up_suggestion,
    )


@router.post("/stream")
async def stream_message(
    payload: MessageSimulateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    state, conversation, model_name = await _run_lab_runtime(db, context, payload)
    await persist_conversation_exchange(
        db=db,
        conversation=conversation,
        user_text=state.message_text,
        assistant_text=state.draft_reply,
        intent=state.intent,
        confidence_score=state.confidence_score,
        model_name=model_name,
        reply_fragments=state.reply_fragments,
        follow_up_suggestion=state.follow_up_suggestion,
    )
    if getattr(state, "handoff_requested", False):
        await persist_conversation_pipeline_fields(
            db=db,
            conversation_id=conversation.id,
            tenant_id=context.tenant_id,
            pipeline_status="handoff",
            summary=state.message_text[:160],
            next_step="Assumir atendimento humano e revisar contexto da conversa.",
            status="waiting_human",
            agent_id=conversation.agent_id,
        )
        await db.commit()
    await refresh_conversation_context_from_db(
        db,
        tenant_id=context.tenant_id,
        conversation_id=conversation.id,
        last_intent=state.intent,
        media_notes=state.media_context,
    )

    async def event_generator():
        chunks = state.draft_reply.split(" ")
        for chunk in chunks:
            yield f"data: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.03)
        yield (
            "data: "
            f"{json.dumps({'done': True, 'intent': state.intent, 'conversation_id': conversation.id, 'reply_fragments': state.reply_fragments, 'follow_up_suggestion': state.follow_up_suggestion})}\n\n"
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
