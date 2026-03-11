"""add triggers

Revision ID: 003_triggers
Revises: 002_indexes
Create Date: 2026-03-05 00:20:00
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "003_triggers"
down_revision: Union[str, Sequence[str], None] = "002_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TRIGGER = """
CREATE TRIGGER trg_tenant_after_insert_default_rule
AFTER INSERT ON tenants
FOR EACH ROW
BEGIN
  INSERT INTO commission_rules (
    id,
    tenant_id,
    name,
    priority,
    rule_scope,
    percent_min,
    percent_max,
    condition_type,
    active_from,
    is_active,
    version_no,
    created_by_user_id,
    created_at,
    updated_at
  ) VALUES (
    UUID(),
    NEW.id,
    'Regra padrao MVP',
    100,
    'tenant',
    2.00,
    3.00,
    'hybrid',
    NOW(),
    1,
    1,
    '00000000-0000-0000-0000-000000000000',
    NOW(),
    NOW()
  );
END
"""

SALES_TRIGGER = """
CREATE TRIGGER trg_sales_after_insert_commission
AFTER INSERT ON sales
FOR EACH ROW
BEGIN
  INSERT INTO commission_calculations (
    id,
    tenant_id,
    sale_id,
    rule_id,
    applied_percent,
    commission_amount,
    calc_snapshot_json,
    calculated_at,
    created_at
  )
  SELECT
    UUID(),
    NEW.tenant_id,
    NEW.id,
    r.id,
    COALESCE(r.fixed_percent, r.percent_min, 0),
    ROUND(NEW.amount * (COALESCE(r.fixed_percent, r.percent_min, 0) / 100), 2),
    JSON_OBJECT(
      'rule_name', r.name,
      'rule_scope', r.rule_scope,
      'fixed_percent', r.fixed_percent,
      'percent_min', r.percent_min,
      'percent_max', r.percent_max
    ),
    NOW(),
    NOW()
  FROM commission_rules r
  WHERE r.tenant_id = NEW.tenant_id
    AND r.is_active = 1
    AND (r.active_to IS NULL OR r.active_to >= NOW())
  ORDER BY r.priority ASC, r.created_at DESC
  LIMIT 1;
END
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    op.execute("DROP TRIGGER IF EXISTS trg_tenant_after_insert_default_rule")
    op.execute("DROP TRIGGER IF EXISTS trg_sales_after_insert_commission")
    op.execute(TENANT_TRIGGER)
    op.execute(SALES_TRIGGER)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    op.execute("DROP TRIGGER IF EXISTS trg_sales_after_insert_commission")
    op.execute("DROP TRIGGER IF EXISTS trg_tenant_after_insert_default_rule")
