from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_sales_agent
from app.agents.state import AgentState
from app.core.config import get_settings
from app.models.entities import ChannelIntegration, Conversation, Lead, Tenant
from app.schemas.public import PublicMarketingLeadRequest
from app.services.messages import list_recent_conversation_messages, persist_conversation_exchange

settings = get_settings()


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_public_tenant(db: AsyncSession) -> Tenant:
    result = await db.execute(
        select(Tenant).where(Tenant.slug == settings.public_demo_tenant_slug, Tenant.deleted_at.is_(None))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Public demo tenant is not configured",
        )
    return tenant


async def _get_or_create_public_integration(
    db: AsyncSession,
    tenant_id: str,
    provider: str,
    inbox_ref: str,
    api_base_url: str,
    config_json: dict,
) -> ChannelIntegration:
    result = await db.execute(
        select(ChannelIntegration).where(
            ChannelIntegration.tenant_id == tenant_id,
            ChannelIntegration.provider == provider,
            ChannelIntegration.inbox_ref == inbox_ref,
            ChannelIntegration.deleted_at.is_(None),
        )
    )
    integration = result.scalar_one_or_none()
    if integration:
        return integration

    integration = ChannelIntegration(
        id=str(uuid4()),
        tenant_id=tenant_id,
        provider=provider,
        inbox_ref=inbox_ref,
        api_base_url=api_base_url,
        webhook_secret_enc=b"public-site",
        config_json=config_json,
        status="active",
    )
    db.add(integration)
    await db.flush()
    return integration


async def _create_public_conversation(
    db: AsyncSession,
    tenant_id: str,
    provider: str,
    inbox_ref: str,
    channel: str,
    lead_name: str,
    email: str | None,
    metadata_json: dict,
) -> Conversation:
    integration = await _get_or_create_public_integration(
        db=db,
        tenant_id=tenant_id,
        provider=provider,
        inbox_ref=inbox_ref,
        api_base_url="https://super-vendedor.local/public",
        config_json={"channel": channel, "source": provider},
    )
    lead = Lead(
        id=str(uuid4()),
        tenant_id=tenant_id,
        integration_id=integration.id,
        name=lead_name,
        email=email,
        source_channel=channel,
        lifecycle_status="engaged",
        first_seen_at=_utcnow_naive(),
        last_seen_at=_utcnow_naive(),
        metadata_json=metadata_json,
    )
    db.add(lead)
    await db.flush()

    conversation = Conversation(
        id=str(uuid4()),
        tenant_id=tenant_id,
        lead_id=lead.id,
        integration_id=integration.id,
        channel=channel,
        status="open",
        started_at=_utcnow_naive(),
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def ensure_public_demo_conversation(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str | None,
    channel: str,
) -> Conversation:
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    return await _create_public_conversation(
        db=db,
        tenant_id=tenant_id,
        provider="marketing_site",
        inbox_ref=f"public-demo:{channel}",
        channel=channel,
        lead_name="Visitante demo publica",
        email=None,
        metadata_json={"source": "public_demo"},
    )


def derive_qualification_signals(message_text: str) -> list[str]:
    folded = message_text.lower()
    signals: list[str] = []
    if any(token in folded for token in ["orcamento", "parcela", "renda"]):
        signals.extend(["orcamento", "faixa de parcela"])
    if any(token in folded for token in ["financiamento", "juros", "vale a pena"]):
        signals.extend(["comparacao", "perfil financeiro"])
    if any(token in folded for token in ["seminovo", "usado", "ano do carro"]):
        signals.extend(["modelo", "ano", "regra do produto"])
    if any(token in folded for token in ["whatsapp", "email", "canal"]):
        signals.extend(["canal", "handoff"])
    if "urg" not in " ".join(signals):
        signals.append("urgencia")
    deduped: list[str] = []
    for item in signals:
        if item not in deduped:
            deduped.append(item)
    return deduped[:4]


async def build_public_demo_state(
    db: AsyncSession,
    tenant_id: str,
    conversation: Conversation,
    message_text: str,
    channel: str,
) -> AgentState:
    history = await list_recent_conversation_messages(db, tenant_id, conversation.id)
    return AgentState(
        tenant_id=tenant_id,
        lead_id=conversation.lead_id,
        conversation_id=conversation.id,
        channel=channel,
        message_text=message_text,
        conversation_history=[
            {
                "role": "assistant" if message.sender_type == "assistant" else "user",
                "content": message.content,
            }
            for message in history
        ],
    )


async def run_public_demo_exchange(
    db: AsyncSession,
    tenant_id: str,
    conversation: Conversation,
    message_text: str,
    channel: str,
) -> AgentState:
    state = await build_public_demo_state(db, tenant_id, conversation, message_text, channel)
    state = await run_sales_agent(state)
    await persist_conversation_exchange(
        db=db,
        conversation=conversation,
        user_text=message_text,
        assistant_text=state.draft_reply,
        intent=state.intent,
        confidence_score=state.confidence_score,
        model_name=settings.openai_model if settings.openai_api_key else "mock-llm",
        reply_fragments=state.reply_fragments,
        follow_up_suggestion=state.follow_up_suggestion,
    )
    return state


async def capture_marketing_lead(
    db: AsyncSession,
    tenant_id: str,
    payload: PublicMarketingLeadRequest,
) -> tuple[str, str]:
    conversation = await _create_public_conversation(
        db=db,
        tenant_id=tenant_id,
        provider="marketing_site",
        inbox_ref="landing-intake",
        channel="landing",
        lead_name=payload.name,
        email=payload.email,
        metadata_json={
            "source": "marketing_landing",
            "company": payload.company or "",
            "message_preview": payload.message[:180],
        },
    )
    await persist_conversation_exchange(
        db=db,
        conversation=conversation,
        user_text=payload.message,
        assistant_text=(
            "Recebi seu interesse. Nosso time vai usar este contexto para priorizar o contato e entrar com a proxima acao comercial."
        ),
        intent="marketing_capture",
        confidence_score=1.0,
        model_name="marketing-capture",
        reply_fragments=[
            "Recebi seu interesse.",
            "Nosso time vai usar este contexto para priorizar o contato.",
        ],
        follow_up_suggestion="Revisar lead capturado e iniciar contato consultivo.",
    )
    return conversation.lead_id, conversation.id
