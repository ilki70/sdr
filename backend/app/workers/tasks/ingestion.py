from __future__ import annotations

import asyncio
from typing import Any

from app.core.db import SessionLocal
from app.models.entities import KnowledgeSource
from app.services.knowledge import ingest_knowledge_source, reingest_knowledge_source
from app.services.knowledge_ops import (
    get_knowledge_job_by_id,
    mark_job_finished,
    mark_job_started,
)
from app.services.vinac_lab import ensure_vinac_knowledge
from app.workers.celery_app import celery_app


async def _run_knowledge_job(job_id: str, task_id: str | None) -> dict[str, Any]:
    async with SessionLocal() as session:
        job = await get_knowledge_job_by_id(session, job_id)
        if not job:
            raise ValueError(f"knowledge_job_not_found:{job_id}")
        await mark_job_started(session, job, celery_task_id=task_id)
        tenant_id = job.tenant_id
        product_id = job.product_id
        payload = job.input_json or {}

    source_ids: list[str] = []
    indexed_sources: list[str] = []
    async with SessionLocal() as session:
        job = await get_knowledge_job_by_id(session, job_id)
        assert job is not None
        try:
            if job.job_type == "ingest_url":
                source = await ingest_knowledge_source(session, tenant_id, product_id, str(payload["source_ref"]))
                source_ids.append(source.id)
                indexed_sources.append(source.source_ref)
                await mark_job_finished(
                    session,
                    job,
                    status="completed",
                    result_json={"indexed_sources": indexed_sources, "source_ids": source_ids},
                    source_id=source.id,
                )
            elif job.job_type == "reingest_source":
                source = await session.get(KnowledgeSource, str(payload["source_id"]))
                if not source or source.tenant_id != tenant_id:
                    raise ValueError(f"knowledge_source_not_found:{payload['source_id']}")
                source = await reingest_knowledge_source(session, source)
                source_ids.append(source.id)
                indexed_sources.append(source.source_ref)
                await mark_job_finished(
                    session,
                    job,
                    status="completed",
                    result_json={"indexed_sources": indexed_sources, "source_ids": source_ids},
                    source_id=source.id,
                )
            elif job.job_type == "ingest_file":
                source = await ingest_knowledge_source(session, tenant_id, product_id, str(payload["source_ref"]))
                source_ids.append(source.id)
                indexed_sources.append(source.source_ref)
                await mark_job_finished(
                    session,
                    job,
                    status="completed",
                    result_json={"indexed_sources": indexed_sources, "source_ids": source_ids},
                    source_id=source.id,
                )
            elif job.job_type == "ingest_vinac_official":
                indexed_sources = await ensure_vinac_knowledge(tenant_id, product_id)
                await mark_job_finished(
                    session,
                    job,
                    status="completed",
                    result_json={"indexed_sources": indexed_sources, "total_sources": len(indexed_sources)},
                )
            else:
                raise ValueError(f"unsupported_job_type:{job.job_type}")
        except Exception as exc:
            await mark_job_finished(session, job, status="failed", error_message=str(exc))
            raise

    return {"status": "completed", "source_ids": source_ids, "indexed_sources": indexed_sources}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2, "countdown": 5})
def ingest_knowledge_job(self, job_id: str) -> dict[str, Any]:
    return asyncio.run(_run_knowledge_job(job_id, self.request.id))
