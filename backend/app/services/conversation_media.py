from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

import httpx
from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings

settings = get_settings()


def _get_client() -> AsyncOpenAI | None:
    if not settings.resolved_openai_api_key:
        return None
    return AsyncOpenAI(api_key=settings.resolved_openai_api_key, timeout=settings.openai_timeout_seconds)


async def _read_media_bytes(file_ref: str) -> tuple[bytes, str]:
    if file_ref.startswith("http://") or file_ref.startswith("https://"):
        headers: dict[str, str] = {}
        gateway_base = settings.whatsapp_gateway_base_url.rstrip("/")
        if file_ref.startswith(gateway_base) and settings.whatsapp_gateway_secret:
            headers["X-WhatsApp-Gateway-Secret"] = settings.whatsapp_gateway_secret
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(file_ref)
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0].strip()
            return response.content, mime_type

    path = Path(file_ref)
    if not path.exists():
        raise FileNotFoundError(file_ref)
    mime_type = "application/octet-stream"
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime_type = "image/jpeg"
    elif suffix == ".png":
        mime_type = "image/png"
    elif suffix == ".webp":
        mime_type = "image/webp"
    elif suffix in {".mp3", ".mpeg"}:
        mime_type = "audio/mpeg"
    elif suffix == ".wav":
        mime_type = "audio/wav"
    elif suffix == ".m4a" or suffix == ".mp4":
        mime_type = "audio/mp4" if suffix == ".m4a" else "video/mp4"
    return path.read_bytes(), mime_type


async def transcribe_audio(file_ref: str, mime_type: str | None = None) -> str:
    client = _get_client()
    if client is None:
        return f"transcricao pendente para {file_ref}"

    try:
        payload, detected_mime = await _read_media_bytes(file_ref)
        transcription_model = getattr(settings, "openai_audio_transcription_model", "whisper-1")
        filename = Path(file_ref).name if not file_ref.startswith(("http://", "https://")) else "audio"
        upload_name = filename or "audio"
        if not upload_name.lower().endswith((".mp3", ".mpeg", ".wav", ".m4a", ".mp4")):
            upload_name = f"{upload_name}.mp3"
        with tempfile.NamedTemporaryFile(suffix=Path(upload_name).suffix or ".mp3", delete=False) as tmp:
            tmp.write(payload)
            tmp.flush()
            tmp_path = Path(tmp.name)
        try:
            with tmp_path.open("rb") as audio_file:
                response = await client.audio.transcriptions.create(model=transcription_model, file=audio_file)
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        text = getattr(response, "text", "") if response is not None else ""
        if isinstance(text, str) and text.strip():
            return text.strip()
        return "Nao foi possivel extrair transcricao util do audio."
    except (OpenAIError, OSError, httpx.HTTPError) as exc:
        return f"Falha ao transcrever audio: {exc}"


async def analyze_image(file_ref: str, caption: str | None = None, mime_type: str | None = None) -> str:
    client = _get_client()
    if client is None:
        return f"analise de imagem pendente para {file_ref}"

    try:
        payload, detected_mime = await _read_media_bytes(file_ref)
        media_type = mime_type or detected_mime or "image/jpeg"
        data_url = f"data:{media_type};base64,{base64.b64encode(payload).decode('ascii')}"
        prompt = caption or "Analise a imagem com foco em contexto comercial e diga os fatos uteis para um atendimento."
        response = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Voce descreve imagens em portugues do Brasil de forma objetiva, "
                        "extraindo fatos uteis para vendas e suporte."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        )
        if not response.choices:
            return "Nao foi possivel analisar a imagem."
        content = getattr(response.choices[0].message, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
        return "Nao foi possivel analisar a imagem."
    except (OpenAIError, OSError, httpx.HTTPError) as exc:
        return f"Falha ao analisar imagem: {exc}"


async def summarize_media_item(item: dict[str, Any]) -> str:
    kind = str(item.get("kind") or item.get("type") or "").lower().strip()
    file_ref = str(item.get("file_ref") or item.get("url") or item.get("path") or "").strip()
    caption = item.get("caption")
    mime_type = item.get("mime_type")

    if not file_ref:
        return ""

    if kind in {"audio", "voice"} or (mime_type and str(mime_type).startswith("audio/")):
        transcript = await transcribe_audio(file_ref, mime_type=mime_type)
        return f"audio={file_ref}; transcript={transcript}"

    if kind in {"image", "photo"} or (mime_type and str(mime_type).startswith("image/")):
        analysis = await analyze_image(file_ref, caption=str(caption) if caption else None, mime_type=mime_type)
        return f"image={file_ref}; analysis={analysis}"

    return f"{kind or 'media'}={file_ref}"


async def summarize_media_attachments(items: list[dict[str, Any]] | None) -> list[str]:
    if not items:
        return []
    notes: list[str] = []
    for item in items:
        note = await summarize_media_item(item)
        if note:
            notes.append(note)
    return notes
