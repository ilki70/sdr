from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


class PersonaCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    tone: str = Field(min_length=2, max_length=80)
    prompt_system: str = Field(min_length=20)
    approach_rules: list[str] = Field(default_factory=list)
    stage_playbook: dict[str, str] = Field(default_factory=dict)
    objection_playbook: dict[str, str] = Field(default_factory=dict)
    publish: bool = True


class PersonaVersionCreateRequest(BaseModel):
    tone: str = Field(min_length=2, max_length=80)
    prompt_system: str = Field(min_length=20)
    approach_rules: list[str] = Field(default_factory=list)
    stage_playbook: dict[str, str] = Field(default_factory=dict)
    objection_playbook: dict[str, str] = Field(default_factory=dict)
    publish: bool = False


class PersonaResponse(OrmModel):
    id: str
    tenant_id: str
    name: str
    description: str | None
    active_version_no: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PersonaVersionResponse(OrmModel):
    id: str
    tenant_id: str
    persona_id: str
    version_no: int
    tone: str
    approach_rules_json: dict
    objection_playbook_json: dict
    prompt_system: str
    is_published: bool
    created_by_user_id: str
    created_at: datetime


class PersonaDetailResponse(BaseModel):
    persona: PersonaResponse
    versions: list[PersonaVersionResponse]
