from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.quality import QualityReviewResponse
from app.services.quality import list_quality_reviews

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/reviews", response_model=list[QualityReviewResponse])
async def get_quality_reviews(
    limit: int = Query(default=10, ge=1, le=50),
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[QualityReviewResponse]:
    return await list_quality_reviews(db, context.tenant_id, limit=limit)

