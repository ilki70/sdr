from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.agents import AgentResponse
from app.schemas.common import OrmModel
from app.schemas.personas import PersonaResponse
from app.schemas.knowledge import EvaluationRunResponse

TrainingFocus = Literal["first_attendance", "qualification", "objection_handling", "closing", "follow_up"]


class AgentTrainingRequest(BaseModel):
    cycles: int = Field(default=1, ge=1, le=5)
    interactions_per_cycle: int = Field(default=4, ge=1, le=10)
    focus: TrainingFocus = "first_attendance"
    auto_apply: bool = False


class TrainingCycleResponse(BaseModel):
    cycle_no: int
    average_score: float
    total_turns: int
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)
    applied_persona_version_no: int | None = None
    applied_agent_version_no: int | None = None


class AgentTrainingResponse(BaseModel):
    evaluation_run: EvaluationRunResponse
    agent: AgentResponse
    persona: PersonaResponse | None = None
    cycles: list[TrainingCycleResponse] = Field(default_factory=list)
    summary_json: dict[str, Any] = Field(default_factory=dict)
    report_markdown: str
