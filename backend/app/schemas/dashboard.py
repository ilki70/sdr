from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardRecentConversationResponse(BaseModel):
    id: str
    agent_id: str | None = None
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


class DashboardAgentMetricResponse(BaseModel):
    agent_id: str
    name: str
    slug: str
    conversation_count: int
    open_conversation_count: int
    integration_count: int
    last_activity_at: datetime | None = None


class DashboardOverviewResponse(BaseModel):
    client_count: int
    product_count: int
    conversation_count: int
    active_rule_count: int
    active_integration_count: int
    sales_count: int
    revenue_total: Decimal
    recent_jobs: list[DashboardRecentJobResponse]
    recent_conversations: list[DashboardRecentConversationResponse]
    agent_metrics: list[DashboardAgentMetricResponse]
    latest_evaluation: DashboardLatestEvaluationResponse | None
