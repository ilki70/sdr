from app.services.conversation_semantics import (
    detect_delivery_channel,
    detect_pending_user_request,
    detect_speech_act,
    looks_like_name_candidate,
    missing_business_slots,
    missing_profile_slots,
    slot_confirmation,
)


def test_detect_pending_user_request_identifies_delivery_channel_choice() -> None:
    assert (
        detect_pending_user_request(
            "whatsapp",
            current_topic="simulation_delivery",
            last_agent_commitment="send_simulation",
        )
        == "choose_delivery_channel"
    )


def test_detect_speech_act_identifies_correction() -> None:
    assert (
        detect_speech_act(
            "o q já passei",
            history=[],
            current_topic="simulation_delivery",
            last_agent_commitment="send_simulation",
        )
        == "correction"
    )


def test_looks_like_name_candidate_rejects_operational_phrases() -> None:
    assert looks_like_name_candidate("Me envie") is False
    assert looks_like_name_candidate("Ilki Amaro") is True


def test_missing_business_slots_returns_only_missing_items() -> None:
    assert missing_business_slots({"asset_type": "imovel", "goal": "moradia"}) == [
        "asset_value",
        "timeline",
        "budget_monthly",
    ]


def test_missing_profile_slots_uses_missing_profile_fields_when_present() -> None:
    assert missing_profile_slots(missing_profile_fields=["cpf", "telefone"], slots={}) == ["cpf", "phone"]


def test_slot_confirmation_only_confirms_multiple_new_slots() -> None:
    assert slot_confirmation({"asset_type": "imovel"}) is None
    assert slot_confirmation({"asset_type": "imovel", "goal": "moradia"}) is not None


def test_detect_delivery_channel_recognizes_whatsapp() -> None:
    assert detect_delivery_channel("me manda no whatsapp") == "whatsapp"
