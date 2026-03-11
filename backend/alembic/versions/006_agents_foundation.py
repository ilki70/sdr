"""agents foundation

Revision ID: 006_agents_foundation
Revises: 005_knowledge_jobs_and_versions
Create Date: 2026-03-11 18:30:00
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "006_agents_foundation"
down_revision: Union[str, Sequence[str], None] = "005_knowledge_jobs_and_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active_version_no", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_agent_slug"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_agents_tenant"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_agents_created_by"),
    )

    op.create_table(
        "agent_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=True),
        sa.Column("persona_version_no", sa.Integer(), nullable=True),
        sa.Column("prompt_system", sa.Text(), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("tool_config_json", sa.JSON(), nullable=False),
        sa.Column("knowledge_config_json", sa.JSON(), nullable=False),
        sa.Column("channel_config_json", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("agent_id", "version_no", name="uq_agent_version"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_av_tenant"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], name="fk_av_agent"),
        sa.ForeignKeyConstraint(["persona_id"], ["bot_personas.id"], name="fk_av_persona"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_av_created_by"),
    )

    op.add_column("knowledge_sources", sa.Column("agent_id", sa.String(length=36), nullable=True))
    op.add_column("channel_integrations", sa.Column("agent_id", sa.String(length=36), nullable=True))
    op.add_column("conversations", sa.Column("agent_id", sa.String(length=36), nullable=True))

    op.create_foreign_key("fk_ks_agent", "knowledge_sources", "agents", ["agent_id"], ["id"])
    op.create_foreign_key("fk_ci_agent", "channel_integrations", "agents", ["agent_id"], ["id"])
    op.create_foreign_key("fk_conv_agent", "conversations", "agents", ["agent_id"], ["id"])

    bind = op.get_bind()
    metadata = sa.MetaData()
    tenants = sa.Table("tenants", metadata, autoload_with=bind)
    tenant_users = sa.Table("tenant_users", metadata, autoload_with=bind)
    bot_personas = sa.Table("bot_personas", metadata, autoload_with=bind)
    agents = sa.Table("agents", metadata, autoload_with=bind)
    agent_versions = sa.Table("agent_versions", metadata, autoload_with=bind)
    channel_integrations = sa.Table("channel_integrations", metadata, autoload_with=bind)
    conversations = sa.Table("conversations", metadata, autoload_with=bind)

    tenant_rows = bind.execute(sa.select(tenants.c.id)).fetchall()
    for tenant_row in tenant_rows:
        tenant_id = str(tenant_row.id)

        creator_id = bind.execute(
            sa.select(tenant_users.c.user_id).where(tenant_users.c.tenant_id == tenant_id).limit(1)
        ).scalar_one_or_none()
        creator_id = str(creator_id or SYSTEM_USER_ID)

        persona_row = bind.execute(
            sa.select(
                bot_personas.c.id,
                bot_personas.c.active_version_no,
                bot_personas.c.name,
                bot_personas.c.description,
            )
            .where(
                bot_personas.c.tenant_id == tenant_id,
                bot_personas.c.deleted_at.is_(None),
                bot_personas.c.is_active == sa.true(),
            )
            .order_by(bot_personas.c.created_at.asc())
            .limit(1)
        ).mappings().first()

        agent_id = str(uuid4())
        agent_name = str(persona_row["name"]) if persona_row and persona_row["name"] else "Vinac Consorcios"
        description = (
            str(persona_row["description"])
            if persona_row and persona_row["description"]
            else "Agente inicial migrado do tenant existente."
        )

        bind.execute(
            agents.insert().values(
                id=agent_id,
                tenant_id=tenant_id,
                name=agent_name,
                slug="vinac-consorcios",
                description=description,
                active_version_no=1,
                status="active",
                created_by_user_id=creator_id,
            )
        )

        bind.execute(
            agent_versions.insert().values(
                id=str(uuid4()),
                tenant_id=tenant_id,
                agent_id=agent_id,
                version_no=1,
                persona_id=str(persona_row["id"]) if persona_row else None,
                persona_version_no=int(persona_row["active_version_no"]) if persona_row and persona_row["active_version_no"] else None,
                prompt_system=(
                    "Voce e o agente comercial inicial deste tenant. "
                    "Atenda com tom consultivo, sustentado por contexto oficial e orientado a proximo passo."
                ),
                policy_json={"rules": ["use contexto oficial", "nao invente fatos", "sempre proponha proximo passo"]},
                tool_config_json={"rag_enabled": True, "web_allowlist_enabled": True},
                knowledge_config_json={"scope": "tenant_default"},
                channel_config_json={"default_channel": "lab"},
                is_published=True,
                created_by_user_id=creator_id,
            )
        )

        bind.execute(
            channel_integrations.update()
            .where(channel_integrations.c.tenant_id == tenant_id, channel_integrations.c.agent_id.is_(None))
            .values(agent_id=agent_id)
        )
        bind.execute(
            conversations.update()
            .where(conversations.c.tenant_id == tenant_id, conversations.c.agent_id.is_(None))
            .values(agent_id=agent_id)
        )


def downgrade() -> None:
    op.drop_constraint("fk_conv_agent", "conversations", type_="foreignkey")
    op.drop_constraint("fk_ci_agent", "channel_integrations", type_="foreignkey")
    op.drop_constraint("fk_ks_agent", "knowledge_sources", type_="foreignkey")

    op.drop_column("conversations", "agent_id")
    op.drop_column("channel_integrations", "agent_id")
    op.drop_column("knowledge_sources", "agent_id")

    op.drop_table("agent_versions")
    op.drop_table("agents")
