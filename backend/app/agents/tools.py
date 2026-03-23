from __future__ import annotations

from app.services.vector_store import search_rag_context
from app.core.db import SessionLocal
from app.services.knowledge import search_allowlisted_sources


async def tool_rag_search(tenant_id: str, query: str) -> list[str]:
    records = await search_rag_context(tenant_id, query)
    return [f"{record['content']} (fonte: {record['source']})" for record in records]


async def tool_web_search_allowlist(tenant_id: str, query: str) -> list[str]:
    async with SessionLocal() as session:
        return await search_allowlisted_sources(session, tenant_id, query)


async def tool_followup_scheduler(lead_id: str | None) -> str:
    return f"follow-up queued for {lead_id or 'unknown-lead'}"
