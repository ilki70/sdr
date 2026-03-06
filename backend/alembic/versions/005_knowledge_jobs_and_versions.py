"""knowledge versions jobs and evaluation runs

Revision ID: 005_knowledge_jobs_and_versions
Revises: 004_system_user
Create Date: 2026-03-06 03:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_knowledge_jobs_and_versions"
down_revision: Union[str, Sequence[str], None] = "004_system_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_source_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=True),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("source_id", "version_no", name="uq_knowledge_source_version"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_ksv_tenant"),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], name="fk_ksv_source"),
    )

    op.create_table(
        "knowledge_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_kj_tenant"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_kj_product"),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], name="fk_kj_source"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_kj_created_by"),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("report_markdown", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_er_tenant"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_er_product"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_er_created_by"),
    )

    op.create_index("ix_ksv_source_created", "knowledge_source_versions", ["source_id", "created_at"])
    op.create_index("ix_kj_tenant_product_created", "knowledge_jobs", ["tenant_id", "product_id", "created_at"])
    op.create_index("ix_kj_status", "knowledge_jobs", ["status"])
    op.create_index("ix_er_tenant_product_created", "evaluation_runs", ["tenant_id", "product_id", "created_at"])
    op.create_index("ix_er_status", "evaluation_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_er_status", table_name="evaluation_runs")
    op.drop_index("ix_er_tenant_product_created", table_name="evaluation_runs")
    op.drop_index("ix_kj_status", table_name="knowledge_jobs")
    op.drop_index("ix_kj_tenant_product_created", table_name="knowledge_jobs")
    op.drop_index("ix_ksv_source_created", table_name="knowledge_source_versions")
    op.drop_table("evaluation_runs")
    op.drop_table("knowledge_jobs")
    op.drop_table("knowledge_source_versions")
