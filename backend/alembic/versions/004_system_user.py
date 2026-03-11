"""ensure system user for tenant trigger

Revision ID: 004_system_user
Revises: 003_triggers
Create Date: 2026-03-06 00:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_system_user"
down_revision: Union[str, Sequence[str], None] = "003_triggers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, autoload_with=bind)
    existing = bind.execute(
        sa.select(users.c.id).where(users.c.id == "00000000-0000-0000-0000-000000000000")
    ).scalar_one_or_none()
    if existing:
        bind.execute(
            users.update()
            .where(users.c.id == "00000000-0000-0000-0000-000000000000")
            .values(email="system@agentevendedor.example.com")
        )
        return

    bind.execute(
        users.insert().values(
            id="00000000-0000-0000-0000-000000000000",
            email="system@agentevendedor.example.com",
            password_hash="$2b$12$7v8L.PQbFOfl5S.HsQGJ/eVET95Nf8ec3VBx7LxyR4hnGv.4S0m3a",
            full_name="System User",
            is_active=True,
        )
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000000'"
    )
