from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


class IntegrationCreateRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=24)
    inbox_ref: str = Field(min_length=2, max_length=128)
    api_base_url: str = Field(min_length=8, max_length=255)
    webhook_secret: str = Field(min_length=4, max_length=255)
    config_json: dict[str, Any] | None = None
    status: str = Field(default="active", min_length=2, max_length=24)


class IntegrationUpdateRequest(BaseModel):
    inbox_ref: str | None = Field(default=None, min_length=2, max_length=128)
    api_base_url: str | None = Field(default=None, min_length=8, max_length=255)
    webhook_secret: str | None = Field(default=None, min_length=4, max_length=255)
    config_json: dict[str, Any] | None = None
    status: str | None = Field(default=None, min_length=2, max_length=24)


class IntegrationResponse(OrmModel):
    id: str
    tenant_id: str
    provider: str
    inbox_ref: str
    api_base_url: str
    config_json: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime
