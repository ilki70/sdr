from __future__ import annotations

from app.services.conversation_context import _extract_asset_value, _infer_expected_slot
from app.services.conversation_policy import detect_closing_signal, detect_human_request


def infer_runtime_expected_slot(history: list[dict[str, str]]) -> str | None:
    last_assistant_message = next(
        (item.get("content", "") for item in reversed(history) if item.get("role") == "assistant" and item.get("content")),
        "",
    )
    lowered = last_assistant_message.lower()
    if any(token in lowered for token in ("parcela", "orçamento", "orcamento", "por mês", "por mes")):
        return "budget_monthly"
    return _infer_expected_slot(history)


def extract_budget_monthly(text: str, expected_slot: str | None) -> str | None:
    lowered = text.lower()
    if expected_slot != "budget_monthly" and not any(token in lowered for token in ("parcela", "orçamento", "orcamento", "por mês", "por mes")):
        return None
    return _extract_asset_value(text)


def has_explicit_name_intro(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("me chamo", "meu nome", "sou "))


def looks_like_name_candidate(text: str) -> bool:
    cleaned = " ".join(text.replace("\n", " ").split()).strip()
    if not cleaned or any(char.isdigit() for char in cleaned):
        return False
    words = cleaned.split()
    if not 2 <= len(words) <= 4:
        return False
    blocked = {
        "uso",
        "proprio",
        "próprio",
        "me",
        "envie",
        "passei",
        "quero",
        "ja",
        "já",
        "disse",
        "imovel",
        "imóvel",
        "veiculo",
        "veículo",
        "investimento",
        "moradia",
        "whatsapp",
    }
    normalized_words = {word.lower() for word in words}
    if normalized_words & blocked:
        return False
    return all(word.replace("-", "").replace("'", "").isalpha() for word in words)


def detect_simulation_adjustment(text: str) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in ("maximo de parcelas", "máximo de parcelas", "maior prazo", "max parcelas", "mais parcelas")):
        return "maximize_installments"
    return None


def detect_delivery_channel(text: str) -> str | None:
    lowered = text.lower()
    if "whatsapp" in lowered or "zap" in lowered:
        return "whatsapp"
    if "e-mail" in lowered or "email" in lowered:
        return "email"
    return None


def detect_pending_user_request(text: str, *, current_topic: str, last_agent_commitment: str | None) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in ("me envie", "pode enviar", "manda", "pode mandar", "envia")):
        return "send_simulation"
    if detect_simulation_adjustment(text):
        return "adjust_simulation"
    if detect_delivery_channel(text):
        return "choose_delivery_channel"
    if any(token in lowered for token in ("o q já passei", "o que ja passei", "já passei", "ja passei", "já disse", "ja disse")):
        return "correct_context"
    if detect_closing_signal(text, []):
        return "close_conversation"
    if detect_human_request(text):
        return "human_handoff"
    if lowered in {"sim", "isso", "pode ser"} and current_topic == "proposal_ready":
        return "confirm_simulation"
    if lowered in {"sim", "isso", "pode ser"} and last_agent_commitment in {"prepare_simulation", "send_simulation"}:
        return last_agent_commitment
    return None


def detect_objection_type(text: str) -> str | None:
    lowered = text.lower()
    objection_map = {
        "fees": ("taxa", "juros", "caro", "custa", "administracao", "administração"),
        "trust": ("seguro", "confiar", "golpe", "medo", "confiavel", "confiável"),
        "comparison": ("financiamento", "financiar", "comparado", "comparacao", "comparação"),
        "lance": ("lance",),
        "timeline": ("contemplac", "contemplação", "quando", "demora", "prazo"),
    }
    for objection_type, tokens in objection_map.items():
        if any(token in lowered for token in tokens):
            return objection_type
    return None


def detect_speech_act(text: str, *, history: list[dict[str, str]], current_topic: str, last_agent_commitment: str | None) -> str:
    lowered = text.lower().strip()
    if detect_human_request(text):
        return "handoff_request"
    if detect_closing_signal(text, history):
        return "closing"
    if detect_objection_type(text):
        return "objection"
    pending_user_request = detect_pending_user_request(
        text,
        current_topic=current_topic,
        last_agent_commitment=last_agent_commitment,
    )
    if pending_user_request == "correct_context":
        return "correction"
    if pending_user_request in {"send_simulation", "adjust_simulation", "choose_delivery_channel"}:
        return "request_action"
    if lowered in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "tudo bem"}:
        return "greeting"
    if lowered in {"sim", "isso", "pode ser"}:
        return "confirmation"
    if lowered in {"nao", "não"}:
        return "negation"
    return "inform"


def missing_business_slots(slots: dict[str, str]) -> list[str]:
    ordered = ("asset_type", "goal", "asset_value", "timeline", "budget_monthly")
    return [slot for slot in ordered if not slots.get(slot)]


def missing_profile_slots(*, missing_profile_fields: list[str], slots: dict[str, str]) -> list[str]:
    if missing_profile_fields:
        normalized = {
            "nome_completo": "lead_name",
            "cpf": "cpf",
            "telefone": "phone",
        }
        return [normalized[item] for item in missing_profile_fields if item in normalized]

    missing: list[str] = []
    if not slots.get("lead_name"):
        missing.append("lead_name")
    if not slots.get("cpf"):
        missing.append("cpf")
    if not slots.get("phone"):
        missing.append("phone")
    return missing


def slot_prompt(slot_name: str, *, greeted: bool) -> list[str]:
    prompts = {
        "lead_name": [
            "Olá! Aqui é da Orfi Consórcios.",
            "Para eu te atender melhor, qual é o seu nome?",
        ]
        if not greeted
        else ["Para eu te atender melhor, qual é o seu nome?"],
        "asset_type": ["Você está buscando imóvel ou veículo?"],
        "goal": ["Seu objetivo principal é morar, investir ou outro?"],
        "asset_value": ["Qual é a faixa de valor do bem que você busca?"],
        "timeline": ["Qual prazo faz sentido para você?"],
        "budget_monthly": ["Qual valor de parcela mensal faz sentido para você?"],
        "cpf": ["Antes de seguir com a simulação, preciso confirmar seu CPF."],
        "phone": ["E qual telefone devo usar no seu cadastro?"],
    }
    return prompts.get(slot_name, ["Me diga um pouco mais para eu seguir com você."])


def follow_up_for_slot(slot_name: str) -> str:
    labels = {
        "lead_name": "nome do lead",
        "asset_type": "tipo de bem",
        "goal": "objetivo principal",
        "asset_value": "faixa de valor",
        "timeline": "prazo",
        "budget_monthly": "parcela mensal",
        "cpf": "CPF",
        "phone": "telefone",
    }
    return f"Capturar {labels.get(slot_name, slot_name)}."


def slot_confirmation(new_slots: dict[str, str]) -> str | None:
    ordered_labels = {
        "lead_name": "nome",
        "asset_type": "bem",
        "goal": "objetivo",
        "asset_value": "valor",
        "timeline": "prazo",
        "budget_monthly": "parcela",
        "lance": "lance",
        "cpf": "CPF",
        "phone": "telefone",
    }
    parts: list[str] = []
    for key in ("lead_name", "asset_type", "goal", "asset_value", "timeline", "budget_monthly", "lance", "cpf", "phone"):
        value = new_slots.get(key)
        if value:
            parts.append(f"{ordered_labels[key]}: {value}")
    if not parts or len(parts) == 1:
        return None
    return f"Perfeito, anotei {'; '.join(parts[:3])}."


def objection_reply(objection_type: str, slots: dict[str, str]) -> str:
    if objection_type == "fees":
        return "Faz sentido olhar isso com cuidado. O melhor caminho aqui é comparar o custo total e o prazo da proposta oficial, sem prometer economia fora do cenário real."
    if objection_type == "trust":
        return "Sua cautela faz sentido. Eu posso te orientar com base no fluxo oficial e, antes de qualquer avanço, deixar a proposta e as condições bem claras."
    if objection_type == "comparison":
        return "A comparação faz sentido, mas ela depende muito do prazo, da parcela e da estratégia de contemplação. O ideal é colocar seu caso no papel antes de concluir qual caminho fica melhor."
    if objection_type == "lance":
        if slots.get("lance"):
            return f"Perfeito. Considerando o lance de {slots['lance']}, eu consigo seguir a conversa sem perder esse ponto."
        return "O lance pode acelerar bastante, mas ele precisa ser analisado junto com valor do bem, prazo e estratégia da proposta."
    if objection_type == "timeline":
        return "Prazo de contemplação é um ponto importante. O ideal é alinhar valor do bem, prazo e estratégia para te orientar com responsabilidade."
    return "Entendi seu ponto. Eu vou te orientar de forma objetiva e sem prometer algo fora do contexto."


def looks_like_restart_question(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "tudo bem",
            "oi",
            "ola",
            "olá",
            "viu minha mensagem",
            "andou",
            "avançou",
            "avancou",
        )
    )
