from app.services.conversation_policy import (
    ask_delivery_channel_reply,
    detect_closing_signal,
    detect_human_request,
    proposal_ready_decision,
    proposal_progress_reply,
    qualification_decision,
    registration_decision,
    send_simulation_reply,
)


def test_detect_human_request_recognizes_human_handoff_language() -> None:
    assert detect_human_request("Quero falar com um consultor humano") is True


def test_detect_closing_signal_recognizes_negative_reply_after_help_offer() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Vou enviar a simulação pelo WhatsApp. Gostaria de esclarecer alguma dúvida ou prefere que eu aguarde seu retorno?",
        }
    ]

    assert detect_closing_signal("nao", history) is True


def test_proposal_progress_reply_uses_known_simulation_context() -> None:
    fragments = proposal_progress_reply(
        {
            "asset_value": "R$ 500mil",
            "timeline": "12 meses",
            "budget_monthly": "R$ 4mil",
        }
    )

    assert "R$ 500mil" in fragments[-1]
    assert "R$ 4mil" in fragments[-1]


def test_send_simulation_reply_prefers_known_whatsapp_number() -> None:
    fragments = send_simulation_reply(
        {
            "phone": "12988162249",
            "preferred_delivery_channel": "whatsapp",
        }
    )

    assert "12988162249" in fragments[0]


def test_ask_delivery_channel_reply_returns_expected_prompt() -> None:
    assert ask_delivery_channel_reply() == ["Perfeito. Você prefere receber a simulação por WhatsApp ou por e-mail?"]


def test_qualification_decision_includes_confirmation_when_present() -> None:
    decision = qualification_decision(
        prompt_fragments=["Qual prazo faz sentido para você?"],
        follow_up_suggestion="Capturar prazo.",
        confirmation="Perfeito, anotei bem: imóvel; valor: R$ 500mil.",
    )

    assert decision.fragments[0].startswith("Perfeito")
    assert decision.flow_stage == "qualification"


def test_registration_decision_only_prefixes_confirmation_for_lead_name() -> None:
    decision = registration_decision(
        prompt_fragments=["Para eu te atender melhor, qual é o seu nome?"],
        follow_up_suggestion="Capturar nome do lead.",
        confirmation="Perfeito, anotei valor: R$ 500mil; prazo: 12 meses.",
        next_slot="lead_name",
    )

    assert decision.fragments[0].startswith("Perfeito")
    assert decision.flow_stage == "registration"


def test_proposal_ready_decision_preserves_summary() -> None:
    decision = proposal_ready_decision(
        slots={"asset_value": "R$ 500mil", "timeline": "12 meses"},
        confirmation=None,
        summary="Lead pronto para simulacao com valor R$ 500mil e prazo 12 meses.",
    )

    assert decision.fragments == ["Perfeito. Com esses dados, eu sigo para a simulação."]
    assert "R$ 500mil" in decision.follow_up_suggestion
