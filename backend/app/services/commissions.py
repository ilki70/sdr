from uuid import uuid4

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow_naive
from app.models.entities import CommissionRule
from app.schemas.commissions import CommissionRuleCreateRequest, CommissionRulePatchRequest


def _rule_select(tenant_id: str) -> Select[tuple[CommissionRule]]:
    return select(CommissionRule).where(CommissionRule.tenant_id == tenant_id, CommissionRule.deleted_at.is_(None))


async def list_rules(db: AsyncSession, tenant_id: str) -> list[CommissionRule]:
    result = await db.execute(_rule_select(tenant_id).order_by(CommissionRule.priority.asc()))
    return list(result.scalars().all())


async def create_rule(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    payload: CommissionRuleCreateRequest,
) -> CommissionRule:
    rule = CommissionRule(
        id=str(uuid4()),
        tenant_id=tenant_id,
        created_by_user_id=user_id,
        version_no=1,
        **payload.model_dump(),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def get_rule_or_none(db: AsyncSession, tenant_id: str, rule_id: str) -> CommissionRule | None:
    result = await db.execute(_rule_select(tenant_id).where(CommissionRule.id == rule_id))
    return result.scalar_one_or_none()


async def patch_rule(db: AsyncSession, rule: CommissionRule, payload: CommissionRulePatchRequest) -> CommissionRule:
    data = payload.model_dump(exclude_none=True)
    if data:
        data["version_no"] = rule.version_no + 1
    for key, value in data.items():
        setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    return rule


async def soft_delete_rule(db: AsyncSession, rule: CommissionRule) -> None:
    rule.deleted_at = utcnow_naive()
    await db.commit()
