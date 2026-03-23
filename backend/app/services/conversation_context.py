from __future__ import annotations

from functools import lru_cache
from datetime import datetime
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utcnow_naive
from app.services.messages import list_recent_conversation_messages

settings = get_settings()

FRAGMENT_BUFFER_WINDOW_SECONDS = 6


class ConversationContextSnapshot(BaseModel):
    tenant_id: str
    conversation_id: str
    property_type: str = "nao informado"
    property_value: str = "nao informado"
    timeline: str = "nao informado"
    lance: str = "nao informado"
    last_intent: str = "unknown"
    summary: str = "sem fatos estruturados"
    media_summary: str = "sem midia"
    turn_count: int = 0
    updated_at: datetime = Field(default_factory=utcnow_naive)
    pending_fragment_text: str = ""
    pending_fragment_updated_at: datetime | None = None


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip()


def _is_greeting_or_ack(text: str) -> bool:
    folded = _clean_text(text).lower()
    return folded in {
        "oi",
        "ola",
        "olá",
        "bom dia",
        "boa tarde",
        "boa noite",
        "sim",
        "nao",
        "não",
        "ok",
        "certo",
        "beleza",
    }


def _format_currency_like(value: str) -> str:
    compact = _clean_text(value)
    if not compact:
        return compact
    if compact.lower().startswith("r$"):
        return compact
    return f"R$ {compact}"


def _extract_amount(text: str) -> str | None:
    folded = text.lower()
    if not folded:
        return None

    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", folded)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))

    match = re.search(r"(\d+(?:[.,]\d+)?\s*(?:mil|milhao|milhoes|mi|k|mil))", normalized)
    if match:
        value = match.group(1).replace(" ", "")
        return _format_currency_like(value)

    match = re.search(r"r\$\s*([\d.,]+)", normalized)
    if match:
        return _format_currency_like(f"R$ {match.group(1)}")

    match = re.search(r"\b(\d{2,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b", normalized)
    if match:
        return _format_currency_like(match.group(1))
    return None


def _extract_timeline(text: str) -> str | None:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    match = re.search(r"(?:ate|em)\s+(\d+\s*(?:meses?|anos?|semanas?|dias?))", normalized)
    if match:
        return match.group(1).replace("  ", " ").strip()
    match = re.search(r"\b(\d+\s*(?:meses?|anos?|semanas?|dias?))\b", normalized)
    if match:
        return match.group(1).replace("  ", " ").strip()
    return None


def _looks_like_timeline_answer(text: str) -> bool:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(char for char in normalized if not unicodedata.combining(char))
    return any(term in folded for term in ["mes", "meses", "ano", "anos", "semana", "semanas", "dia", "dias"])


def _extract_property_type(text: str) -> str | None:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(char for char in normalized if not unicodedata.combining(char))
    if any(
        term in folded
        for term in [
            "casa",
            "imovel",
            "apartamento",
            "sobrado",
            "terreno",
            "moto",
            "motocicleta",
            "carro",
            "veiculo",
            "caminhao",
            "caminhonete",
        ]
    ):
        if "casa" in folded:
            return "casa"
        if "apartamento" in folded:
            return "apartamento"
        if "sobrado" in folded:
            return "sobrado"
        if "terreno" in folded:
            return "terreno"
        if "moto" in folded or "motocicleta" in folded:
            return "moto"
        if "caminhonete" in folded:
            return "caminhonete"
        if "caminhao" in folded:
            return "caminhao"
        if "carro" in folded:
            return "carro"
        if "veiculo" in folded:
            return "veiculo"
        return "imovel"
    return None


def _extract_lance(text: str) -> str | None:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(char for char in normalized if not unicodedata.combining(char))
    if "lance" not in folded and "dar" not in folded:
        return None
    return _extract_amount(text)


