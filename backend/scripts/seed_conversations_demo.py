import asyncio
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import delete, func, select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal
from app.core.time import utcnow_naive
from app.models.entities import Agent, ChannelIntegration, Conversation, Lead, Message, Tenant, TenantUser, User
from scripts.seed_deep_test_data import ensure_admin_and_tenant, ensure_system_user


SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
DEMO_AGENT_SLUG = "sdr-demo"
DEMO_INTEGRATION_INBOX = "seed:sdr-conversations-demo"


@dataclass(frozen=True)
class DemoConversation:
    seed_key: str
    lead_name: str
    phone: str
    channel: str
    pipeline_status: str
    conversation_status: str
    lead_status: str
    summary: str
    next_step: str
    started_hours_ago: int
    updated_hours_ago: int
    messages: list[tuple[str, str, str, dict | None]]


DEMO_CONVERSATIONS = [
    DemoConversation(
        seed_key="lead-camila-novo",
        lead_name="Camila Rocha",
        phone="+55 11 99871-1101",
        channel="whatsapp",
        pipeline_status="new",
        conversation_status="open",
        lead_status="new",
        summary="Quer entender como funciona o consorcio de carros e ainda nao informou faixa de parcela.",
        next_step="Fazer primeira qualificacao e descobrir objetivo, urgencia e faixa de parcela.",
        started_hours_ago=3,
        updated_hours_ago=2,
        messages=[
            ("lead", "inbound", "Oi, queria entender como funciona o consorcio de carros.", None),
        ],
    ),
    DemoConversation(
        seed_key="lead-bruno-qualificando",
        lead_name="Bruno Martins",
        phone="+55 21 99731-2234",
        channel="whatsapp",
        pipeline_status="qualifying",
        conversation_status="open",
        lead_status="engaged",
        summary="Busca carta para carro de ate 90 mil e perguntou sobre faixa de parcelas e prazo.",
        next_step="Aprofundar capacidade de parcela e preparar passagem para simulacao.",
        started_hours_ago=18,
        updated_hours_ago=1,
        messages=[
            ("lead", "inbound", "Tenho interesse em um carro na faixa de 90 mil e queria saber como ficam as parcelas.", None),
            (
                "assistant",
                "outbound",
                "Posso te ajudar a mapear a melhor faixa de parcela. Hoje voce busca menor parcela, mais rapidez ou previsibilidade?",
                {"follow_up_suggestion": "Confirmar faixa de parcela desejada e urgencia de compra."},
            ),
            ("lead", "inbound", "Quero algo em torno de 1.400 por mes e nao tenho tanta pressa.", None),
        ],
    ),
    DemoConversation(
        seed_key="lead-renata-handoff",
        lead_name="Renata Alves",
        phone="+55 31 99642-7788",
        channel="whatsapp",
        pipeline_status="handoff",
        conversation_status="waiting_human",
        lead_status="handoff",
        summary="Lead quer simulacao formal ainda hoje e pede confirmacao de condicoes com especialista humano.",
        next_step="Assumir atendimento humano, revisar contexto e enviar simulacao oficial.",
        started_hours_ago=28,
        updated_hours_ago=1,
        messages=[
            ("lead", "inbound", "Quero seguir com uma simulacao formal e preciso fechar isso hoje.", None),
            (
                "assistant",
                "outbound",
                "Perfeito. Vou encaminhar seu caso para um especialista humano revisar as condicoes e seguir com a simulacao.",
                {"follow_up_suggestion": "Encaminhar para humano com contexto e objetivo de fechamento no mesmo dia."},
            ),
        ],
    ),
    DemoConversation(
        seed_key="lead-diego-agendado",
        lead_name="Diego Nascimento",
        phone="+55 41 99102-4400",
        channel="lab",
        pipeline_status="scheduled",
        conversation_status="open",
        lead_status="scheduled",
        summary="Reuniao de alinhamento para simulacao ficou combinada para amanha as 10h.",
        next_step="Confirmar horario, responsavel e preparar follow-up antes da reuniao.",
        started_hours_ago=42,
        updated_hours_ago=4,
        messages=[
            ("lead", "inbound", "Podemos marcar uma conversa amanha cedo para eu entender a proposta?", None),
            (
                "assistant",
                "outbound",
                "Claro. Vou deixar registrado um alinhamento para amanha as 10h com o time comercial.",
                {"follow_up_suggestion": "Confirmar a reuniao agendada e enviar contexto ao responsavel."},
            ),
        ],
    ),
    DemoConversation(
        seed_key="lead-lucas-desqualificado",
        lead_name="Lucas Pires",
        phone="+55 51 99288-3301",
        channel="whatsapp",
        pipeline_status="disqualified",
        conversation_status="closed",
        lead_status="disqualified",
        summary="Lead informou que estava apenas pesquisando, sem prazo nem intencao real de seguir agora.",
        next_step="Registrar motivo da perda e encerrar no funil.",
        started_hours_ago=72,
        updated_hours_ago=48,
        messages=[
            ("lead", "inbound", "Estou so pesquisando mesmo, sem prazo. Talvez eu veja isso no ano que vem.", None),
            (
                "assistant",
                "outbound",
                "Sem problema. Quando fizer sentido retomar, podemos revisar as opcoes com mais contexto.",
                {"follow_up_suggestion": "Registrar curiosidade sem prazo como perda temporaria."},
            ),
        ],
    ),
]


