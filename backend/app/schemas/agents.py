from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    slug: str = Field(min_length=2, max_length=140)
    description: str | None = None
    persona_id: str | None = Field(default=None, max_length=36)
    persona_version_no: int | None = None
    prompt_system: str = Field(min_length=20)
    policy_json: dict[str, Any] = Field(default_factory=dict)
    tool_config_json: dict[str, Any] = Field(default_factory=dict)
    knowledge_config_json: dict[str, Any] = Field(default_factory=dict)
    channel_config_json: dict[str, Any] = Field(default_factory=dict)
    publish: bool = True


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    slug: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = None
    status: str | None = Field(default=None, min_length=2, max_length=24)


class AgentVersionCreateRequest(BaseModel):
    persona_id: str | None = Field(default=None, max_length=36)
    persona_version_no: int | None = None
    prompt_system: str = Field(min_length=20)
    policy_json: dict[str, Any] = Field(default_factory=dict)
    tool_config_json: dict[str, Any] = Field(default_factory=dict)
    knowledge_config_json: dict[str, Any] = Field(default_factory=dict)
    channel_config_json: dict[str, Any] = Field(default_factory=dict)
    publish: bool = False


class AgentResponse(OrmModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    active_version_no: int | None
    status: str
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class AgentVersionResponse(OrmModel):
    id: str
    tenant_id: str
    agent_id: str
    version_no: int
    persona_id: str | None
    persona_version_no: int | None
    prompt_system: str
    policy_json: dict[str, Any]
    tool_config_json: dict[str, Any]
    knowledge_config_json: dict[str, Any]
    channel_config_json: dict[str, Any]
    is_published: bool
    created_by_user_id: str
    created_at: datetime


class AgentDetailResponse(BaseModel):
    agent: AgentResponse
    versions: list[AgentVersionResponse]
