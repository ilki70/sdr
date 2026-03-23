from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.entities import Client, Product
from app.services.knowledge_ops import (
    get_evaluation_run_by_id,
    mark_evaluation_finished,
    mark_evaluation_started,
)
from app.services.segment_lab import run_segment_lab, summarize_segment_results
from app.services.vinac_lab import build_vinac_report, run_vinac_lab, summarize_vinac_results, write_vinac_report
from app.workers.celery_app import celery_app


async def _run_evaluation(run_id: str, task_id: str | None) -> dict[str, Any]:
    async with SessionLocal() as session:
        run = await get_evaluation_run_by_id(session, run_id)
        if not run:
            raise ValueError(f"evaluation_run_not_found:{run_id}")
        await mark_evaluation_started(session, run, celery_task_id=task_id)
        tenant_id = run.tenant_id
        product_id = run.product_id

    async with SessionLocal() as session:
        run = await get_evaluation_run_by_id(session, run_id)
        assert run is not None
        try:
            if run.evaluation_type == "vinac_sales_lab":
                results = await run_vinac_lab(tenant_id)
                report_markdown = build_vinac_report(results)
                summary_json = summarize_vinac_results(results)
            elif run.evaluation_type.startswith("segment_"):
                if not product_id:
                    raise ValueError("segment_evaluation_requires_product")
                segment_result = await session.execute(
                    select(Client.segment)
                    .join(Product, Product.client_id == Client.id)
                    .where(Product.id == product_id, Product.tenant_id == tenant_id)
                )
                segment = segment_result.scalar_one_or_none()
                if not segment:
                    raise ValueError("segment_not_found_for_product")
                results, report_markdown = await run_segment_lab(tenant_id, segment)
                summary_json = summarize_segment_results(results, segment)
            else:
                raise ValueError(f"unsupported_evaluation_type:{run.evaluation_type}")
            report_path = write_vinac_report(report_markdown)
            summary_json["report_path"] = report_path
            await mark_evaluation_finished(
                session,
                run,
                status="completed",
                summary_json=summary_json,
                report_markdown=report_markdown,
            )
            return summary_json
        except Exception as exc:
            await mark_evaluation_finished(session, run, status="failed", error_message=str(exc))
            raise


async def run_evaluation_async(run_id: str, task_id: str | None = None) -> dict[str, Any]:
    return await _run_evaluation(run_id, task_id)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 1, "countdown": 5})
def run_evaluation_job(self, run_id: str) -> dict[str, Any]:
    return asyncio.run(run_evaluation_async(run_id, self.request.id))
