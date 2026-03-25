from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

MAX_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_UPLOAD_ROOT = Path("/data/uploads") if Path("/data").exists() else Path("uploads")
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", str(DEFAULT_UPLOAD_ROOT)))
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "image/jpeg",
    "image/png",
    "image/webp",
    "audio/mpeg",
    "audio/wav",
    "audio/mp4",
    "video/mp4",
    "video/webm",
}


def _ensure_valid_mime(mime_type: str | None) -> str:
    if mime_type and mime_type in ALLOWED_MIME_TYPES:
        return mime_type
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported MIME type")


def _ensure_valid_size(size_bytes: int) -> None:
    if size_bytes <= MAX_SIZE_BYTES:
        return
    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")


async def persist_upload(file: UploadFile) -> tuple[str, str, int, str]:
    mime_type = _ensure_valid_mime(file.content_type)
    content = await file.read()
    size_bytes = len(content)
    _ensure_valid_size(size_bytes)

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename or "upload.bin").suffix.lower()
    file_id = str(uuid4())
    destination = UPLOAD_ROOT / f"{file_id}{extension}"
    destination.write_bytes(content)

    checksum = sha256(content).hexdigest()
    return str(destination), checksum, size_bytes, mime_type
