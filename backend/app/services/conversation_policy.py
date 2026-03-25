from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyDecision:
    fragments: list[str]
    follow_up_suggestion: str | None
    flow_stage: str
    handoff_requested: bool = False
    updated_last_agent_commitment: str | None = None


def last_assistant_message(history: list[dict[str, str]]) -> str:
    return next(
        (str(item.get("content") or "") for item in reversed(history) if item.get("role") == "assistant" and item.get("content")),
        "",
    )


def detect_human_request(text: str) -> bool:
    lowered = text.lower()
    triggers = (
        "atendente",
        "humano",
        "pessoa",
        "consultor",
        "falar com algu",
        "quero falar com",
    )
    return any(trigger in lowered for trigger in triggers)


def detect_closing_signal(text: str, history: list[dict[str, str]]) -> bool:
    lowered = text.lower().strip()
    if lowered in {"obrigado", "obrigada", "valeu", "era isso", "pode encerrar", "tá bom", "ta bom", "ok obrigado", "ok, obrigado"}:
        return True

    if lowered in {"nao", "não"}:
        last_assistant = last_assistant_message(history).lower()
        if any(
            token in last_assistant
            for token in (
                "alguma dúvida",
                "alguma duvida",
                "posso ajudar",
                "prefere que eu aguarde",
                "gostaria de esclarecer",
                "mais alguma",
                "tem alguma dúvida",
                "tem alguma duvida",
            )
        ):
            return True
    return False


def proposal_progress_reply(slots: dict[str, str]) -> list[str]:
    if slots.get("asset_value") and slots.get("timeline") and slots.get("budget_monthly"):
        return [
            "Perfeito. Eu sigo com a simulação com base no que já alinhamos.",
            f"Hoje eu tenho valor em {slots['asset_value']}, prazo em {slots['timeline']} e parcela alvo em {slots['budget_monthly']}.",
        ]
    if slots.get("asset_value") and slots.get("timeline"):
        return [
            "Perfeito. Eu sigo com a simulação com base no que já alinhamos.",
            f"Hoje eu tenho valor em {slots['asset_value']} e prazo em {slots['timeline']}.",
        ]
    return ["Perfeito. Eu sigo com a simulação com base no que já alinhamos."]


def send_simulation_reply(slots: dict[str, str]) -> list[str]:
    phone = slots.get("phone")
    channel = slots.get("preferred_delivery_channel")
    if channel == "email":
        return ["Perfeito. Eu sigo com o envio por e-mail assim que você me confirmar o melhor endereço."]
    if phone:
        return [f"Perfeito. Vou seguir com o envio pelo WhatsApp no número {phone} e deixo você à vontade para me chamar se quiser ajustar algo depois."]
    return ["Perfeito. Eu sigo com o envio da simulação e, se precisar ajustar algo, você me chama por aqui."]


def ask_delivery_channel_reply() -> list[str]:
    return ["Perfeito. Você prefere receber a simulação por WhatsApp ou por e-mail?"]


def closing_decision(policy_context: dict[str, Any] | None = None) -> PolicyDecision:
    follow_up_suggestion = "Encerrar a conversa por agora e aguardar retorno do lead."
    if isinstance(policy_context, dict):
        follow_up_rules = policy_context.get("follow_up_rules")
        if isinstance(follow_up_rules, list) and follow_up_rules:
            follow_up_suggestion = str(follow_up_rules[0])
    return PolicyDecision(
        fragments=["Perfeito. Fico à disposição e sigo por aqui caso você queira retomar depois."],
        follow_up_suggestion=follow_up_suggestion,
        flow_stage="closing",
    )


def human_handoff_decision(policy_context: dict[str, Any] | None = None) -> PolicyDecision:
    follow_up_suggestion = "Assumir atendimento humano e revisar contexto capturado."
    if isinstance(policy_context, dict):
        handoff_rules = policy_context.get("handoff_rules")
        if isinstance(handoff_rules, list) and handoff_rules:
            follow_up_suggestion = str(handoff_rules[0])
    return PolicyDecision(
        fragments=["Vou direcionar seu atendimento para um consultor humano."],
        follow_up_suggestion=follow_up_suggestion,
        flow_stage="handoff",
        handoff_requested=True,
    )


def active_handoff_decision(policy_context: dict[str, Any] | None = None) -> PolicyDecision:
    follow_up_suggestion = "Aguardar atendimento humano e revisar novas mensagens do lead."
    if isinstance(policy_context, dict):
        handoff_rules = policy_context.get("handoff_rules")
        if isinstance(handoff_rules, list) and handoff_rules:
            follow_up_suggestion = str(handoff_rules[0])
    return PolicyDecision(
        fragments=["Seu atendimento já está com um consultor humano. Vou manter o contexto atualizado por aqui."],
        follow_up_suggestion=follow_up_suggestion,
        flow_stage="handoff",
        handoff_requested=True,
    )


