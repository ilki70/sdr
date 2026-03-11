import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    backend_webhook_url: str = Field(alias="BACKEND_WEBHOOK_URL")
    default_inbox_ref: str = Field(default="whatsapp-default", alias="WHATSAPP_DEFAULT_INBOX_REF")
    webhook_secret: str = Field(default="", alias="WHATSAPP_WEBHOOK_SECRET")
    data_dir: str = Field(default="/data", alias="WHATSAPP_SERVICE_DATA_DIR")
    service_port: int = Field(default=8080, alias="WHATSAPP_SERVICE_PORT")
    request_timeout_seconds: int = Field(default=20, alias="WHATSAPP_REQUEST_TIMEOUT_SECONDS")


settings = Settings()
app = FastAPI(title="WhatsApp Service", debug=False)
events_path = Path(settings.data_dir) / "events.jsonl"
events_path.parent.mkdir(parents=True, exist_ok=True)


class InboundMessageRequest(BaseModel):
    message_text: str = Field(min_length=1, max_length=4000)
    contact_id: str = Field(min_length=1, max_length=128)
    inbox_ref: str | None = Field(default=None, max_length=128)
    webhook_secret: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=140)
    contact_phone: str | None = Field(default=None, max_length=40)
    external_message_id: str | None = Field(default=None, max_length=128)
    external_conversation_id: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None


def _append_event(kind: str, payload: dict[str, Any]) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "payload": payload,
    }
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _load_recent_events(limit: int) -> list[dict[str, Any]]:
    if not events_path.exists():
        return []
    lines = events_path.read_text(encoding="utf-8").splitlines()
    selected = lines[-limit:]
    return [json.loads(line) for line in selected if line.strip()]


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "whatsapp-service", "data_file": str(events_path)}


@app.get("/api/events")
async def list_events(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    return {"items": _load_recent_events(limit)}


@app.post("/api/messages/inbound")
async def post_inbound_message(payload: InboundMessageRequest) -> dict[str, Any]:
    backend_payload = {
        "inbox_ref": payload.inbox_ref or settings.default_inbox_ref,
        "webhook_secret": payload.webhook_secret or settings.webhook_secret,
        "message_text": payload.message_text,
        "contact_id": payload.contact_id,
        "contact_name": payload.contact_name,
        "contact_phone": payload.contact_phone,
        "external_message_id": payload.external_message_id,
        "external_conversation_id": payload.external_conversation_id,
        "metadata_json": payload.metadata_json or {},
    }
    _append_event("inbound_received", backend_payload)

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(settings.backend_webhook_url, json=backend_payload)
    except httpx.HTTPError as exc:
        _append_event("backend_error", {"error": str(exc), "request": backend_payload})
        raise HTTPException(status_code=502, detail="Backend webhook unavailable") from exc

    response_payload = response.json()
    _append_event(
        "backend_response",
        {
            "status_code": response.status_code,
            "request": backend_payload,
            "response": response_payload,
        },
    )
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail=response_payload)

    return response_payload
