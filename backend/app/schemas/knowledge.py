from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


class KnowledgeSourceResponse(OrmModel):
    id: str
    tenant_id: str
    product_id: str
    source_type: str
    source_ref: str
    status: str
    version_no: int
    last_indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KnowledgeIngestUrlRequest(BaseModel):
    product_id: str = Field(min_length=36, max_length=36)
    source_ref: str = Field(min_length=8, max_length=500)


class KnowledgeSearchResult(BaseModel):
    source_id: str
    product_id: str
    source: str
    source_type: str
    score: float
    content: str


class KnowledgeProductRequest(BaseModel):
    product_id: str = Field(min_length=36, max_length=36)


class KnowledgeUploadResponse(BaseModel):
    source: KnowledgeSourceResponse
    asset_id: str
    storage_path: str


class KnowledgeJobResponse(OrmModel):
    id: str
    tenant_id: str
    product_id: str
    source_id: str | None
    created_by_user_id: str
    job_type: str
    status: str
    input_json: dict
    result_json: dict | None
    error_message: str | None
    celery_task_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDiffResponse(BaseModel):
    source_id: str
    current_version_no: int
    previous_version_no: int | None
    current_created_at: datetime | None
    previous_created_at: datetime | None
    diff_text: str


class EvaluationRunResponse(OrmModel):
    id: str
    tenant_id: str
    product_id: str | None
    created_by_user_id: str
    evaluation_type: str
    status: str
    summary_json: dict | None
    report_markdown: str | None
    error_message: str | None
    celery_task_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
