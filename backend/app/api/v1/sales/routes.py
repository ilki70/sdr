from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.sales import SaleResponse
from app.services.sales import list_sales

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("", response_model=list[SaleResponse])
async def get_sales(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[SaleResponse]:
    sales = await list_sales(db, context.tenant_id)
    return [SaleResponse.model_validate(item) for item in sales]
