"""agent improvement history

Revision ID: 009_agent_improvement_history
Revises: 008_lead_profile_fields
Create Date: 2026-03-24 17:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_agent_improvement_history"
down_revision: Union[str, Sequence[str], None] = "008_lead_profile_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_improvements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_run_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("findings_json", sa.JSON(), nullable=True),
        sa.Column("recommendations_json", sa.JSON(), nullable=True),
        sa.Column("sample_conversation_ids_json", sa.JSON(), nullable=True),
        sa.Column("base_agent_version_no", sa.Integer(), nullable=True),
        sa.Column("applied_agent_version_no", sa.Integer(), nullable=True),
        sa.Column("base_persona_id", sa.String(length=36), nullable=True),
        sa.Column("base_persona_version_no", sa.Integer(), nullable=True),
        sa.Column("applied_persona_version_no", sa.Integer(), nullable=True),
        sa.Column("reverted_agent_version_no", sa.Integer(), nullable=True),
        sa.Column("reverted_persona_version_no", sa.Integer(), nullable=True),
        sa.Column("reverted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reverted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["base_persona_id"], ["bot_personas.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"]),
        sa.ForeignKeyConstraint(["reverted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("agent_improvements")
