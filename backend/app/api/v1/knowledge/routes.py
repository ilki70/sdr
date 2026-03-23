from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.knowledge import (
    EvaluationRunResponse,
    KnowledgeDiffResponse,
    KnowledgeIngestUrlRequest,
    KnowledgeJobResponse,
    KnowledgeProductRequest,
    KnowledgeSearchResult,
    KnowledgeSourceResponse,
    KnowledgeUploadResponse,
)
from app.services.knowledge import (
    get_knowledge_source_or_none,
    ingest_knowledge_source,
    list_knowledge_sources,
    reingest_knowledge_source,
)
from app.services.knowledge_ops import (
    build_version_diff,
    create_evaluation_run,
    create_knowledge_job,
    get_evaluation_run_or_none,
    get_latest_evaluation_run,
    get_knowledge_job_or_none,
    list_knowledge_jobs,
    list_source_versions,
)
from app.services.products import create_product_asset, get_product_or_none
from app.services.uploads import persist_upload
from app.services.vector_store import search_rag_context
from app.workers.tasks.evaluation import run_evaluation_async, run_evaluation_job
from app.workers.tasks.ingestion import ingest_knowledge_job, run_knowledge_job_async

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _track_background_task(task: asyncio.Task[object], label: str) -> None:
    def _log_result(finished_task: asyncio.Task[object]) -> None:
        try:
            finished_task.result()
        except Exception:
            logger.exception("background_%s_failed", label)

    task.add_done_callback(_log_result)


def _enqueue_knowledge_job(job_id: str) -> None:
    if settings.redis_url and not settings.celery_task_always_eager:
        ingest_knowledge_job.delay(job_id)
        return
    _track_background_task(asyncio.create_task(run_knowledge_job_async(job_id)), "knowledge_job")


def _enqueue_evaluation_job(run_id: str) -> None:
    if settings.redis_url and not settings.celery_task_always_eager:
        run_evaluation_job.delay(run_id)
        return
    _track_background_task(asyncio.create_task(run_evaluation_async(run_id)), "evaluation_job")


@router.get("/sources", response_model=list[KnowledgeSourceResponse])
async def get_sources(
    product_id: str | None = Query(default=None),
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeSourceResponse]:
    sources = await list_knowledge_sources(db, context.tenant_id, product_id=product_id)
    return [KnowledgeSourceResponse.model_validate(item) for item in sources]


