from __future__ import annotations

from typing import Any

from app.core.db import SessionLocal
from app.services.agents import (
    get_default_agent_or_none,
    get_persona_version_for_agent,
    get_published_agent_version_or_none,
)
from app.services.personas import get_persona_or_none


def _normalized_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]


def _normalized_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key).strip(): str(item).strip()
        for key, item in value.items()
        if isinstance(key, str) and str(key).strip() and isinstance(item, str) and str(item).strip()
    }


async def get_conversation_policy_context(tenant_id: str, agent_id: str | None) -> dict[str, Any]:
    async with SessionLocal() as session:
        agent_version = None
        if agent_id:
            agent_version = await get_published_agent_version_or_none(session, tenant_id, agent_id)
        if not agent_version:
            default_agent = await get_default_agent_or_none(session, tenant_id)
            if default_agent:
                agent_version = await get_published_agent_version_or_none(session, tenant_id, default_agent.id)

        if not agent_version:
            return {}

        persona = None
        persona_version = await get_persona_version_for_agent(session, tenant_id, agent_version)
        if persona_version and agent_version.persona_id:
            persona = await get_persona_or_none(session, tenant_id, agent_version.persona_id)

        policy_json = agent_version.policy_json if isinstance(agent_version.policy_json, dict) else {}
        qualification = policy_json.get("qualification") if isinstance(policy_json.get("qualification"), dict) else {}
        objections = policy_json.get("objections") if isinstance(policy_json.get("objections"), list) else []
        objection_replies = {
            str(item.get("objection")).strip(): str(item.get("response")).strip()
            for item in objections
            if isinstance(item, dict)
            and isinstance(item.get("objection"), str)
            and str(item.get("objection")).strip()
            and isinstance(item.get("response"), str)
            and str(item.get("response")).strip()
        }

        return {
            "agent_prompt_system": agent_version.prompt_system,
            "positioning": str(policy_json.get("positioning") or "").strip(),
            "agent_rules": _normalized_list(policy_json.get("rules")),
            "handoff_rules": _normalized_list(policy_json.get("handoff_rules")),
            "follow_up_rules": _normalized_list(policy_json.get("follow_up_rules")),
            "qualification_questions": _normalized_list(qualification.get("questions")),
            "qualification_required_fields": _normalized_list(qualification.get("required_fields")),
            "agent_objection_replies": objection_replies,
            "persona_name": persona.name if persona else None,
            "persona_tone": persona_version.tone if persona_version else "",
            "persona_prompt_system": persona_version.prompt_system if persona_version else "",
            "approach_rules": _normalized_list(persona_version.approach_rules_json.get("rules") if persona_version else []),
            "objection_playbook": _normalized_mapping(persona_version.objection_playbook_json if persona_version else {}),
        }
