from __future__ import annotations


def _clean_fragment(text: str) -> str:
    return " ".join(str(text).split()).strip()


def _split_long_fragment(text: str, *, max_chars: int) -> list[str]:
    cleaned = _clean_fragment(text)
    if len(cleaned) <= max_chars:
        return [cleaned] if cleaned else []

    parts: list[str] = []
    remaining = cleaned
    while len(remaining) > max_chars:
        split_at = remaining.rfind(". ", 0, max_chars + 1)
        if split_at == -1:
            split_at = remaining.rfind("? ", 0, max_chars + 1)
        if split_at == -1:
            split_at = remaining.rfind("! ", 0, max_chars + 1)
        if split_at == -1:
            split_at = remaining.rfind(", ", 0, max_chars + 1)
        if split_at == -1:
            split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at == -1 or split_at < max_chars // 2:
            split_at = max_chars
        else:
            split_at += 1
        part = _clean_fragment(remaining[:split_at])
        if part:
            parts.append(part)
        remaining = remaining[split_at:].strip()
    if remaining:
        parts.append(_clean_fragment(remaining))
    return parts


def format_reply(channel: str, fragments: list[str]) -> tuple[str, list[str]]:
    cleaned_fragments = [_clean_fragment(fragment) for fragment in fragments if _clean_fragment(fragment)]
    if not cleaned_fragments:
        return "", []

    if channel == "whatsapp":
        formatted_fragments: list[str] = []
        for fragment in cleaned_fragments:
            formatted_fragments.extend(_split_long_fragment(fragment, max_chars=180))
        return "\n\n".join(formatted_fragments), formatted_fragments

    return "\n\n".join(cleaned_fragments), cleaned_fragments
