from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

EMBEDDING_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


@lru_cache
def get_embedding_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)


def embeddings_enabled() -> bool:
    return bool(settings.openai_api_key and settings.qdrant_url)


def embedding_dimensions() -> int:
    return EMBEDDING_DIMS.get(settings.openai_embedding_model, 1536)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = get_embedding_client()
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    return [list(item.embedding) for item in response.data]
