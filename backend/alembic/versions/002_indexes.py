"""add indexes

Revision ID: 002_indexes
Revises: 001_init_schema
Create Date: 2026-03-05 00:10:00
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "002_indexes"
down_revision: Union[str, Sequence[str], None] = "001_init_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_leads_tenant_channel_created", "leads", ["tenant_id", "source_channel", "created_at"])
    op.create_index("idx_conversations_tenant_ext", "conversations", ["tenant_id", "external_conversation_id"])
    op.create_index("idx_messages_tenant_conv_sent", "messages", ["tenant_id", "conversation_id", "sent_at"])
    op.create_index("idx_sales_tenant_closed_status", "sales", ["tenant_id", "closed_at", "status"])
    op.create_index(
        "idx_commission_rules_active_window",
        "commission_rules",
        ["tenant_id", "is_active", "active_from", "active_to", "priority"],
    )
    op.create_index(
        "idx_metric_snapshots_filters",
        "metric_snapshots",
        ["tenant_id", "metric_date", "granularity", "channel", "client_id", "product_id"],
    )
    op.create_index("idx_products_tenant_name", "products", ["tenant_id", "name"])
    op.create_index("idx_knowledge_sources_tenant_type_status", "knowledge_sources", ["tenant_id", "source_type", "status"])
    op.execute("CREATE FULLTEXT INDEX ftx_knowledge_chunks_content ON knowledge_chunks (content)")


def downgrade() -> None:
    op.execute("DROP INDEX ftx_knowledge_chunks_content ON knowledge_chunks")
    op.drop_index("idx_knowledge_sources_tenant_type_status", table_name="knowledge_sources")
    op.drop_index("idx_products_tenant_name", table_name="products")
    op.drop_index("idx_metric_snapshots_filters", table_name="metric_snapshots")
    op.drop_index("idx_commission_rules_active_window", table_name="commission_rules")
    op.drop_index("idx_sales_tenant_closed_status", table_name="sales")
    op.drop_index("idx_messages_tenant_conv_sent", table_name="messages")
    op.drop_index("idx_conversations_tenant_ext", table_name="conversations")
    op.drop_index("idx_leads_tenant_channel_created", table_name="leads")