async def ensure_agent(tenant_id: str, user_id: str) -> Agent:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Agent).where(Agent.tenant_id == tenant_id, Agent.slug == DEMO_AGENT_SLUG, Agent.deleted_at.is_(None))
        )
        agent = result.scalar_one_or_none()
        if agent:
            return agent

        agent = Agent(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name="Orfi SDR Demo",
            slug=DEMO_AGENT_SLUG,
            description="Agente de demonstracao para validar a tela de conversas do funil SDR.",
            status="active",
            created_by_user_id=user_id,
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        return agent


async def ensure_integration(tenant_id: str, agent_id: str) -> ChannelIntegration:
    async with SessionLocal() as session:
        result = await session.execute(
            select(ChannelIntegration).where(
                ChannelIntegration.tenant_id == tenant_id,
                ChannelIntegration.inbox_ref == DEMO_INTEGRATION_INBOX,
                ChannelIntegration.deleted_at.is_(None),
            )
        )
        integration = result.scalar_one_or_none()
        if integration:
            integration.agent_id = agent_id
            await session.commit()
            await session.refresh(integration)
            return integration

        integration = ChannelIntegration(
            id=str(uuid4()),
            tenant_id=tenant_id,
            agent_id=agent_id,
            provider="agent_lab",
            inbox_ref=DEMO_INTEGRATION_INBOX,
            api_base_url="http://127.0.0.1:3000",
            webhook_secret_enc=b"seed-demo",
            config_json={"seed": True, "scope": "conversations-demo"},
            status="active",
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        return integration


async def ensure_demo_conversation(
    tenant_id: str,
    integration_id: str,
    agent_id: str,
    demo: DemoConversation,
) -> None:
    async with SessionLocal() as session:
        now = utcnow_naive()
        started_at = now - timedelta(hours=demo.started_hours_ago)
        updated_at = now - timedelta(hours=demo.updated_hours_ago)

        lead_result = await session.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.integration_id == integration_id,
                Lead.external_contact_id == demo.seed_key,
            )
        )
        lead = lead_result.scalar_one_or_none()
        if not lead:
            lead = Lead(
                id=str(uuid4()),
                tenant_id=tenant_id,
                integration_id=integration_id,
                external_contact_id=demo.seed_key,
                name=demo.lead_name,
                phone=demo.phone,
                source_channel=demo.channel,
                lifecycle_status=demo.lead_status,
                first_seen_at=started_at,
                last_seen_at=updated_at,
                metadata_json={"seed": True, "seed_key": demo.seed_key},
            )
            session.add(lead)
            await session.flush()
        else:
            lead.name = demo.lead_name
            lead.phone = demo.phone
            lead.source_channel = demo.channel
            lead.lifecycle_status = demo.lead_status
            lead.first_seen_at = started_at
            lead.last_seen_at = updated_at
            lead.metadata_json = {"seed": True, "seed_key": demo.seed_key}

        conversation_result = await session.execute(
            select(Conversation).where(
                Conversation.tenant_id == tenant_id,
                Conversation.lead_id == lead.id,
                Conversation.integration_id == integration_id,
            )
        )
        conversation = conversation_result.scalar_one_or_none()
        if not conversation:
            conversation = Conversation(
                id=str(uuid4()),
                tenant_id=tenant_id,
                agent_id=agent_id,
                lead_id=lead.id,
                integration_id=integration_id,
                external_conversation_id=f"seed:{demo.seed_key}",
                channel=demo.channel,
                status=demo.conversation_status,
                pipeline_status=demo.pipeline_status,
                summary=demo.summary,
                next_step=demo.next_step,
                started_at=started_at,
                updated_at=updated_at,
            )
            session.add(conversation)
            await session.flush()
        else:
            conversation.agent_id = agent_id
            conversation.external_conversation_id = f"seed:{demo.seed_key}"
            conversation.channel = demo.channel
            conversation.status = demo.conversation_status
            conversation.pipeline_status = demo.pipeline_status
            conversation.summary = demo.summary
            conversation.next_step = demo.next_step
            conversation.started_at = started_at
            conversation.updated_at = updated_at

        await session.execute(delete(Message).where(Message.conversation_id == conversation.id, Message.tenant_id == tenant_id))

        total_messages = len(demo.messages)
        spacing_minutes = 0 if total_messages <= 1 else max(1, int(((demo.started_hours_ago - demo.updated_hours_ago) * 60) / (total_messages - 1)))
        for index, (sender_type, direction, content, metadata_json) in enumerate(demo.messages):
            sent_at = started_at + timedelta(minutes=spacing_minutes * index)
            if index == total_messages - 1:
                sent_at = updated_at
            session.add(
                Message(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    conversation_id=conversation.id,
                    external_message_id=f"{demo.seed_key}:{index + 1}",
                    sender_type=sender_type,
                    direction=direction,
                    content=content,
                    metadata_json=metadata_json,
                    sent_at=sent_at,
                    created_at=sent_at,
                )
            )

        await session.commit()


async def print_summary(tenant_id: str) -> None:
    async with SessionLocal() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one()

        admin_result = await session.execute(
            select(User)
            .join(TenantUser, TenantUser.user_id == User.id)
            .where(TenantUser.tenant_id == tenant_id)
            .order_by(User.created_at.asc())
        )
        admin = admin_result.scalars().first()

        conversation_count = await session.scalar(
            select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id)
        )
        message_count = await session.scalar(select(func.count(Message.id)).where(Message.tenant_id == tenant_id))

        print("seed_done=true")
        print(f"tenant_slug={tenant.slug}")
        if admin:
            print(f"admin_email={admin.email}")
        print(f"agent_slug={DEMO_AGENT_SLUG}")
        print(f"conversations={conversation_count or 0}")
        print(f"messages={message_count or 0}")


async def main() -> None:
    await ensure_system_user()
    tenant_id, user_id = await ensure_admin_and_tenant()
    agent = await ensure_agent(tenant_id, user_id)
    integration = await ensure_integration(tenant_id, agent.id)
    for demo in DEMO_CONVERSATIONS:
        await ensure_demo_conversation(tenant_id, integration.id, agent.id, demo)
    await print_summary(tenant_id)


if __name__ == "__main__":
    asyncio.run(main())
