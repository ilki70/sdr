import asyncio
import json

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
    ConversationSummaryResponse,
    MessageSimulateRequest,
    MessageSimulateResponse,
)
from app.services.messages import (
    create_lab_conversation,
    ensure_lab_conversation,
    get_conversation_detail,
    list_conversations,
    list_recent_conversation_messages,
    persist_conversation_exchange,
)

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
    state = AgentState(
        tenant_id=context.tenant_id,
        agent_id=conversation.agent_id,
        lead_id=conversation.lead_id,
        conversation_id=conversation.id,
        channel=payload.channel,
        message_text=payload.message_text,
        conversation_history=[
            {
                "role": "assistant" if message.sender_type == "assistant" else "user",
                "content": message.content,
            }
            for message in history
        ],
    )
    return state, conversation.id


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


@router.post("/simulate", response_model=MessageSimulateResponse)
async def simulate_message(
    payload: MessageSimulateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> MessageSimulateResponse:
    state, conversation_id = await _prepare_state(db, context, payload)
    state = await run_sales_agent(state)
    conversation = await ensure_lab_conversation(
        db=db,
        tenant_id=context.tenant_id,
        conversation_id=conversation_id,
        agent_id=payload.agent_id,
        channel=payload.channel,
    )
    await persist_conversation_exchange(
        db=db,
        conversation=conversation,
        user_text=payload.message_text,
        assistant_text=state.draft_reply,
        intent=state.intent,
        confidence_score=state.confidence_score,
        model_name=settings.openai_model if settings.resolved_openai_api_key else "mock-llm",
        reply_fragments=state.reply_fragments,
        follow_up_suggestion=state.follow_up_suggestion,
    )
    return MessageSimulateResponse(
        conversation_id=conversation_id,
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
    state, conversation_id = await _prepare_state(db, context, payload)
    state = await run_sales_agent(state)
    conversation = await ensure_lab_conversation(
        db=db,
        tenant_id=context.tenant_id,
        conversation_id=conversation_id,
        agent_id=payload.agent_id,
        channel=payload.channel,
    )
    await persist_conversation_exchange(
        db=db,
        conversation=conversation,
        user_text=payload.message_text,
        assistant_text=state.draft_reply,
        intent=state.intent,
        confidence_score=state.confidence_score,
        model_name=settings.openai_model if settings.resolved_openai_api_key else "mock-llm",
        reply_fragments=state.reply_fragments,
        follow_up_suggestion=state.follow_up_suggestion,
    )

    async def event_generator():
        chunks = state.draft_reply.split(" ")
        for chunk in chunks:
            yield f"data: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.03)
        yield (
            "data: "
            f"{json.dumps({'done': True, 'intent': state.intent, 'conversation_id': conversation_id, 'reply_fragments': state.reply_fragments, 'follow_up_suggestion': state.follow_up_suggestion})}\n\n"
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
