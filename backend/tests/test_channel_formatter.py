from app.services.channel_formatter import format_reply


def test_format_reply_keeps_short_fragments_for_whatsapp() -> None:
    reply_text, fragments = format_reply("whatsapp", ["Perfeito. Vou seguir com o envio da simulação."])

    assert reply_text == "Perfeito. Vou seguir com o envio da simulação."
    assert fragments == ["Perfeito. Vou seguir com o envio da simulação."]


def test_format_reply_splits_long_whatsapp_fragment() -> None:
    long_fragment = (
        "Perfeito. Vou seguir com a simulação usando o contexto que você já me passou, "
        "sem reiniciar a conversa, e se surgir qualquer ajuste no valor, no prazo ou na parcela "
        "você pode me chamar por aqui que eu continuo exatamente deste ponto."
    )

    reply_text, fragments = format_reply("whatsapp", [long_fragment])

    assert len(fragments) >= 2
    assert reply_text == "\n\n".join(fragments)


def test_format_reply_keeps_non_whatsapp_response_joined() -> None:
    reply_text, fragments = format_reply("lab", ["Primeira parte.", "Segunda parte."])

    assert reply_text == "Primeira parte.\n\nSegunda parte."
    assert fragments == ["Primeira parte.", "Segunda parte."]
