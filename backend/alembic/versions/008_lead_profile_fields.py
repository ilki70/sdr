"""lead profile fields

Revision ID: 008_lead_profile_fields
Revises: 007_conversation_pipeline_fields
Create Date: 2026-03-24 16:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_lead_profile_fields"
down_revision: Union[str, Sequence[str], None] = "007_conversation_pipeline_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("cpf", sa.String(length=14), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "cpf")
