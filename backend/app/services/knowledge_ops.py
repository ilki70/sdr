from __future__ import annotations

import difflib
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow_naive
from app.models.entities import EvaluationRun, KnowledgeJob, KnowledgeSourceVersion


async def create_knowledge_job(
    db: AsyncSession,
    tenant_id: str,
    product_id: str,
    created_by_user_id: str,
    job_type: str,
    input_json: dict,
    source_id: str | None = None,
) -> KnowledgeJob:
    job = KnowledgeJob(
        id=str(uuid4()),
        tenant_id=tenant_id,
        product_id=product_id,
        source_id=source_id,
        created_by_user_id=created_by_user_id,
        job_type=job_type,
        status="queued",
        input_json=input_json,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_knowledge_job_or_none(db: AsyncSession, tenant_id: str, job_id: str) -> KnowledgeJob | None:
    result = await db.execute(
        select(KnowledgeJob).where(KnowledgeJob.tenant_id == tenant_id, KnowledgeJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def get_knowledge_job_by_id(db: AsyncSession, job_id: str) -> KnowledgeJob | None:
    result = await db.execute(select(KnowledgeJob).where(KnowledgeJob.id == job_id))
    return result.scalar_one_or_none()


async def list_knowledge_jobs(
    db: AsyncSession,
    tenant_id: str,
    product_id: str | None = None,
    limit: int = 20,
) -> list[KnowledgeJob]:
    query = select(KnowledgeJob).where(KnowledgeJob.tenant_id == tenant_id)
    if product_id:
        query = query.where(KnowledgeJob.product_id == product_id)
    result = await db.execute(query.order_by(KnowledgeJob.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def mark_job_started(db: AsyncSession, job: KnowledgeJob, celery_task_id: str | None = None) -> None:
    job.status = "running"
    job.started_at = utcnow_naive()
    if celery_task_id:
        job.celery_task_id = celery_task_id
    await db.commit()


async def mark_job_finished(
    db: AsyncSession,
    job: KnowledgeJob,
    status: str,
    result_json: dict | None = None,
    error_message: str | None = None,
    source_id: str | None = None,
) -> None:
    job.status = status
    job.result_json = result_json
    job.error_message = error_message
    job.finished_at = utcnow_naive()
    if source_id:
        job.source_id = source_id
    await db.commit()


async def record_source_version(
    db: AsyncSession,
    tenant_id: str,
    source_id: str,
    version_no: int,
    title: str | None,
    source_type: str,
    source_ref: str,
    content_hash: str | None,
    content_text: str,
) -> KnowledgeSourceVersion:
    version = KnowledgeSourceVersion(
        id=str(uuid4()),
        tenant_id=tenant_id,
        source_id=source_id,
        version_no=version_no,
        title=title,
        source_type=source_type,
        source_ref=source_ref,
        content_hash=content_hash,
        content_text=content_text,
    )
    db.add(version)
    await db.flush()
    return version


async def list_source_versions(db: AsyncSession, tenant_id: str, source_id: str, limit: int = 10) -> list[KnowledgeSourceVersion]:
    result = await db.execute(
        select(KnowledgeSourceVersion)
        .where(KnowledgeSourceVersion.tenant_id == tenant_id, KnowledgeSourceVersion.source_id == source_id)
        .order_by(KnowledgeSourceVersion.version_no.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def build_version_diff(current_text: str, previous_text: str | None) -> str:
    current_lines = [line.strip() for line in current_text.replace(". ", ".\n").splitlines() if line.strip()]
    previous_lines = [line.strip() for line in (previous_text or "").replace(". ", ".\n").splitlines() if line.strip()]
    diff = difflib.unified_diff(
        previous_lines,
        current_lines,
        fromfile="anterior",
        tofile="atual",
        lineterm="",
        n=2,
    )
    return "\n".join(diff) or "Sem diferencas textuais relevantes entre as duas ultimas versoes."


async def create_evaluation_run(
    db: AsyncSession,
    tenant_id: str,
    product_id: str | None,
    created_by_user_id: str,
    evaluation_type: str,
) -> EvaluationRun:
    run = EvaluationRun(
        id=str(uuid4()),
        tenant_id=tenant_id,
        product_id=product_id,
        created_by_user_id=created_by_user_id,
        evaluation_type=evaluation_type,
        status="queued",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def get_evaluation_run_or_none(db: AsyncSession, tenant_id: str, run_id: str) -> EvaluationRun | None:
    result = await db.execute(
        select(EvaluationRun).where(EvaluationRun.tenant_id == tenant_id, EvaluationRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def get_evaluation_run_by_id(db: AsyncSession, run_id: str) -> EvaluationRun | None:
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    return result.scalar_one_or_none()


async def get_latest_evaluation_run(
    db: AsyncSession,
    tenant_id: str,
    product_id: str | None = None,
) -> EvaluationRun | None:
    query = select(EvaluationRun).where(EvaluationRun.tenant_id == tenant_id)
    if product_id:
        query = query.where(EvaluationRun.product_id == product_id)
    result = await db.execute(query.order_by(EvaluationRun.created_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def mark_evaluation_started(db: AsyncSession, run: EvaluationRun, celery_task_id: str | None = None) -> None:
    run.status = "running"
    run.started_at = utcnow_naive()
    if celery_task_id:
        run.celery_task_id = celery_task_id
    await db.commit()


async def mark_evaluation_finished(
    db: AsyncSession,
    run: EvaluationRun,
    status: str,
    summary_json: dict | None = None,
    report_markdown: str | None = None,
    error_message: str | None = None,
) -> None:
    run.status = status
    run.summary_json = summary_json
    run.report_markdown = report_markdown
    run.error_message = error_message
    run.finished_at = utcnow_naive()
    await db.commit()
