"""conversation pipeline fields

Revision ID: 007_conversation_pipeline_fields
Revises: 006_agents_foundation
Create Date: 2026-03-20 21:25:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_conversation_pipeline_fields"
down_revision: Union[str, Sequence[str], None] = "006_agents_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("pipeline_status", sa.String(length=24), nullable=True))
    op.add_column("conversations", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("next_step", sa.Text(), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE conversations
            SET pipeline_status = CASE
                WHEN status IN ('waiting_human', 'handoff') THEN 'handoff'
                WHEN status = 'closed' THEN 'disqualified'
                ELSE 'qualifying'
            END
            WHERE pipeline_status IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("conversations", "next_step")
    op.drop_column("conversations", "summary")
    op.drop_column("conversations", "pipeline_status")
