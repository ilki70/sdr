from __future__ import annotations

from typing import Any


GENERIC_RUNTIME_STATE_KEY = "conversation_runtime_state"


def get_runtime_state(metadata: dict[str, Any] | None, *, source: str | None = None) -> dict[str, Any]:
    payload = dict(metadata or {})
    if source:
        scoped_state = payload.get(f"{source}_runtime_state")
        if isinstance(scoped_state, dict) and scoped_state:
            return dict(scoped_state)
    generic_state = payload.get(GENERIC_RUNTIME_STATE_KEY)
    if isinstance(generic_state, dict):
        return dict(generic_state)
    return {}


def store_runtime_state(
    metadata: dict[str, Any] | None,
    runtime_state: dict[str, Any] | None,
    *,
    source: str,
) -> dict[str, Any]:
    payload = dict(metadata or {})
    if not isinstance(runtime_state, dict) or not runtime_state:
        return payload

    normalized_runtime_state = {
        key: value
        for key, value in runtime_state.items()
        if isinstance(key, str)
    }
    payload[GENERIC_RUNTIME_STATE_KEY] = normalized_runtime_state
    payload[f"{source}_runtime_state"] = dict(normalized_runtime_state)
    return payload
