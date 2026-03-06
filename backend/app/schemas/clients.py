from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import OrmModel


class ClientCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    segment: str | None = Field(default=None, max_length=60)
    website_url: HttpUrl | None = None
    status: str = Field(default="active", max_length=24)


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    segment: str | None = Field(default=None, max_length=60)
    website_url: HttpUrl | None = None
    status: str | None = Field(default=None, max_length=24)


class ClientResponse(OrmModel):
    id: str
    tenant_id: str
    name: str
    segment: str | None
    website_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime
