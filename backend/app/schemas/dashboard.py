from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardRecentConversationResponse(BaseModel):
    id: str
    title: str
    status: str
    updated_at: datetime
    message_count: int
    last_message_preview: str | None = None


class DashboardRecentJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    created_at: datetime
    product_id: str


class DashboardLatestEvaluationResponse(BaseModel):
    id: str
    evaluation_type: str
    status: str
    summary_json: dict | None
    created_at: datetime


class DashboardStageMetricResponse(BaseModel):
    stage: str
    count: int


class DashboardHandoffQueueItemResponse(BaseModel):
    conversation_id: str
    title: str
    lead_id: str
    channel: str
    handoff_reason: str | None = None
    updated_at: datetime
    last_message_preview: str | None = None


class DashboardOverviewResponse(BaseModel):
    lead_count: int
    engaged_lead_count: int
    client_count: int
    product_count: int
    conversation_count: int
    qualification_started_count: int
    handoff_ready_count: int
    avg_messages_per_conversation: float
    active_rule_count: int
    active_integration_count: int
    sales_count: int
    revenue_total: Decimal
    stage_metrics: list[DashboardStageMetricResponse]
    handoff_queue: list[DashboardHandoffQueueItemResponse]
    recent_jobs: list[DashboardRecentJobResponse]
    recent_conversations: list[DashboardRecentConversationResponse]
    latest_evaluation: DashboardLatestEvaluationResponse | None