def simulation_delivery_decision(
    *,
    slots: dict[str, str],
    pending_user_request: str | None,
    last_agent_commitment: str | None,
    message_text: str,
) -> PolicyDecision | None:
    lowered = message_text.lower().strip()
    if pending_user_request == "confirm_simulation":
        return PolicyDecision(
            fragments=ask_delivery_channel_reply(),
            follow_up_suggestion="Definir canal de envio da simulacao.",
            flow_stage="simulation_delivery",
            updated_last_agent_commitment="send_simulation",
        )
    if lowered in {"nao", "não"} and last_agent_commitment == "send_simulation":
        return PolicyDecision(
            fragments=["Perfeito. Quando quiser retomar ou ajustar a simulação, eu sigo por aqui."],
            follow_up_suggestion="Encerrar a conversa por agora e aguardar retorno do lead.",
            flow_stage="closing",
        )
    if pending_user_request == "correct_context" and slots.get("phone"):
        return PolicyDecision(
            fragments=[f"Sim, eu sigo com o número {slots['phone']} que você já me passou."],
            follow_up_suggestion="Enviar simulacao no contato ja confirmado.",
            flow_stage="simulation_delivery",
            updated_last_agent_commitment="send_simulation",
        )
    if pending_user_request in {"send_simulation", "choose_delivery_channel"}:
        return PolicyDecision(
            fragments=send_simulation_reply(slots),
            follow_up_suggestion="Executar envio da simulacao no canal combinado.",
            flow_stage="simulation_delivery",
            updated_last_agent_commitment="send_simulation",
        )
    return None


def proposal_in_progress_decision(
    *,
    slots: dict[str, str],
    adjustment_type: str | None,
    budget_follow_up_text: str,
    missing_profile_prompt: str | None,
    missing_profile_follow_up: str | None,
    restart_question_detected: bool,
) -> PolicyDecision | None:
    if adjustment_type == "maximize_installments":
        fragments = proposal_progress_reply(slots)
        if slots.get("budget_monthly"):
            fragments.append(
                f"Perfeito. Vou considerar o maior prazo possível mantendo a parcela por volta de {slots['budget_monthly']}."
            )
            return PolicyDecision(
                fragments=fragments,
                follow_up_suggestion="Ajustar simulacao para maior prazo com a parcela mensal ja informada.",
                flow_stage="proposal_in_progress",
            )
        fragments.append("Perfeito. Para ajustar ao maior prazo possível, me diga qual parcela mensal faz sentido para você.")
        return PolicyDecision(
            fragments=fragments,
            follow_up_suggestion=budget_follow_up_text,
            flow_stage="proposal_in_progress",
        )
    if missing_profile_prompt and missing_profile_follow_up:
        fragments = proposal_progress_reply(slots)
        fragments.append(missing_profile_prompt)
        return PolicyDecision(
            fragments=fragments,
            follow_up_suggestion=missing_profile_follow_up,
            flow_stage="proposal_in_progress",
        )
    if restart_question_detected:
        fragments = proposal_progress_reply(slots)
        fragments.append("Se fizer sentido, eu sigo daqui sem reiniciar sua qualificação.")
        return PolicyDecision(
            fragments=fragments,
            follow_up_suggestion="Seguir com simulacao sem reiniciar qualificacao.",
            flow_stage="proposal_in_progress",
        )
    return None


def objection_decision(
    *,
    base_reply: str,
    confirmation: str | None,
    next_prompt: str | None,
    next_follow_up: str | None,
) -> PolicyDecision:
    if next_prompt and next_follow_up:
        fragments = [base_reply, next_prompt] if not confirmation else [confirmation, base_reply, next_prompt]
        return PolicyDecision(
            fragments=fragments,
            follow_up_suggestion=next_follow_up,
            flow_stage="objection_handling",
        )
    fragments = [base_reply, "Se fizer sentido, eu sigo com a simulação a partir do que você já me passou."]
    if confirmation:
        fragments.insert(0, confirmation)
    return PolicyDecision(
        fragments=fragments,
        follow_up_suggestion="Conduzir para simulacao com base no contexto ja confirmado.",
        flow_stage="objection_handling",
    )


def qualification_decision(
    *,
    prompt_fragments: list[str],
    follow_up_suggestion: str,
    confirmation: str | None,
) -> PolicyDecision:
    fragments = [confirmation, *prompt_fragments] if confirmation else prompt_fragments
    return PolicyDecision(
        fragments=fragments,
        follow_up_suggestion=follow_up_suggestion,
        flow_stage="qualification",
    )


def registration_decision(
    *,
    prompt_fragments: list[str],
    follow_up_suggestion: str,
    confirmation: str | None,
    next_slot: str,
) -> PolicyDecision:
    fragments = [confirmation, *prompt_fragments] if confirmation and next_slot == "lead_name" else prompt_fragments
    return PolicyDecision(
        fragments=fragments,
        follow_up_suggestion=follow_up_suggestion,
        flow_stage="registration",
    )


def proposal_ready_decision(
    *,
    slots: dict[str, str],
    confirmation: str | None,
    summary: str,
) -> PolicyDecision:
    fragments = ["Perfeito. Com esses dados, eu sigo para a simulação."]
    if confirmation:
        fragments.insert(0, confirmation)
    return PolicyDecision(
        fragments=fragments,
        follow_up_suggestion=summary,
        flow_stage="proposal_ready",
    )
