from __future__ import annotations

import html
import io
import logging
import re
import unicodedata
import zipfile
from hashlib import sha256
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow_naive
from app.models.entities import KnowledgeChunk, KnowledgeSource
from app.services.knowledge_ops import record_source_version
from app.services.vector_store import delete_source_chunks, search_rag_context, upsert_source_chunks

logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[a-zA-Z0-9À-ÿ]{2,}")
SYNONYM_HINTS = {
    "seminovo": ["3 anos", "ate 3 anos", "limite de idade"],
    "idade": ["3 anos", "ate 3 anos", "seminovo"],
    "adesao": ["proposta", "contrato digital", "primeira parcela", "concorrer"],
    "orcamento": ["1.000", "1000", "faixa de parcelas", "simulacao"],
    "confiavel": ["banco central", "certidao", "abac"],
    "financiamento": ["sem juros", "taxa de administracao"],
    "carta": ["outro modelo", "onde comprar", "carta de credito"],
}


@dataclass(frozen=True)
class ExtractedSource:
    source_type: str
    title: str
    summary: str
    content: str


def _normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _extract_html_text(raw_html: str) -> ExtractedSource:
    title_match = TITLE_RE.search(raw_html)
    description_match = DESCRIPTION_RE.search(raw_html)
    title = html.unescape(title_match.group(1)).strip() if title_match else "Pagina web"
    description = html.unescape(description_match.group(1)).strip() if description_match else ""

    sanitized = SCRIPT_STYLE_RE.sub(" ", raw_html)
    sanitized = TAG_RE.sub(" ", sanitized)
    text = _normalize_text(html.unescape(sanitized))
    summary = description or text[:220]
    content = f"TITULO: {title}\nDESCRICAO: {summary}\nCONTEUDO: {text}"
    return ExtractedSource(source_type="web_page", title=title, summary=summary, content=content)


def _extract_pdf_text(binary_content: bytes, source_ref: str) -> ExtractedSource:
    pages: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(binary_content))
        for page in reader.pages[:16]:
            extracted = page.extract_text() or ""
            if extracted.strip():
                pages.append(extracted)
    except Exception:
        pages = []
    raw_text = _normalize_text(" ".join(pages))
    title = Path(source_ref).name or source_ref.rsplit("/", 1)[-1]
    summary = raw_text[:220] if raw_text else f"Documento PDF oficial: {title}"
    content = f"TITULO: {title}\nDESCRICAO: {summary}\nCONTEUDO: {raw_text or summary}"
    return ExtractedSource(source_type="pdf", title=title, summary=summary, content=content)


def _extract_docx_text(binary_content: bytes, source_ref: str) -> ExtractedSource:
    try:
        with zipfile.ZipFile(io.BytesIO(binary_content)) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nao foi possivel extrair o DOCX: {exc}",
        ) from exc

    text = TAG_RE.sub(" ", document_xml)
    text = _normalize_text(html.unescape(text))
    title = Path(source_ref).name
    summary = text[:220] if text else f"Documento DOCX: {title}"
    content = f"TITULO: {title}\nDESCRICAO: {summary}\nCONTEUDO: {text or summary}"
    return ExtractedSource(source_type="docx", title=title, summary=summary, content=content)


def _extract_plain_text(binary_content: bytes, source_ref: str) -> ExtractedSource:
    text = binary_content.decode("utf-8", errors="ignore")
    normalized = _normalize_text(text)
    title = Path(source_ref).name
    summary = normalized[:220] if normalized else f"Documento texto: {title}"
    content = f"TITULO: {title}\nDESCRICAO: {summary}\nCONTEUDO: {normalized or summary}"
    return ExtractedSource(source_type="text", title=title, summary=summary, content=content)


async def _extract_youtube_text(client: httpx.AsyncClient, source_ref: str) -> ExtractedSource:
    oembed_url = f"https://www.youtube.com/oembed?url={quote_plus(source_ref)}&format=json"
    response = await client.get(oembed_url, timeout=20.0)
    response.raise_for_status()
    payload = response.json()
    title = payload.get("title", "Video YouTube")
    author_name = payload.get("author_name", "canal oficial")
    summary = f"Video oficial do YouTube: {title}. Canal: {author_name}."
    content = (
        f"TITULO: {title}\n"
        f"DESCRICAO: {summary}\n"
        f"CONTEUDO: Use este video como referencia oficial de funcionamento e apresentacao do produto."
    )
    return ExtractedSource(source_type="youtube_video", title=title, summary=summary, content=content)