@router.get("/sources/{source_id}/diff", response_model=KnowledgeDiffResponse)
async def get_source_diff(
    source_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeDiffResponse:
    source = await get_knowledge_source_or_none(db, context.tenant_id, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge source not found")

    versions = await list_source_versions(db, context.tenant_id, source_id, limit=2)
    current = versions[0] if versions else None
    previous = versions[1] if len(versions) > 1 else None
    diff_text = build_version_diff(current.content_text if current else "", previous.content_text if previous else None)
    return KnowledgeDiffResponse(
        source_id=source_id,
        current_version_no=current.version_no if current else source.version_no,
        previous_version_no=previous.version_no if previous else None,
        current_created_at=current.created_at if current else None,
        previous_created_at=previous.created_at if previous else None,
        diff_text=diff_text,
    )


@router.get("/jobs", response_model=list[KnowledgeJobResponse])
async def get_jobs(
    product_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeJobResponse]:
    jobs = await list_knowledge_jobs(db, context.tenant_id, product_id=product_id, limit=limit)
    return [KnowledgeJobResponse.model_validate(job) for job in jobs]


@router.post("/jobs/url", response_model=KnowledgeJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_url_ingestion(
    payload: KnowledgeIngestUrlRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeJobResponse:
    product = await get_product_or_none(db, context.tenant_id, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product for tenant")
    job = await create_knowledge_job(
        db,
        tenant_id=context.tenant_id,
        product_id=payload.product_id,
        created_by_user_id=context.user_id,
        job_type="ingest_url",
        input_json={"source_ref": payload.source_ref},
    )
    _enqueue_knowledge_job(job.id)
    refreshed = await get_knowledge_job_or_none(db, context.tenant_id, job.id)
    assert refreshed is not None
    return KnowledgeJobResponse.model_validate(refreshed)


@router.post("/jobs/upload", response_model=KnowledgeUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_upload_ingestion(
    product_id: str = Form(...),
    file: UploadFile = File(...),
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeUploadResponse:
    product = await get_product_or_none(db, context.tenant_id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product for tenant")

    path, checksum, size, _mime = await persist_upload(file)
    asset = await create_product_asset(
        db=db,
        tenant_id=context.tenant_id,
        product_id=product_id,
        created_by_user_id=context.user_id,
        title=file.filename or "documento",
        storage_path=path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        checksum_sha256=checksum,
    )
    job = await create_knowledge_job(
        db,
        tenant_id=context.tenant_id,
        product_id=product_id,
        created_by_user_id=context.user_id,
        job_type="ingest_file",
        input_json={"source_ref": path, "asset_id": asset.id},
    )
    _enqueue_knowledge_job(job.id)
    return KnowledgeUploadResponse(
        source=KnowledgeSourceResponse(
            id="pending",
            tenant_id=context.tenant_id,
            product_id=product_id,
            source_type="pending_upload",
            source_ref=path,
            status="queued",
            version_no=0,
            last_indexed_at=None,
            created_at=job.created_at,
            updated_at=job.updated_at,
        ),
        asset_id=asset.id,
        storage_path=path,
    )


@router.post("/jobs/vinac", response_model=KnowledgeJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_vinac_ingestion(
    payload: KnowledgeProductRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeJobResponse:
    product = await get_product_or_none(db, context.tenant_id, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product for tenant")
    job = await create_knowledge_job(
        db,
        tenant_id=context.tenant_id,
        product_id=payload.product_id,
        created_by_user_id=context.user_id,
        job_type="ingest_vinac_official",
        input_json={"seed": "vinac_official"},
    )
    _enqueue_knowledge_job(job.id)
    refreshed = await get_knowledge_job_or_none(db, context.tenant_id, job.id)
    assert refreshed is not None
    return KnowledgeJobResponse.model_validate(refreshed)


@router.post("/sources/{source_id}/reingest", response_model=KnowledgeJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_reingest_source(
    source_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeJobResponse:
    source = await get_knowledge_source_or_none(db, context.tenant_id, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge source not found")
    if source.source_ref.startswith("manual://") or source.source_ref.startswith("vinac://"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Manual sources do not support reingestion")
    job = await create_knowledge_job(
        db,
        tenant_id=context.tenant_id,
        product_id=source.product_id,
        created_by_user_id=context.user_id,
        job_type="reingest_source",
        input_json={"source_id": source.id, "source_ref": source.source_ref},
        source_id=source.id,
    )
    _enqueue_knowledge_job(job.id)
    refreshed = await get_knowledge_job_or_none(db, context.tenant_id, job.id)
    assert refreshed is not None
    return KnowledgeJobResponse.model_validate(refreshed)


@router.get("/search", response_model=list[KnowledgeSearchResult])
async def get_search_results(
    q: str = Query(min_length=2),
    product_id: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=10),
    context: RequestContext = Depends(get_request_context),
) -> list[KnowledgeSearchResult]:
    items = await search_rag_context(context.tenant_id, q, limit=limit, product_id=product_id)
    return [KnowledgeSearchResult.model_validate(item) for item in items]


@router.post("/sources/url", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def post_url_source(
    payload: KnowledgeIngestUrlRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeSourceResponse:
    product = await get_product_or_none(db, context.tenant_id, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product for tenant")
    source = await ingest_knowledge_source(db, context.tenant_id, payload.product_id, payload.source_ref)
    return KnowledgeSourceResponse.model_validate(source)


@router.post("/sources/upload", response_model=KnowledgeUploadResponse, status_code=status.HTTP_201_CREATED)
async def post_upload_source(
    product_id: str = Form(...),
    file: UploadFile = File(...),
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeUploadResponse:
    product = await get_product_or_none(db, context.tenant_id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product for tenant")

    path, checksum, size, _mime = await persist_upload(file)
    asset = await create_product_asset(
        db=db,
        tenant_id=context.tenant_id,
        product_id=product_id,
        created_by_user_id=context.user_id,
        title=file.filename or "documento",
        storage_path=path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        checksum_sha256=checksum,
    )
    source = await ingest_knowledge_source(db, context.tenant_id, product_id, path)
    return KnowledgeUploadResponse(
        source=KnowledgeSourceResponse.model_validate(source),
        asset_id=asset.id,
        storage_path=path,
    )


@router.post("/evaluations/vinac", response_model=EvaluationRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_vinac_evaluation(
    payload: KnowledgeProductRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> EvaluationRunResponse:
    product = await get_product_or_none(db, context.tenant_id, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product for tenant")
    run = await create_evaluation_run(
        db,
        tenant_id=context.tenant_id,
        product_id=payload.product_id,
        created_by_user_id=context.user_id,
        evaluation_type="vinac_sales_lab",
    )
    _enqueue_evaluation_job(run.id)
    refreshed = await get_evaluation_run_or_none(db, context.tenant_id, run.id)
    assert refreshed is not None
    return EvaluationRunResponse.model_validate(refreshed)


@router.post("/evaluations/segment", response_model=EvaluationRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_segment_evaluation(
    payload: KnowledgeProductRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> EvaluationRunResponse:
    product = await get_product_or_none(db, context.tenant_id, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product for tenant")
    run = await create_evaluation_run(
        db,
        tenant_id=context.tenant_id,
        product_id=payload.product_id,
        created_by_user_id=context.user_id,
        evaluation_type="segment_consorcio_de_veiculos",
    )
    _enqueue_evaluation_job(run.id)
    refreshed = await get_evaluation_run_or_none(db, context.tenant_id, run.id)
    assert refreshed is not None
    return EvaluationRunResponse.model_validate(refreshed)


@router.get("/evaluations/latest", response_model=EvaluationRunResponse | None)
async def get_latest_evaluation(
    product_id: str | None = Query(default=None),
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> EvaluationRunResponse | None:
    run = await get_latest_evaluation_run(db, context.tenant_id, product_id=product_id)
    if not run:
        return None
    return EvaluationRunResponse.model_validate(run)
