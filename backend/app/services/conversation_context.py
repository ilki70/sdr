from __future__ import annotations

import logging
from functools import lru_cache
from datetime import datetime
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utcnow_naive
from app.services.messages import list_recent_conversation_messages

settings = get_settings()
logger = logging.getLogger(__name__)

FRAGMENT_BUFFER_WINDOW_SECONDS = 6


class ConversationContextSnapshot(BaseModel):
    tenant_id: str
    conversation_id: str
    asset_type: str = "nao informado"
    asset_value: str = "nao informado"
    target_use_case: str = "nao informado"
    lead_name: str = "nao informado"
    goal: str = "nao informado"
    timeline: str = "nao informado"
    lance: str = "nao informado"
    last_intent: str = "unknown"
    current_question_slot: str = "nao informado"
    last_confirmed_slot: str = "nao informado"
    extracted_slots: dict[str, str] = Field(default_factory=dict)
    summary: str = "sem fatos estruturados"
    media_summary: str = "sem midia"
    memory_notes: list[str] = Field(default_factory=list)
    turn_count: int = 0
    updated_at: datetime = Field(default_factory=utcnow_naive)
    pending_fragment_text: str = ""
    pending_fragment_updated_at: datetime | None = None


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip()


def _fold_text(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


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


def _looks_like_name(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned or any(char.isdigit() for char in cleaned):
        return False
    words = cleaned.split()
    if len(words) > 6:
        return False
    folded = _fold_text(cleaned)
    blocked = {
        "oi",
        "ola",
        "olá",
        "sim",
        "nao",
        "não",
        "quero",
        "moto",
        "carro",
        "imovel",
        "investimento",
        "consorcio",
    }
    return folded not in blocked


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


def _extract_amount_for_keywords(text: str, keywords: tuple[str, ...]) -> str | None:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    amount_pattern = r"(\d+(?:[.,]\d+)?\s*(?:milhoes?|milhao|mil|mi|k)?|\d{2,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)"
    keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)

    patterns = [
        rf"\b(?:{keyword_pattern})\b(?:\s+de)?\s*(?:r\$\s*)?{amount_pattern}",
        rf"{amount_pattern}(?=\s*(?:de\s+)?(?:{keyword_pattern})\b)",
        rf"{amount_pattern}(?=\s*(?:para\s+dar\s+de|de|como)?\s*(?:{keyword_pattern})\b)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        groups = [group for group in match.groups() if group]
        if not groups:
            continue
        amount = groups[-1]
        formatted = _format_currency_like(amount)
        if formatted:
            return formatted
    return None


def _extract_timeline(text: str) -> str | None:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"\buma\b", "1", normalized)
    normalized = re.sub(r"\bum\b", "1", normalized)
    match = re.search(r"(?:ate|em)\s+(\d+\s*(?:meses?|anos?|semanas?|dias?))", normalized)
    if match:
        return match.group(1).replace("  ", " ").strip()
    match = re.search(r"\b(\d+\s*(?:meses?|anos?|semanas?|dias?))\b", normalized)
    if match:
        return match.group(1).replace("  ", " ").strip()
    return None


def _amount_matches_timeline(amount: str | None, timeline: str | None) -> bool:
    if not amount or not timeline:
        return False
    amount_digits = "".join(char for char in amount if char.isdigit())
    timeline_digits = "".join(char for char in timeline if char.isdigit())
    return bool(amount_digits and timeline_digits and amount_digits == timeline_digits)


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
    if not any(term in folded for term in ("lance", "dar", "tenho", "entrada")):
        return None
    return _extract_amount_for_keywords(text, ("lance", "dar", "tenho", "entrada"))


def _extract_asset_value(text: str) -> str | None:
    contextual = _extract_amount_for_keywords(
        text,
        ("valor", "credito", "crédito", "imovel", "imovel", "apartamento", "casa", "carro", "moto", "veiculo", "veiculo"),
    )
    return contextual or _extract_amount(text)


def _extract_lead_name(text: str) -> str | None:
    import re

    cleaned = _clean_text(text)
    folded = _fold_text(cleaned)
    match = re.search(
        r"\b(?:meu nome(?: completo)? e|meu nome(?: completo)? eh|me chamo|sou)\s+([A-Za-zÀ-ÿ'`-]+(?:\s+[A-Za-zÀ-ÿ'`-]+){1,5})(?=\s*(?:,|;|\.|!|\?|$|\be\b\s+(?:cpf|telefone|fone|celular|whatsapp|prazo|lance|valor|parcela|objetivo)))",
        cleaned,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = _clean_text(match.group(1))
        return candidate.title() if _looks_like_name(candidate) else None
    if _looks_like_name(cleaned):
        return cleaned.title()
    if folded.startswith("sou "):
        candidate = _clean_text(cleaned[4:])
        return candidate.title() if _looks_like_name(candidate) else None
    return None


def _extract_target_use_case(text: str) -> str | None:
    folded = _fold_text(text)
    compact = _clean_text(folded)
    if any(term in folded for term in ["investir", "investimento", "retorno", "aplicar"]):
        return "investimento"
    if compact in {"uso", "proprio", "propria", "próprio", "própria"}:
        return "moradia"
    if any(
        term in folded
        for term in [
            "morar",
            "moradia",
            "imovel proprio",
            "imovel próprio",
            "casa propria",
            "casa própria",
            "uso proprio",
            "uso próprio",
            "uso pessoal",
        ]
    ):
        return "moradia"
    if any(term in folded for term in ["trabalho", "trabalhar", "uber", "rodar", "frota"]):
        return "trabalho"
    if any(term in folded for term in ["lazer", "passeio", "viagem", "uso pessoal"]):
        return "uso_pessoal"
    return None


def _extract_goal(text: str) -> str | None:
    cleaned = _clean_text(text)
    folded = _fold_text(cleaned)
    if any(term in folded for term in ["quero", "gostaria", "pretendo", "busco", "objetivo"]):
        return cleaned
    return None


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
    if "nome" in folded:
        return "lead_name"
    if "lance" in folded:
        return "lance"
    if "prazo" in folded or "meses" in folded or "anos" in folded:
        return "timeline"
    if "valor" in folded or "faixa de valor" in folded or "quanto" in folded:
        return "asset_value"
    if "tipo de imovel" in folded or "qual bem" in folded or "qual veiculo" in folded or "qual moto" in folded:
        return "asset_type"
    if "objetivo" in folded or "pretende" in folded or "finalidade" in folded:
        return "goal"
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
    asset_type: str | None = None
    asset_value: str | None = None
    target_use_case: str | None = None
    lead_name: str | None = None
    goal: str | None = None
    timeline: str | None = None
    lance: str | None = None
    summary_parts: list[str] = []
    turn_count = 0
    expected_slot: str | None = None
    last_confirmed_slot: str | None = None

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
            confirmed_slots_in_message: set[str] = set()
            extracted_name = _extract_lead_name(content)
            if extracted_name and (expected_slot == "lead_name" or lead_name is None):
                lead_name = extracted_name
                last_confirmed_slot = "lead_name"
                confirmed_slots_in_message.add("lead_name")

            extracted_use_case = _extract_target_use_case(content)
            if extracted_use_case:
                target_use_case = extracted_use_case
                last_confirmed_slot = "target_use_case"
                confirmed_slots_in_message.add("target_use_case")

            extracted_goal = _extract_goal(content)
            if extracted_goal and (expected_slot == "goal" or "quero" in content.lower() or "pretendo" in content.lower()):
                goal = extracted_goal
                last_confirmed_slot = "goal"
                confirmed_slots_in_message.add("goal")

            extracted_type = _extract_property_type(content)
            if extracted_type:
                asset_type = extracted_type
                last_confirmed_slot = "asset_type"
                confirmed_slots_in_message.add("asset_type")

            extracted_timeline = _extract_timeline(content)
            if extracted_timeline and (expected_slot == "timeline" or _looks_like_timeline_answer(content)):
                timeline = extracted_timeline
                last_confirmed_slot = "timeline"
                confirmed_slots_in_message.add("timeline")

            extracted_lance = _extract_lance(content)
            if extracted_lance:
                lance = extracted_lance
                last_confirmed_slot = "lance"
                confirmed_slots_in_message.add("lance")

            extracted_value = _extract_asset_value(content)
            lowered = content.lower()
            if extracted_value:
                if "lance" in lowered:
                    if extracted_value != lance and asset_value is None:
                        asset_value = extracted_value
                        last_confirmed_slot = "asset_value"
                    elif expected_slot == "asset_value" and asset_value is None:
                        asset_value = extracted_value
                        last_confirmed_slot = "asset_value"
                        confirmed_slots_in_message.add("asset_value")
                    elif lance is None:
                        lance = extracted_value
                        last_confirmed_slot = "lance"
                        confirmed_slots_in_message.add("lance")
                elif expected_slot == "lance":
                    lance = extracted_value
                    last_confirmed_slot = "lance"
                    confirmed_slots_in_message.add("lance")
                elif expected_slot == "asset_value":
                    asset_value = extracted_value
                    last_confirmed_slot = "asset_value"
                    confirmed_slots_in_message.add("asset_value")
                elif (
                    expected_slot == "timeline"
                    and "lance" not in lowered
                    and asset_value is None
                    and not _amount_matches_timeline(extracted_value, extracted_timeline)
                ):
                    asset_value = extracted_value
                    last_confirmed_slot = "asset_value"
                    confirmed_slots_in_message.add("asset_value")
                elif "lance" not in lowered and not _looks_like_timeline_answer(content):
                    asset_value = extracted_value
                    last_confirmed_slot = "asset_value"
                    confirmed_slots_in_message.add("asset_value")

            if any(term in content.lower() for term in ["quero", "gostaria", "objetivo", "pretendo", "quero ver", "quero comprar"]):
                summary_parts.append(_clean_text(content))

            if expected_slot and expected_slot in confirmed_slots_in_message:
                expected_slot = None

    extracted_slots: dict[str, str] = {}
    if lead_name:
        extracted_slots["lead_name"] = lead_name
        summary_parts.append(f"lead_name={lead_name}")
    if asset_type:
        extracted_slots["asset_type"] = asset_type
        summary_parts.append(f"asset_type={asset_type}")
    if asset_value:
        extracted_slots["asset_value"] = asset_value
        summary_parts.append(f"asset_value={asset_value}")
    if target_use_case:
        extracted_slots["target_use_case"] = target_use_case
        summary_parts.append(f"target_use_case={target_use_case}")
    if goal:
        extracted_slots["goal"] = goal
        summary_parts.append(f"goal={goal}")
    if timeline:
        extracted_slots["timeline"] = timeline
        summary_parts.append(f"prazo={timeline}")
    if lance:
        extracted_slots["lance"] = lance
        summary_parts.append(f"lance={lance}")

    latest_user_message = next(
        (item.get("content", "") for item in reversed(messages) if item.get("role") == "user" and item.get("content")),
        "",
    )

    return ConversationContextSnapshot(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        asset_type=asset_type or "nao informado",
        asset_value=asset_value or "nao informado",
        target_use_case=target_use_case or "nao informado",
        lead_name=lead_name or "nao informado",
        goal=goal or "nao informado",
        timeline=timeline or "nao informado",
        lance=lance or "nao informado",
        last_intent=last_intent or (infer_turn_intent(latest_user_message) if latest_user_message else "unknown"),
        current_question_slot=expected_slot or "nao informado",
        last_confirmed_slot=last_confirmed_slot or "nao informado",
        extracted_slots=extracted_slots,
        summary="; ".join(summary_parts) if summary_parts else "sem fatos estruturados",
        media_summary=" | ".join(media_notes) if media_notes else "sem midia",
        memory_notes=_build_memory_notes(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            summary_parts=summary_parts,
            extracted_slots=extracted_slots,
            turn_count=turn_count,
            last_intent=last_intent or (infer_turn_intent(latest_user_message) if latest_user_message else "unknown"),
            current_question_slot=expected_slot or "nao informado",
            last_confirmed_slot=last_confirmed_slot or "nao informado",
        ),
        turn_count=turn_count,
        updated_at=utcnow_naive(),
    )


def _build_memory_notes(
    *,
    tenant_id: str,
    conversation_id: str,
    summary_parts: list[str],
    extracted_slots: dict[str, str],
    turn_count: int,
    last_intent: str,
    current_question_slot: str,
    last_confirmed_slot: str,
) -> list[str]:
    notes: list[str] = []
    if turn_count <= 1:
        notes.append(f"conversa_iniciada={tenant_id}:{conversation_id}")
    for key in ("lead_name", "asset_type", "asset_value", "target_use_case", "goal", "timeline", "lance"):
        value = extracted_slots.get(key)
        if value:
            label = "prazo" if key == "timeline" else key
            notes.append(f"{label}={value}")
    if last_intent and last_intent != "unknown":
        notes.append(f"ultima_intencao={last_intent}")
    if current_question_slot and current_question_slot != "nao informado":
        notes.append(f"pergunta_atual={current_question_slot}")
    if last_confirmed_slot and last_confirmed_slot != "nao informado":
        notes.append(f"ultimo_slot_confirmado={last_confirmed_slot}")
    for item in summary_parts:
        compact = _clean_text(item)
        if compact:
            notes.append(f"resumo={compact}")
    return _dedupe_preserve_order(notes)


def _dedupe_preserve_order(values: list[str], *, max_items: int = 24) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) >= max_items:
            break
    return result


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
    try:
        payload = await client.get(conversation_context_cache_key(tenant_id, conversation_id))
    except (RedisError, OSError, TimeoutError) as exc:
        logger.warning(
            "conversation_context_cache_read_failed",
            extra={"tenant_id": tenant_id, "conversation_id": conversation_id, "error": str(exc)},
        )
        return None
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
    try:
        await client.setex(
            conversation_context_cache_key(snapshot.tenant_id, snapshot.conversation_id),
            ttl_seconds,
            snapshot.model_dump_json(),
        )
    except (RedisError, OSError, TimeoutError) as exc:
        logger.warning(
            "conversation_context_cache_write_failed",
            extra={"tenant_id": snapshot.tenant_id, "conversation_id": snapshot.conversation_id, "error": str(exc)},
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
    previous_snapshot = await load_cached_conversation_context(tenant_id, conversation_id)
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
    if previous_snapshot is not None:
        snapshot.memory_notes = _merge_memory_notes(previous_snapshot.memory_notes, snapshot.memory_notes)
        if previous_snapshot.summary and previous_snapshot.summary != "sem fatos estruturados":
            snapshot.memory_notes = _merge_memory_notes([f"memoria_anterior={previous_snapshot.summary}"], snapshot.memory_notes)
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
    memory_notes = " | ".join(snapshot.memory_notes[-12:]) if snapshot.memory_notes else "sem memoria longa"
    return (
        f"lead_name={snapshot.lead_name}; "
        f"asset_type={snapshot.asset_type}; "
        f"asset_value={snapshot.asset_value}; "
        f"target_use_case={snapshot.target_use_case}; "
        f"goal={snapshot.goal}; "
        f"prazo={snapshot.timeline}; "
        f"lance={snapshot.lance}; "
        f"slot_atual={snapshot.current_question_slot}; "
        f"ultimo_slot_confirmado={snapshot.last_confirmed_slot}; "
        f"slots_extraidos={snapshot.extracted_slots}; "
        f"ultima_intencao={snapshot.last_intent}; "
        f"turnos={snapshot.turn_count}; "
        f"midia={snapshot.media_summary}; "
        f"resumo={snapshot.summary}; "
        f"memoria_longa={memory_notes}"
    )


def _merge_memory_notes(*groups: list[str], max_items: int = 24) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            cleaned = _clean_text(value)
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            merged.append(cleaned)
            if len(merged) >= max_items:
                return merged
    return merged
