from __future__ import annotations

from types import SimpleNamespace

from app.services.lead_capture import apply_lead_capture


def _make_lead() -> SimpleNamespace:
    return SimpleNamespace(
        name=None,
        phone=None,
        cpf=None,
        metadata_json={},
    )


def test_apply_lead_capture_extracts_name_and_cpf_from_same_message() -> None:
    lead = _make_lead()

    changes = apply_lead_capture(
        lead,
        text="quero uma simulacao de imovel valor de 500mil, prazo 180 meses, lance de 100mil. meu nome e ilki amaro junior e cpf 00275230716",
        fallback_phone=None,
    )

    assert "nome_completo" in changes
    assert "cpf" in changes
    assert lead.name == "Ilki Amaro Junior"
    assert lead.cpf == "002.752.307-16"


def test_apply_lead_capture_extracts_phone_from_text() -> None:
    lead = _make_lead()

    changes = apply_lead_capture(
        lead,
        text="meu nome completo e Ilki Amaro e telefone 12988162249",
        fallback_phone=None,
    )

    assert "telefone" in changes
    assert lead.phone == "12988162249"
    assert lead.name == "Ilki Amaro"
