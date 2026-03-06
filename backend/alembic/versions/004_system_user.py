"""ensure system user for tenant trigger

Revision ID: 004_system_user
Revises: 003_triggers
Create Date: 2026-03-06 00:50:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "004_system_user"
down_revision: Union[str, Sequence[str], None] = "003_triggers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO users (id, email, password_hash, full_name, is_active, created_at, updated_at)
        VALUES (
          '00000000-0000-0000-0000-000000000000',
          'system@agentevendedor.example.com',
          '$2b$12$7v8L.PQbFOfl5S.HsQGJ/eVET95Nf8ec3VBx7LxyR4hnGv.4S0m3a',
          'System User',
          1,
          NOW(),
          NOW()
        )
        ON DUPLICATE KEY UPDATE email = VALUES(email)
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000000'"
    )
