from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


class CommissionRuleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    priority: int = Field(default=100, ge=1, le=10000)
    rule_scope: str = Field(min_length=3, max_length=16)
    client_id: str | None = Field(default=None, min_length=36, max_length=36)
    product_id: str | None = Field(default=None, min_length=36, max_length=36)
    percent_min: Decimal | None = Field(default=None, ge=0, le=100)
    percent_max: Decimal | None = Field(default=None, ge=0, le=100)
    fixed_percent: Decimal | None = Field(default=None, ge=0, le=100)
    condition_type: str = Field(min_length=3, max_length=24)
    conditions_json: dict[str, Any] | None = None
    active_from: datetime
    active_to: datetime | None = None
    is_active: bool = True


class CommissionRulePatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    priority: int | None = Field(default=None, ge=1, le=10000)
    percent_min: Decimal | None = Field(default=None, ge=0, le=100)
    percent_max: Decimal | None = Field(default=None, ge=0, le=100)
    fixed_percent: Decimal | None = Field(default=None, ge=0, le=100)
    conditions_json: dict[str, Any] | None = None
    active_to: datetime | None = None
    is_active: bool | None = None


class CommissionRuleResponse(OrmModel):
    id: str
    tenant_id: str
    name: str
    priority: int
    rule_scope: str
    client_id: str | None
    product_id: str | None
    percent_min: Decimal | None
    percent_max: Decimal | None
    fixed_percent: Decimal | None
    condition_type: str
    conditions_json: dict[str, Any] | None
    active_from: datetime
    active_to: datetime | None
    is_active: bool
    version_no: int
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime
