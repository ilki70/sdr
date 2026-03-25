from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAIError

from app.core.config import get_settings
from app.services.conversation_context import (
    _extract_asset_value,
    _extract_lance,
    _extract_property_type,
    _extract_target_use_case,
    _extract_timeline,
)
from app.services.conversation_semantics import (
    detect_delivery_channel,
    detect_objection_type,
    detect_pending_user_request,
    detect_simulation_adjustment,
    detect_speech_act,
    extract_budget_monthly,
    has_explicit_name_intro,
    looks_like_name_candidate,
)
from app.services.lead_capture import extract_cpf, extract_full_name, extract_phone
from app.services.llm import _extract_text, _get_client

settings = get_settings()
logger = logging.getLogger(__name__)

SUPPORTED_SLOT_KEYS = {
    "asset_type",
    "goal",
    "asset_value",
    "timeline",
    "budget_monthly",
    "lance",
    "lead_name",
    "cpf",
    "phone",
    "preferred_delivery_channel",
}

SUPPORTED_SPEECH_ACTS = {
    "inform",
    "greeting",
    "confirmation",
    "negation",
    "request_action",
    "correction",
    "objection",
    "closing",
    "handoff_request",
}

SUPPORTED_PENDING_REQUESTS = {
    "send_simulation",
    "adjust_simulation",
    "choose_delivery_channel",
    "correct_context",
    "close_conversation",
    "human_handoff",
    "confirm_simulation",
    "prepare_simulation",
}

SUPPORTED_OBJECTION_TYPES = {"fees", "trust", "comparison", "lance", "timeline"}
SUPPORTED_ADJUSTMENT_TYPES = {"maximize_installments"}


def _normalize_goal(value: str) -> str:
    lowered = value.strip().lower()
    if any(token in lowered for token in ("moradia", "morar", "uso proprio", "uso próprio", "pra mim", "para mim", "uso pessoal", "uso")):
        return "moradia"
    if any(token in lowered for token in ("invest", "retorno", "aplicar")):
        return "investimento"
    if any(token in lowered for token in ("trabalho", "uber", "frota")):
        return "trabalho"
    return value.strip()


def _normalize_slot_value(key: str, value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.replace("\n", " ").split()).strip()
    if not cleaned:
        return None
    if key == "goal":
        return _normalize_goal(cleaned)
    if key == "preferred_delivery_channel":
        lowered = cleaned.lower()
        if "email" in lowered or "e-mail" in lowered:
            return "email"
        if "whats" in lowered or "zap" in lowered:
            return "whatsapp"
    return cleaned


def _normalize_interpretation(payload: dict[str, Any]) -> dict[str, Any]:
    slots_payload = payload.get("slot_updates")
    normalized_slots: dict[str, str] = {}
    if isinstance(slots_payload, dict):
        for key, value in slots_payload.items():
            if key not in SUPPORTED_SLOT_KEYS:
                continue
            normalized_value = _normalize_slot_value(key, value)
            if normalized_value:
                normalized_slots[key] = normalized_value

    result: dict[str, Any] = {"slot_updates": normalized_slots}

    speech_act = payload.get("speech_act")
    if isinstance(speech_act, str) and speech_act in SUPPORTED_SPEECH_ACTS:
        result["speech_act"] = speech_act

    pending_user_request = payload.get("pending_user_request")
    if isinstance(pending_user_request, str) and pending_user_request in SUPPORTED_PENDING_REQUESTS:
        result["pending_user_request"] = pending_user_request

    objection_type = payload.get("objection_type")
    if isinstance(objection_type, str) and objection_type in SUPPORTED_OBJECTION_TYPES:
        result["objection_type"] = objection_type

    adjustment_type = payload.get("adjustment_type")
    if isinstance(adjustment_type, str) and adjustment_type in SUPPORTED_ADJUSTMENT_TYPES:
        result["adjustment_type"] = adjustment_type

    return result


def _heuristic_interpretation(
    *,
    message_text: str,
    history: list[dict[str, str]],
    known_slots: dict[str, str],
    current_topic: str,
    last_agent_commitment: str | None,
    expected_slot: str | None,
) -> dict[str, Any]:
    slot_updates: dict[str, str] = {}
    lowered = message_text.lower()
    has_asset_value_context = any(
        token in lowered
        for token in (
            "valor",
            "credito",
            "crédito",
            "imovel",
            "imóvel",
            "casa",
            "apartamento",
            "carro",
            "moto",
            "veiculo",
            "veículo",
        )
    )

    lead_name = extract_full_name(message_text)
    if lead_name and (expected_slot == "lead_name" or has_explicit_name_intro(message_text)) and looks_like_name_candidate(lead_name):
        slot_updates["lead_name"] = lead_name

    asset_type = _extract_property_type(message_text)
    if asset_type:
        slot_updates["asset_type"] = asset_type

    goal = _extract_target_use_case(message_text)
    if goal:
        slot_updates["goal"] = _normalize_goal(goal)

    timeline = _extract_timeline(message_text)
    if timeline:
        slot_updates["timeline"] = timeline

    lance = _extract_lance(message_text)
    if lance:
        slot_updates["lance"] = lance

    budget_monthly = extract_budget_monthly(message_text, expected_slot)
    if budget_monthly:
        slot_updates["budget_monthly"] = budget_monthly

    asset_value = _extract_asset_value(message_text)
    if asset_value and timeline and "".join(char for char in asset_value if char.isdigit()) == "".join(char for char in timeline if char.isdigit()):
        asset_value = None
    if asset_value and lance and asset_value == lance and expected_slot != "asset_value":
        asset_value = None
    if asset_value and expected_slot in {"lead_name", "cpf", "phone"} and not has_asset_value_context:
        asset_value = None
    if asset_value and known_slots.get("asset_value") and expected_slot != "asset_value" and not has_asset_value_context:
        asset_value = None
    if asset_value and expected_slot not in {"timeline", "budget_monthly", "lance"}:
        slot_updates["asset_value"] = asset_value

    cpf = extract_cpf(message_text)
    if cpf:
        slot_updates["cpf"] = cpf

    phone = extract_phone(message_text)
    if phone:
        slot_updates["phone"] = phone

    delivery_channel = detect_delivery_channel(message_text)
    if delivery_channel:
        slot_updates["preferred_delivery_channel"] = delivery_channel

    return {
        "slot_updates": slot_updates,
        "speech_act": detect_speech_act(
            message_text,
            history=history,
            current_topic=current_topic,
            last_agent_commitment=last_agent_commitment,
        ),
        "pending_user_request": detect_pending_user_request(
            message_text,
            current_topic=current_topic,
            last_agent_commitment=last_agent_commitment,
        ),
        "objection_type": detect_objection_type(message_text),
        "adjustment_type": detect_simulation_adjustment(message_text),
    }


async def interpret_turn_semantics(
    *,
    message_text: str,
    history: list[dict[str, str]],
    known_slots: dict[str, str],
    current_topic: str,
    last_agent_commitment: str | None,
    expected_slot: str | None,
) -> dict[str, Any]:
    heuristic = _heuristic_interpretation(
        message_text=message_text,
        history=history,
        known_slots=known_slots,
        current_topic=current_topic,
        last_agent_commitment=last_agent_commitment,
        expected_slot=expected_slot,
    )
    if not settings.resolved_openai_api_key:
        return heuristic

    prompt = {
        "task": "Interpretar a mensagem do lead e converter apenas fatos canonicos e atos conversacionais em JSON.",
        "message_text": message_text,
        "current_topic": current_topic,
        "last_agent_commitment": last_agent_commitment,
        "expected_slot": expected_slot,
        "known_slots": known_slots,
        "recent_history": history[-6:],
        "schema": {
            "slot_updates": {
                "asset_type": "string|null",
                "goal": "string|null",
                "asset_value": "string|null",
                "timeline": "string|null",
                "budget_monthly": "string|null",
                "lance": "string|null",
                "lead_name": "string|null",
                "cpf": "string|null",
                "phone": "string|null",
                "preferred_delivery_channel": "string|null",
            },
            "speech_act": "inform|greeting|confirmation|negation|request_action|correction|objection|closing|handoff_request|null",
            "pending_user_request": "send_simulation|adjust_simulation|choose_delivery_channel|correct_context|close_conversation|human_handoff|confirm_simulation|prepare_simulation|null",
            "objection_type": "fees|trust|comparison|lance|timeline|null",
            "adjustment_type": "maximize_installments|null",
        },
        "rules": [
            "Nao invente dados ausentes.",
            "Consolide variantes em fatos canonicos. Exemplo: uso, pra mim, uso proprio => goal=moradia.",
            "Se a mensagem trouxer um valor para lance, nao sobrescreva asset_value.",
            "Se a mensagem trouxer prazo em linguagem natural curta, normalize para texto simples como 1 ano, 12 meses.",
            "Responda apenas JSON valido.",
        ],
    }

    try:
        response = await _get_client().chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "Voce interpreta mensagens de atendimento comercial e responde apenas JSON valido, sem explicacoes.",
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        content = _extract_text(response.choices[0].message)
        llm_payload = _normalize_interpretation(json.loads(content))
        if not llm_payload.get("slot_updates") and not any(
            llm_payload.get(key) for key in ("speech_act", "pending_user_request", "objection_type", "adjustment_type")
        ):
            return heuristic

        merged = dict(heuristic)
        merged_slots = dict(heuristic.get("slot_updates") or {})
        merged_slots.update(llm_payload.get("slot_updates") or {})
        merged["slot_updates"] = merged_slots
        for key in ("speech_act", "pending_user_request", "objection_type", "adjustment_type"):
            if llm_payload.get(key):
                merged[key] = llm_payload[key]
        return merged
    except (OpenAIError, json.JSONDecodeError, KeyError, IndexError) as exc:
        logger.exception("conversation_turn_interpretation_failed", extra={"error": str(exc)})
        return heuristic
