from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    JSON,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class TenantUser(Base):
    __tablename__ = "tenant_users"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    segment: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    sales_terms_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    version_no: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class ProductAsset(Base):
    __tablename__ = "product_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    storage_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class KnowledgeSource(Base, TimestampMixin):
    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    agent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("agents.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    version_no: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class KnowledgeSourceVersion(Base):
    __tablename__ = "knowledge_source_versions"
    __table_args__ = (UniqueConstraint("source_id", "version_no", name="uq_knowledge_source_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content_text: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    embedding_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class KnowledgeJob(Base, TimestampMixin):
    __tablename__ = "knowledge_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    product_id: Mapped[Optional[str]] = mapped_column(ForeignKey("products.id"), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    report_markdown: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class BotPersona(Base, TimestampMixin):
    __tablename__ = "bot_personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    active_version_no: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_agent_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    active_version_no: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version_no", name="uq_agent_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    persona_id: Mapped[Optional[str]] = mapped_column(ForeignKey("bot_personas.id"), nullable=True)
    persona_version_no: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    prompt_system: Mapped[str] = mapped_column(Text(), nullable=False)
    policy_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    tool_config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    knowledge_config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    channel_config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class PersonaVersion(Base):
    __tablename__ = "persona_versions"
    __table_args__ = (UniqueConstraint("persona_id", "version_no", name="uq_persona_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    persona_id: Mapped[str] = mapped_column(ForeignKey("bot_personas.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    tone: Mapped[str] = mapped_column(String(80), nullable=False)
    approach_rules_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    objection_playbook_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    prompt_system: Mapped[str] = mapped_column(Text(), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class ChannelIntegration(Base, TimestampMixin):
    __tablename__ = "channel_integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    agent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("agents.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    inbox_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    api_base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_secret_enc: Mapped[bytes] = mapped_column(LargeBinary(512), nullable=False)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class ChatwootWebhookEvent(Base):
    __tablename__ = "chatwoot_webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    integration_id: Mapped[str] = mapped_column(ForeignKey("channel_integrations.id"), nullable=False)
    event_uid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    process_status: Mapped[str] = mapped_column(String(24), nullable=False, default="received")
    retry_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    integration_id: Mapped[str] = mapped_column(ForeignKey("channel_integrations.id"), nullable=False)
    external_contact_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(140), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    source_channel: Mapped[str] = mapped_column(String(24), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    agent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("agents.id"), nullable=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    integration_id: Mapped[str] = mapped_column(ForeignKey("channel_integrations.id"), nullable=False)
    external_conversation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    pipeline_status: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    next_step: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    external_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    token_input: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    token_output: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    source_channel: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class CommissionRule(Base, TimestampMixin):
    __tablename__ = "commission_rules"
    __table_args__ = (UniqueConstraint("id", "tenant_id", name="uq_commission_rule"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    priority: Mapped[int] = mapped_column(Integer(), nullable=False, default=100)
    rule_scope: Mapped[str] = mapped_column(String(16), nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(ForeignKey("clients.id"), nullable=True)
    product_id: Mapped[Optional[str]] = mapped_column(ForeignKey("products.id"), nullable=True)
    percent_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    percent_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    fixed_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    condition_type: Mapped[str] = mapped_column(String(24), nullable=False)
    conditions_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    active_from: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    active_to: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    version_no: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


class CommissionCalculation(Base):
    __tablename__ = "commission_calculations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    sale_id: Mapped[str] = mapped_column(ForeignKey("sales.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(ForeignKey("commission_rules.id"), nullable=False)
    applied_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    calc_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    before_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    metric_date: Mapped[date] = mapped_column(Date(), nullable=False)
    granularity: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(ForeignKey("clients.id"), nullable=True)
    product_id: Mapped[Optional[str]] = mapped_column(ForeignKey("products.id"), nullable=True)
    leads_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    responses_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    conversions_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    closed_sales_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    revenue_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    avg_close_time_seconds: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
