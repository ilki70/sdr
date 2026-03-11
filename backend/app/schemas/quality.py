from datetime import datetime

from pydantic import BaseModel


class QualityReviewResponse(BaseModel):
    conversation_id: str
    title: str
    agent_id: str | None = None
    agent_name: str | None = None
    status: str
    score: int
    findings: list[str]
    reviewed_at: datetime

