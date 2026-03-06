from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.schemas.commissions import CommissionRuleCreateRequest, CommissionRulePatchRequest, CommissionRuleResponse
from app.services.clients import get_client_or_none
from app.services.commissions import create_rule, get_rule_or_none, list_rules, patch_rule
from app.services.products import get_product_or_none

router = APIRouter(prefix="/commissions", tags=["commissions"])


@router.get("/rules", response_model=list[CommissionRuleResponse])
async def get_rules(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[CommissionRuleResponse]:
    rules = await list_rules(db, context.tenant_id)
    return [CommissionRuleResponse.model_validate(item) for item in rules]


@router.post("/rules", response_model=CommissionRuleResponse, status_code=status.HTTP_201_CREATED)
async def post_rule(
    payload: CommissionRuleCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> CommissionRuleResponse:
    if payload.client_id and not await get_client_or_none(db, context.tenant_id, payload.client_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id for tenant")
    if payload.product_id and not await get_product_or_none(db, context.tenant_id, payload.product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product_id for tenant")
    rule = await create_rule(db, context.tenant_id, context.user_id, payload)
    return CommissionRuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=CommissionRuleResponse)
async def patch_rule_handler(
    rule_id: str,
    payload: CommissionRulePatchRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> CommissionRuleResponse:
    rule = await get_rule_or_none(db, context.tenant_id, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    updated = await patch_rule(db, rule, payload)
    return CommissionRuleResponse.model_validate(updated)
