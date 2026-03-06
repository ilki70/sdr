from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.embeddings import embed_texts, embedding_dimensions, embeddings_enabled

settings = get_settings()
logger = logging.getLogger(__name__)


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url or "http://localhost:6333",
        timeout=10,
        check_compatibility=False,
    )


async def ensure_collection() -> None:
    if not settings.qdrant_url:
        return
    client = get_qdrant_client()
    exists = await asyncio.to_thread(client.collection_exists, settings.qdrant_collection_name)
    if exists:
        return
    await asyncio.to_thread(
        client.create_collection,
        collection_name=settings.qdrant_collection_name,
        vectors_config=VectorParams(size=embedding_dimensions(), distance=Distance.COSINE),
    )


async def upsert_source_chunks(
    tenant_id: str,
    product_id: str,
    source_id: str,
    source_ref: str,
    source_type: str,
    chunks: list[dict[str, Any]],
) -> None:
    if not embeddings_enabled() or not chunks:
        return

    await ensure_collection()
    vectors = await embed_texts([str(chunk["content"]) for chunk in chunks])
    points = [
        PointStruct(
            id=str(chunk["id"]),
            vector=vector,
            payload={
                "tenant_id": tenant_id,
                "product_id": product_id,
                "source_id": source_id,
                "source_ref": source_ref,
                "source_type": source_type,
                "chunk_index": int(chunk["chunk_index"]),
                "content": str(chunk["content"]),
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=False)
    ]
    if not points:
        return
    client = get_qdrant_client()
    await asyncio.to_thread(client.upsert, settings.qdrant_collection_name, points, True)


async def delete_source_chunks(source_id: str) -> None:
    if not settings.qdrant_url:
        return
    client = get_qdrant_client()
    exists = await asyncio.to_thread(client.collection_exists, settings.qdrant_collection_name)
    if not exists:
        return
    await asyncio.to_thread(
        client.delete,
        settings.qdrant_collection_name,
        Filter(
            must=[
                FieldCondition(key="source_id", match=MatchValue(value=source_id)),
            ]
        ),
        True,
    )


async def semantic_search_rag_context(
    tenant_id: str,
    query: str,
    limit: int = 5,
    product_id: str | None = None,
) -> list[dict[str, Any]]:
    if not embeddings_enabled():
        return []

    await ensure_collection()
    vector = (await embed_texts([query]))[0]
    filters = [FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    if product_id:
        filters.append(FieldCondition(key="product_id", match=MatchValue(value=product_id)))

    client = get_qdrant_client()
    response = await asyncio.to_thread(
        client.query_points,
        settings.qdrant_collection_name,
        query=vector,
        query_filter=Filter(must=filters),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    points = getattr(response, "points", [])
    results: list[dict[str, Any]] = []
    for point in points:
        payload = point.payload or {}
        results.append(
            {
                "source_id": str(payload.get("source_id", "")),
                "product_id": str(payload.get("product_id", "")),
                "source": str(payload.get("source_ref", "")),
                "source_type": str(payload.get("source_type", "")),
                "score": float(point.score or 0),
                "content": str(payload.get("content", "")),
            }
        )
    return results


async def search_rag_context(
    tenant_id: str,
    query: str,
    limit: int = 5,
    product_id: str | None = None,
) -> list[dict[str, Any]]:
    semantic_results: list[dict[str, Any]] = []
    try:
        semantic_results = await semantic_search_rag_context(tenant_id, query, limit=limit, product_id=product_id)
    except Exception:
        logger.exception("semantic_search_failed", extra={"tenant_id": tenant_id, "product_id": product_id or ""})

    from app.services.knowledge import search_knowledge_chunks_lexical

    async with SessionLocal() as session:
        lexical_results = await search_knowledge_chunks_lexical(
            session,
            tenant_id,
            query,
            limit=limit,
            product_id=product_id,
        )

    if not semantic_results:
        return lexical_results
    if not lexical_results:
        return semantic_results

    combined: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in lexical_results + semantic_results:
        key = (str(item.get("source_id", "")), str(item.get("content", "")))
        if key in seen:
            continue
        seen.add(key)
        combined.append(item)
        if len(combined) >= limit:
            break
    return combined
