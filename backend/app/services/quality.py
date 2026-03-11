from __future__ import annotations

from app.core.time import utcnow_naive
from app.services.agents import list_agents
from app.services.messages import get_conversation_detail, list_conversations
from app.schemas.quality import QualityReviewResponse
from sqlalchemy.ext.asyncio import AsyncSession


def _score_conversation(messages) -> tuple[int, list[str]]:
    findings: list[str] = []
    score = 100

    assistant_messages = [message for message in messages if message.sender_type == "assistant"]
    if not assistant_messages:
        return 20, ["Conversa sem resposta do agente."]

    last_assistant = assistant_messages[-1]
    metadata = last_assistant.metadata_json or {}
    content = (last_assistant.content or "").strip()

    if not metadata.get("intent"):
        score -= 15
        findings.append("Resposta sem intent registrada.")
    if not metadata.get("follow_up_suggestion"):
        score -= 10
        findings.append("Resposta sem proximo passo sugerido.")
    if len(content) < 80:
        score -= 15
        findings.append("Resposta final curta demais para um atendimento consultivo.")
    if "mock-llm" in content.lower():
        score -= 20
        findings.append("Resposta ainda depende de modo mock.")
    if not metadata.get("reply_fragments"):
        score -= 10
        findings.append("Resposta sem fragmentacao registrada.")
    if len(messages) < 2:
        score -= 10
        findings.append("Historico muito curto para avaliar continuidade.")

    return max(score, 0), findings


async def list_quality_reviews(
    db: AsyncSession,
    tenant_id: str,
    limit: int = 10,
) -> list[QualityReviewResponse]:
    conversation_summaries = (await list_conversations(db, tenant_id))[:limit]
    agents = await list_agents(db, tenant_id)
    agent_map = {agent.id: agent.name for agent in agents}

    reviews: list[QualityReviewResponse] = []
    for summary in conversation_summaries:
        detail = await get_conversation_detail(db, tenant_id, summary.id)
        messages = detail.messages if detail else []
        score, findings = _score_conversation(messages)
        if score >= 75:
            status = "pass"
        elif score >= 50:
            status = "watch"
        else:
            status = "fail"
        reviews.append(
            QualityReviewResponse(
                conversation_id=summary.id,
                title=summary.title,
                agent_id=summary.agent_id,
                agent_name=agent_map.get(summary.agent_id) if summary.agent_id else None,
                status=status,
                score=score,
                findings=findings,
                reviewed_at=utcnow_naive(),
            )
        )
    return reviews

