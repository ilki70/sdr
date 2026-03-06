from datetime import datetime
from decimal import Decimal

from app.schemas.common import OrmModel


class SaleResponse(OrmModel):
    id: str
    tenant_id: str
    lead_id: str
    product_id: str
    conversation_id: str | None
    status: str
    amount: Decimal
    currency: str
    closed_at: datetime | None
    source_channel: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
