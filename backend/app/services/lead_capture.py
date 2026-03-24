from __future__ import annotations

import re

from app.models.entities import Lead


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) < 10:
        return None
    return digits[:40]


def normalize_cpf(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) != 11 or len(set(digits)) == 1:
        return None
    if not _is_valid_cpf_digits(digits):
        return None
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def extract_cpf(text: str) -> str | None:
    for match in re.finditer(r"\b(?:\d{3}[.\s-]?){3}\d{2}\b", text):
        normalized = normalize_cpf(match.group(0))
        if normalized:
            return normalized
    return None


def extract_full_name(text: str) -> str | None:
    cleaned = " ".join(text.replace("\n", " ").split()).strip()
    if not cleaned or any(char.isdigit() for char in cleaned):
        return None
    match = re.search(
        r"\b(?:meu nome e|me chamo|sou)\s+([A-Za-zÀ-ÿ'`-]+(?:\s+[A-Za-zÀ-ÿ'`-]+){1,5})$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = " ".join(match.group(1).split())
        return candidate.title()
    words = cleaned.split()
    if 2 <= len(words) <= 6 and all(word.replace("-", "").replace("'", "").isalpha() for word in words):
        return " ".join(word.title() for word in words)
    return None


def is_complete_name(value: str | None) -> bool:
    if not value:
        return False
    words = [word for word in value.split() if word]
    return len(words) >= 2 and not any(char.isdigit() for char in value)


def required_profile_fields(lead: Lead) -> list[str]:
    missing: list[str] = []
    if not is_complete_name(lead.name):
        missing.append("nome_completo")
    if not normalize_cpf(getattr(lead, "cpf", None)):
        missing.append("cpf")
    if not normalize_phone(lead.phone):
        missing.append("telefone")
    return missing


def apply_lead_capture(lead: Lead, *, text: str, fallback_phone: str | None = None) -> list[str]:
    changes: list[str] = []

    full_name = extract_full_name(text)
    if full_name and (not is_complete_name(lead.name) or len(full_name) > len(lead.name or "")):
        lead.name = full_name
        changes.append("nome_completo")

    cpf = extract_cpf(text)
    if cpf and cpf != getattr(lead, "cpf", None):
        lead.cpf = cpf
        changes.append("cpf")

    phone = normalize_phone(fallback_phone) or normalize_phone(lead.phone)
    if phone and phone != lead.phone:
        lead.phone = phone
        changes.append("telefone")

    metadata = dict(lead.metadata_json or {})
    metadata["required_profile_fields_missing"] = required_profile_fields(lead)
    lead.metadata_json = metadata
    return changes


def describe_lead_profile(lead: Lead) -> str:
    missing = required_profile_fields(lead)
    if not missing:
        return "cadastro_obrigatorio_completo"
    return "faltando=" + ",".join(missing)


def next_required_profile_field_label(lead: Lead) -> str | None:
    label_map = {
        "nome_completo": "nome completo",
        "cpf": "CPF",
        "telefone": "telefone",
    }
    missing = required_profile_fields(lead)
    if not missing:
        return None
    return label_map.get(missing[0], missing[0])


def _is_valid_cpf_digits(digits: str) -> bool:
    if len(digits) != 11:
        return False

    def calculate_digit(base: str, factor: int) -> str:
        total = sum(int(char) * weight for char, weight in zip(base, range(factor, 1, -1)))
        remainder = (total * 10) % 11
        return "0" if remainder == 10 else str(remainder)

    first = calculate_digit(digits[:9], 10)
    second = calculate_digit(digits[:10], 11)
    return digits[-2:] == first + second