def _resolve_local_path(source_ref: str) -> Path | None:
    raw_path = Path(source_ref)
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.extend(
            [
                raw_path,
                Path.cwd() / raw_path,
                BACKEND_ROOT / raw_path,
                PROJECT_ROOT / raw_path,
            ]
        )

    seen: set[Path] = set()
    for candidate in candidates:
        normalized = candidate.resolve(strict=False)
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized.exists():
            return normalized
    return None


def _extract_local_file(source_ref: str) -> ExtractedSource:
    path = _resolve_local_path(source_ref)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo local nao encontrado")

    binary_content = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(binary_content, source_ref)
    if suffix == ".docx":
        return _extract_docx_text(binary_content, source_ref)
    if suffix in {".txt", ".md"}:
        return _extract_plain_text(binary_content, source_ref)
    if suffix == ".doc":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivos .doc nao sao suportados no MVP")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de arquivo nao suportado para conhecimento")


async def extract_source_from_url(source_ref: str) -> ExtractedSource:
    parsed = urlparse(source_ref)
    hostname = parsed.netloc.lower()
    if "youtube.com" in hostname or "youtu.be" in hostname:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            return await _extract_youtube_text(client, source_ref)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(source_ref, timeout=30.0)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" in content_type or source_ref.lower().endswith(".pdf"):
            return _extract_pdf_text(response.content, source_ref)
        return _extract_html_text(response.text)


async def extract_source_from_ref(source_ref: str) -> ExtractedSource:
    parsed = urlparse(source_ref)
    if parsed.scheme in {"http", "https"}:
        return await extract_source_from_url(source_ref)
    return _extract_local_file(source_ref)


def chunk_text(content: str, chunk_size: int = 900, overlap: int = 180) -> list[str]:
    normalized = _normalize_text(content)
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start += step
    return chunks


async def list_knowledge_sources(
    db: AsyncSession,
    tenant_id: str,
    product_id: str | None = None,
) -> list[KnowledgeSource]:
    query = select(KnowledgeSource).where(
        KnowledgeSource.tenant_id == tenant_id,
        KnowledgeSource.deleted_at.is_(None),
    )
    if product_id:
        query = query.where(KnowledgeSource.product_id == product_id)
    result = await db.execute(query.order_by(KnowledgeSource.updated_at.desc()))
    return list(result.scalars().all())


async def get_knowledge_source_or_none(
    db: AsyncSession,
    tenant_id: str,
    source_id: str,
) -> KnowledgeSource | None:
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.tenant_id == tenant_id,
            KnowledgeSource.id == source_id,
            KnowledgeSource.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _build_or_update_source(
    db: AsyncSession,
    tenant_id: str,
    product_id: str,
    source_ref: str,
    source_type: str,
) -> KnowledgeSource:
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.tenant_id == tenant_id,
            KnowledgeSource.product_id == product_id,
            KnowledgeSource.source_ref == source_ref,
            KnowledgeSource.deleted_at.is_(None),
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        source = KnowledgeSource(
            id=str(uuid4()),
            tenant_id=tenant_id,
            product_id=product_id,
            source_type=source_type,
            source_ref=source_ref,
            status="processing",
            version_no=1,
            last_indexed_at=None,
        )
        db.add(source)
        await db.flush()
        return source

    source.source_type = source_type
    source.status = "processing"
    source.version_no += 1
    return source


async def _replace_source_chunks(
    db: AsyncSession,
    source: KnowledgeSource,
    extracted: ExtractedSource,
    chunks: list[str],
) -> None:
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id))

    chunk_records: list[dict[str, str | int]] = []
    for index, chunk in enumerate(chunks):
        chunk_id = str(uuid4())
        db.add(
            KnowledgeChunk(
                id=chunk_id,
                tenant_id=source.tenant_id,
                source_id=source.id,
                chunk_index=index,
                content=chunk,
                embedding_ref=f"{source.id}:{index}",
                token_count=len(chunk.split()),
            )
        )
        chunk_records.append({"id": chunk_id, "chunk_index": index, "content": chunk})

    await record_source_version(
        db=db,
        tenant_id=source.tenant_id,
        source_id=source.id,
        version_no=source.version_no,
        title=extracted.title,
        source_type=source.source_type,
        source_ref=source.source_ref,
        content_hash=sha256(extracted.content.encode("utf-8", errors="ignore")).hexdigest(),
        content_text=extracted.content,
    )

    await db.flush()
    await delete_source_chunks(source.id)
    try:
        await upsert_source_chunks(
            tenant_id=source.tenant_id,
            product_id=source.product_id,
            source_id=source.id,
            source_ref=source.source_ref,
            source_type=source.source_type,
            chunks=chunk_records,
        )
        source.status = "ready"
    except Exception:
        logger.exception("knowledge_vector_index_failed", extra={"source_id": source.id})
        source.status = "ready_lexical_only"
    source.last_indexed_at = utcnow_naive()