def _infer_expected_slot(messages: list[dict[str, str]]) -> str | None:
    last_assistant_message = next(
        (item.get("content", "") for item in reversed(messages) if item.get("role") == "assistant" and item.get("content")),
        "",
    )
    if not last_assistant_message:
        return None

    import unicodedata

    normalized = unicodedata.normalize("NFKD", last_assistant_message.lower())
    folded = "".join(char for char in normalized if not unicodedata.combining(char))
    if "lance" in folded:
        return "lance"
    if "prazo" in folded or "meses" in folded or "anos" in folded:
        return "timeline"
    if "valor" in folded or "faixa de valor" in folded or "quanto" in folded:
        return "property_value"
    if "tipo de imovel" in folded or "qual bem" in folded or "qual veiculo" in folded:
        return "property_type"
    return None


def infer_turn_intent(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(char for char in normalized if not unicodedata.combining(char))
    if any(word in folded for word in ["casa", "imovel", "apartamento", "sobrado", "terreno", "moto", "carro", "veiculo"]):
        return "property"
    if any(word in folded for word in ["investir", "investimento", "vale a pena", "retorno", "aplicar", "aplicacao", "aplicação"]):
        return "investment"
    if "lance" in folded:
        return "lance"
    if any(word in folded for word in ["preco", "valor", "custo", "orcamento", "parcela"]):
        return "price"
    if any(word in folded for word in ["duvida", "como funciona"]):
        return "question"
    return "generic"


def is_fragment_like(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    if _is_greeting_or_ack(cleaned):
        return False
    if any(marker in cleaned for marker in [".", "?", "!", ":"]):
        return False
    if any(char.isdigit() for char in cleaned):
        return False
    words = cleaned.split()
    if len(words) == 1 and words[0].lower() in {"casa", "imovel", "imóvel", "apartamento", "sobrado", "terreno", "lance", "valor", "prazo", "carro"}:
        return False
    if len(cleaned) <= 18 and len(words) <= 3:
        return True
    return False


def resolve_fragmented_inbound_text(
    snapshot: ConversationContextSnapshot,
    incoming_text: str,
) -> tuple[ConversationContextSnapshot, str, bool]:
    cleaned = _clean_text(incoming_text)
    if not cleaned:
        return snapshot, "", False

    pending = _clean_text(snapshot.pending_fragment_text)
    if pending:
        if snapshot.pending_fragment_updated_at is not None:
            age_seconds = (utcnow_naive() - snapshot.pending_fragment_updated_at).total_seconds()
            if age_seconds > FRAGMENT_BUFFER_WINDOW_SECONDS:
                snapshot.pending_fragment_text = ""
                snapshot.pending_fragment_updated_at = None
            else:
                merged = _clean_text(f"{pending} {cleaned}")
                snapshot.pending_fragment_text = ""
                snapshot.pending_fragment_updated_at = None
                return snapshot, merged, False
        else:
            merged = _clean_text(f"{pending} {cleaned}")
            snapshot.pending_fragment_text = ""
            snapshot.pending_fragment_updated_at = None
            return snapshot, merged, False

    if is_fragment_like(cleaned):
        snapshot.pending_fragment_text = cleaned
        snapshot.pending_fragment_updated_at = utcnow_naive()
        return snapshot, "", True

    return snapshot, cleaned, False


def build_conversation_context_snapshot(
    messages: list[dict[str, str]],
    *,
    tenant_id: str,
    conversation_id: str,
    last_intent: str | None = None,
    media_notes: list[str] | None = None,
) -> ConversationContextSnapshot:
    property_type: str | None = None
    property_value: str | None = None
    timeline: str | None = None
    lance: str | None = None
    summary_parts: list[str] = []
    turn_count = 0
    expected_slot = None

    for item in messages:
        content = item.get("content", "")
        if not content:
            continue
        role = item.get("role", "user")
        if role == "assistant":
            expected_slot = _infer_expected_slot([item])
            continue
        if role == "user":
            turn_count += 1
            extracted_type = _extract_property_type(content)
            if extracted_type:
                property_type = extracted_type

            extracted_timeline = _extract_timeline(content)
            if extracted_timeline:
                timeline = extracted_timeline

            extracted_lance = _extract_lance(content)
            if extracted_lance:
                lance = extracted_lance

            extracted_value = _extract_amount(content)
            lowered = content.lower()
            if extracted_value:
                if "lance" in lowered:
                    lance = extracted_value
                elif expected_slot == "lance":
                    lance = extracted_value
                elif expected_slot == "property_value":
                    property_value = extracted_value
                elif "lance" not in lowered and not _looks_like_timeline_answer(content):
                    property_value = extracted_value

            if any(term in content.lower() for term in ["quero", "gostaria", "objetivo", "pretendo", "quero ver", "quero comprar"]):
                summary_parts.append(_clean_text(content))

    if property_type:
        summary_parts.append(f"tipo_de_imovel={property_type}")
    if property_value:
        summary_parts.append(f"valor_do_imovel={property_value}")
    if timeline:
        summary_parts.append(f"prazo={timeline}")
    if lance:
        summary_parts.append(f"lance={lance}")

    latest_user_message = next(
        (item.get("content", "") for item in reversed(messages) if item.get("role") == "user" and item.get("content")),
        "",
    )

    return ConversationContextSnapshot(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        property_type=property_type or "nao informado",
        property_value=property_value or "nao informado",
        timeline=timeline or "nao informado",
        lance=lance or "nao informado",
        last_intent=last_intent or (infer_turn_intent(latest_user_message) if latest_user_message else "unknown"),
        summary="; ".join(summary_parts) if summary_parts else "sem fatos estruturados",
        media_summary=" | ".join(media_notes) if media_notes else "sem midia",
        turn_count=turn_count,
        updated_at=utcnow_naive(),
    )


def conversation_context_cache_key(tenant_id: str, conversation_id: str) -> str:
    return f"conversation_context:{tenant_id}:{conversation_id}"


@lru_cache
def get_redis_client() -> Redis | None:
    if not settings.redis_url:
        return None
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def load_cached_conversation_context(tenant_id: str, conversation_id: str) -> ConversationContextSnapshot | None:
    client = get_redis_client()
    if client is None:
        return None
    payload = await client.get(conversation_context_cache_key(tenant_id, conversation_id))
    if not payload:
        return None
    return ConversationContextSnapshot.model_validate_json(payload)


async def store_cached_conversation_context(
    snapshot: ConversationContextSnapshot,
) -> ConversationContextSnapshot:
    client = get_redis_client()
    if client is None:
        return snapshot
    ttl_seconds = max(int(settings.conversation_context_ttl_seconds), 60)
    await client.setex(
        conversation_context_cache_key(snapshot.tenant_id, snapshot.conversation_id),
        ttl_seconds,
        snapshot.model_dump_json(),
    )
    return snapshot


async def refresh_conversation_context_from_db(
    db: AsyncSession,
    *,
    tenant_id: str,
    conversation_id: str,
    last_intent: str | None = None,
    media_notes: list[str] | None = None,
) -> ConversationContextSnapshot:
    history = await list_recent_conversation_messages(db, tenant_id, conversation_id, limit=20)
    payload = [
        {
            "role": "assistant" if message.sender_type == "assistant" else "user",
            "content": message.content,
        }
        for message in history
    ]
    snapshot = build_conversation_context_snapshot(
        payload,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        last_intent=last_intent,
        media_notes=media_notes,
    )
    return await store_cached_conversation_context(snapshot)


async def clear_pending_fragment(
    tenant_id: str,
    conversation_id: str,
) -> ConversationContextSnapshot | None:
    snapshot = await load_cached_conversation_context(tenant_id, conversation_id)
    if snapshot is None:
        return None
    snapshot.pending_fragment_text = ""
    snapshot.pending_fragment_updated_at = None
    return await store_cached_conversation_context(snapshot)


def format_conversation_context_for_prompt(snapshot: ConversationContextSnapshot | None) -> str:
    if snapshot is None:
        return "contexto estruturado ausente"
    return (
        f"tipo_de_imovel={snapshot.property_type}; "
        f"valor_do_imovel={snapshot.property_value}; "
        f"prazo={snapshot.timeline}; "
        f"lance={snapshot.lance}; "
        f"ultima_intencao={snapshot.last_intent}; "
        f"turnos={snapshot.turn_count}; "
        f"midia={snapshot.media_summary}; "
        f"resumo={snapshot.summary}"
    )
