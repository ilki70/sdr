from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


class ProductCreateRequest(BaseModel):
    client_id: str = Field(min_length=36, max_length=36)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    base_price: Decimal | None = None
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    sales_terms_json: dict[str, Any] | None = None
    is_active: bool = True


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    base_price: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    sales_terms_json: dict[str, Any] | None = None
    is_active: bool | None = None


class ProductResponse(OrmModel):
    id: str
    tenant_id: str
    client_id: str
    name: str
    description: str | None
    base_price: Decimal | None
    currency: str
    sales_terms_json: dict[str, Any] | None
    is_active: bool
    version_no: int
    created_at: datetime
    updated_at: datetime


class ProductAssetResponse(BaseModel):
    id: str
    product_id: str
    storage_path: str
    checksum_sha256: str
    size_bytes: int