async def ingest_knowledge_source(
    db: AsyncSession,
    tenant_id: str,
    product_id: str,
    source_ref: str,
) -> KnowledgeSource:
    extracted = await extract_source_from_ref(source_ref)
    source = await _build_or_update_source(db, tenant_id, product_id, source_ref, extracted.source_type)
    await _replace_source_chunks(db, source, extracted, chunk_text(extracted.content))
    await db.commit()
    await db.refresh(source)
    return source


async def reingest_knowledge_source(db: AsyncSession, source: KnowledgeSource) -> KnowledgeSource:
    extracted = await extract_source_from_ref(source.source_ref)
    source.source_type = extracted.source_type
    source.version_no += 1
    await _replace_source_chunks(db, source, extracted, chunk_text(extracted.content))
    await db.commit()
    await db.refresh(source)
    return source


async def ingest_manual_knowledge(
    db: AsyncSession,
    tenant_id: str,
    product_id: str,
    source_ref: str,
    title: str,
    content: str,
    source_type: str = "playbook_note",
) -> KnowledgeSource:
    source = await _build_or_update_source(db, tenant_id, product_id, source_ref, source_type)
    full_content = f"TITULO: {title}\nCONTEUDO: {content}"
    await _replace_source_chunks(
        db,
        source,
        ExtractedSource(source_type=source_type, title=title, summary=content[:220], content=full_content),
        chunk_text(full_content),
    )
    await db.commit()
    await db.refresh(source)
    return source


def _tokenize(value: str) -> set[str]:
    return {match.group(0).lower() for match in WORD_RE.finditer(_fold(value))}


def _expand_query_tokens(query_tokens: set[str]) -> set[str]:
    expanded = set(query_tokens)
    for token in list(query_tokens):
        for hint in SYNONYM_HINTS.get(token, []):
            expanded.update(_tokenize(hint))
    return expanded


def _score_chunk(content: str, query_tokens: set[str], source_ref: str) -> float:
    haystack = _fold(content)
    source_value = _fold(source_ref)
    score = 0.0
    for token in query_tokens:
        if token in haystack:
            score += 2.0
        if token in source_value:
            score += 1.0
    for token in query_tokens:
        for hint in SYNONYM_HINTS.get(token, []):
            if _fold(hint) in haystack:
                score += 2.5
    return score


async def search_knowledge_chunks_lexical(
    db: AsyncSession,
    tenant_id: str,
    query: str,
    limit: int = 5,
    product_id: str | None = None,
) -> list[dict[str, str | float]]:
    query_tokens = _expand_query_tokens(_tokenize(query))
    if not query_tokens:
        return []

    statement = (
        select(KnowledgeChunk, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(KnowledgeChunk.tenant_id == tenant_id, KnowledgeSource.deleted_at.is_(None))
    )
    if product_id:
        statement = statement.where(KnowledgeSource.product_id == product_id)

    result = await db.execute(statement)
    ranked: list[dict[str, str | float]] = []
    for chunk, source in result.all():
        score = _score_chunk(chunk.content, query_tokens, source.source_ref)
        if score <= 0:
            continue
        ranked.append(
            {
                "source_id": source.id,
                "product_id": source.product_id,
                "source": source.source_ref,
                "source_type": source.source_type,
                "score": score,
                "content": chunk.content,
            }
        )

    ranked.sort(key=lambda item: float(item["score"]), reverse=True)
    return ranked[:limit]


async def search_allowlisted_sources(
    db: AsyncSession,
    tenant_id: str,
    query: str,
    limit: int = 3,
) -> list[str]:
    chunks = await search_rag_context(tenant_id, query, limit=limit * 2)
    seen_sources: set[str] = set()
    results: list[str] = []
    for item in chunks:
        source = str(item["source"])
        if source in seen_sources:
            continue
        seen_sources.add(source)
        excerpt = str(item["content"])[:180].strip()
        results.append(f"Fonte oficial: {source} | Trecho: {excerpt}")
        if len(results) >= limit:
            break
    return results
