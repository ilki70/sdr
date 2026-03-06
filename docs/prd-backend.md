# PRD Backend - Agente Vendedor IA

## 1) Resumo do produto
- Produto: plataforma B2B para terceirizacao de vendas com agentes conversacionais de IA.
- Objetivo: conduzir lead no funil ate fechamento, com operacao principal via Chatwoot (webhooks).
- Pitch: "Terceirize seu time de vendas. Contrate o maior vendedor do mundo!"
- Modelo comercial: comissao por desempenho (MVP 2% a 3%), configuravel por painel.

## 2) Requisitos funcionais (backend)
- Auth/session: backend confia em sessao validada no proxy Next.js (iron-session) e valida `X-User-Id` + `X-Tenant-Id`.
- Core:
- cadastro de clientes, produtos e ativos de conhecimento.
- ingestao RAG de documentos/URLs/YouTube.
- busca web restrita por allowlist de dominios do cliente.
- persona versionada para bot vendedor.
- entrada/saida de mensagens via webhooks Chatwoot.
- retries idempotentes para eventos de webhook.
- Metrics:
- dashboard de metricas (funil operacional fica no Chatwoot).
- Billing:
- regras de comissao configuraveis por tenant/cliente/produto.
- calculo automatico de comissao por venda.

## 3) Database schema (MySQL 8)

### 3.1 DDL principal
```sql
CREATE TABLE users (
  id CHAR(36) PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE tenants (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  slug VARCHAR(120) NOT NULL UNIQUE,
  status VARCHAR(24) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL
);

CREATE TABLE tenant_users (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  user_id CHAR(36) NOT NULL,
  role VARCHAR(16) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_tenant_user (tenant_id, user_id),
  CONSTRAINT fk_tu_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_tu_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE clients (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  name VARCHAR(140) NOT NULL,
  segment VARCHAR(60) NULL,
  website_url VARCHAR(255) NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_clients_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE TABLE products (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  client_id CHAR(36) NOT NULL,
  name VARCHAR(160) NOT NULL,
  description TEXT NULL,
  base_price DECIMAL(12,2) NULL,
  currency CHAR(3) NOT NULL DEFAULT 'BRL',
  sales_terms_json JSON NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  version_no INT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_products_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_products_client FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE product_assets (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  product_id CHAR(36) NOT NULL,
  asset_type VARCHAR(16) NOT NULL,
  title VARCHAR(180) NOT NULL,
  storage_path VARCHAR(255) NULL,
  source_url VARCHAR(500) NULL,
  mime_type VARCHAR(80) NULL,
  size_bytes BIGINT NULL,
  checksum_sha256 VARCHAR(64) NULL,
  created_by_user_id CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_pa_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_pa_product FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE knowledge_sources (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  product_id CHAR(36) NOT NULL,
  source_type VARCHAR(16) NOT NULL,
  source_ref VARCHAR(500) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  version_no INT NOT NULL DEFAULT 1,
  last_indexed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_ks_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_ks_product FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE knowledge_chunks (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  source_id CHAR(36) NOT NULL,
  chunk_index INT NOT NULL,
  content LONGTEXT NOT NULL,
  embedding_ref VARCHAR(128) NOT NULL,
  token_count INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_kc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_kc_source FOREIGN KEY (source_id) REFERENCES knowledge_sources(id)
);

CREATE TABLE bot_personas (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  name VARCHAR(120) NOT NULL,
  description TEXT NULL,
  active_version_no INT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_bp_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE TABLE persona_versions (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  persona_id CHAR(36) NOT NULL,
  version_no INT NOT NULL,
  tone VARCHAR(80) NOT NULL,
  approach_rules_json JSON NOT NULL,
  objection_playbook_json JSON NOT NULL,
  prompt_system LONGTEXT NOT NULL,
  is_published TINYINT(1) NOT NULL DEFAULT 0,
  created_by_user_id CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_persona_version (persona_id, version_no),
  CONSTRAINT fk_pv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_pv_persona FOREIGN KEY (persona_id) REFERENCES bot_personas(id)
);

CREATE TABLE channel_integrations (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  provider VARCHAR(24) NOT NULL,
  inbox_ref VARCHAR(128) NOT NULL,
  api_base_url VARCHAR(255) NOT NULL,
  webhook_secret_enc VARBINARY(512) NOT NULL,
  config_json JSON NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_ci_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE TABLE chatwoot_webhook_events (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  integration_id CHAR(36) NOT NULL,
  event_uid VARCHAR(128) NOT NULL UNIQUE,
  event_type VARCHAR(64) NOT NULL,
  payload_json JSON NOT NULL,
  received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME NULL,
  process_status VARCHAR(24) NOT NULL DEFAULT 'received',
  retry_count INT NOT NULL DEFAULT 0,
  last_error VARCHAR(255) NULL,
  CONSTRAINT fk_cwe_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_cwe_integration FOREIGN KEY (integration_id) REFERENCES channel_integrations(id)
);

CREATE TABLE leads (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  integration_id CHAR(36) NOT NULL,
  external_contact_id VARCHAR(128) NULL,
  name VARCHAR(140) NULL,
  email VARCHAR(255) NULL,
  phone VARCHAR(40) NULL,
  source_channel VARCHAR(24) NOT NULL,
  lifecycle_status VARCHAR(32) NOT NULL DEFAULT 'new',
  first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME NULL,
  metadata_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_leads_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_leads_integration FOREIGN KEY (integration_id) REFERENCES channel_integrations(id)
);

CREATE TABLE conversations (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  lead_id CHAR(36) NOT NULL,
  integration_id CHAR(36) NOT NULL,
  external_conversation_id VARCHAR(128) NULL,
  channel VARCHAR(24) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'open',
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_conv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_conv_lead FOREIGN KEY (lead_id) REFERENCES leads(id),
  CONSTRAINT fk_conv_integration FOREIGN KEY (integration_id) REFERENCES channel_integrations(id)
);

CREATE TABLE messages (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  conversation_id CHAR(36) NOT NULL,
  external_message_id VARCHAR(128) NULL,
  sender_type VARCHAR(16) NOT NULL,
  direction VARCHAR(16) NOT NULL,
  content LONGTEXT NOT NULL,
  model_name VARCHAR(80) NULL,
  token_input INT NULL,
  token_output INT NULL,
  metadata_json JSON NULL,
  sent_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_msg_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_msg_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE sales (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  lead_id CHAR(36) NOT NULL,
  product_id CHAR(36) NOT NULL,
  conversation_id CHAR(36) NULL,
  status VARCHAR(24) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'BRL',
  closed_at DATETIME NULL,
  source_channel VARCHAR(24) NULL,
  notes TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_sales_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_sales_lead FOREIGN KEY (lead_id) REFERENCES leads(id),
  CONSTRAINT fk_sales_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT fk_sales_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE commission_rules (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  name VARCHAR(120) NOT NULL,
  priority INT NOT NULL DEFAULT 100,
  rule_scope VARCHAR(16) NOT NULL,
  client_id CHAR(36) NULL,
  product_id CHAR(36) NULL,
  percent_min DECIMAL(5,2) NULL,
  percent_max DECIMAL(5,2) NULL,
  fixed_percent DECIMAL(5,2) NULL,
  condition_type VARCHAR(24) NOT NULL,
  conditions_json JSON NULL,
  active_from DATETIME NOT NULL,
  active_to DATETIME NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  version_no INT NOT NULL DEFAULT 1,
  created_by_user_id CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  CONSTRAINT fk_cr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_cr_client FOREIGN KEY (client_id) REFERENCES clients(id),
  CONSTRAINT fk_cr_product FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE commission_calculations (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  sale_id CHAR(36) NOT NULL,
  rule_id CHAR(36) NOT NULL,
  applied_percent DECIMAL(5,2) NOT NULL,
  commission_amount DECIMAL(12,2) NOT NULL,
  calc_snapshot_json JSON NOT NULL,
  calculated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_cc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_cc_sale FOREIGN KEY (sale_id) REFERENCES sales(id),
  CONSTRAINT fk_cc_rule FOREIGN KEY (rule_id) REFERENCES commission_rules(id)
);

CREATE TABLE audit_logs (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  user_id CHAR(36) NOT NULL,
  entity_type VARCHAR(80) NOT NULL,
  entity_id CHAR(36) NOT NULL,
  action VARCHAR(40) NOT NULL,
  before_json JSON NULL,
  after_json JSON NULL,
  ip_address VARCHAR(64) NULL,
  user_agent VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE metric_snapshots (
  id CHAR(36) PRIMARY KEY,
  tenant_id CHAR(36) NOT NULL,
  metric_date DATE NOT NULL,
  granularity VARCHAR(16) NOT NULL,
  channel VARCHAR(24) NULL,
  client_id CHAR(36) NULL,
  product_id CHAR(36) NULL,
  leads_count INT NOT NULL DEFAULT 0,
  responses_count INT NOT NULL DEFAULT 0,
  conversions_count INT NOT NULL DEFAULT 0,
  closed_sales_count INT NOT NULL DEFAULT 0,
  revenue_total DECIMAL(14,2) NOT NULL DEFAULT 0,
  avg_close_time_seconds INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ms_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_ms_client FOREIGN KEY (client_id) REFERENCES clients(id),
  CONSTRAINT fk_ms_product FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### 3.2 Politicas de isolamento (equivalente a RLS)
> Observacao: MySQL nao possui RLS nativa como Postgres. Aplicar isolamento por `tenant_id` + validacao obrigatoria no backend + views seguras.

```sql
-- Contexto definido por request no pool/conn:
-- SET @req_user_id = '...';
-- SET @req_tenant_id = '...';

CREATE VIEW v_sales_secure AS
SELECT s.*
FROM sales s
JOIN tenant_users tu ON tu.tenant_id = s.tenant_id
WHERE tu.user_id = @req_user_id
  AND s.tenant_id = @req_tenant_id
  AND s.deleted_at IS NULL;
```

Regras por operacao (aplicadas no service/repository):
- SELECT: sempre `WHERE tenant_id = :tenant_id`.
- INSERT: `tenant_id` somente do contexto autenticado.
- UPDATE: bloquear se `tenant_id` divergente.
- DELETE: soft delete para dominio; hard delete apenas em tabelas tecnicas.

### 3.3 Triggers
```sql
DELIMITER $$

CREATE TRIGGER trg_tenant_after_insert_default_rule
AFTER INSERT ON tenants
FOR EACH ROW
BEGIN
  INSERT INTO commission_rules (
    id, tenant_id, name, priority, rule_scope,
    percent_min, percent_max, condition_type,
    active_from, is_active, version_no, created_by_user_id
  ) VALUES (
    UUID(), NEW.id, 'Regra padrao MVP', 100, 'tenant',
    2.00, 3.00, 'hybrid',
    NOW(), 1, 1, 'system'
  );
END$$

CREATE TRIGGER trg_sales_after_insert_commission
AFTER INSERT ON sales
FOR EACH ROW
BEGIN
  INSERT INTO commission_calculations (
    id, tenant_id, sale_id, rule_id,
    applied_percent, commission_amount, calc_snapshot_json
  )
  SELECT
    UUID(), NEW.tenant_id, NEW.id, r.id,
    COALESCE(r.fixed_percent, r.percent_min),
    ROUND(NEW.amount * (COALESCE(r.fixed_percent, r.percent_min) / 100), 2),
    JSON_OBJECT('rule', r.name, 'scope', r.rule_scope)
  FROM commission_rules r
  WHERE r.tenant_id = NEW.tenant_id
    AND r.is_active = 1
    AND (r.active_to IS NULL OR r.active_to >= NOW())
  ORDER BY r.priority ASC
  LIMIT 1;
END$$

DELIMITER ;
```

### 3.4 Indexes
```sql
CREATE INDEX idx_leads_tenant_channel_created ON leads (tenant_id, source_channel, created_at);
CREATE INDEX idx_conv_tenant_ext ON conversations (tenant_id, external_conversation_id);
CREATE INDEX idx_msg_tenant_conv_sent ON messages (tenant_id, conversation_id, sent_at);
CREATE INDEX idx_sales_tenant_closed_status ON sales (tenant_id, closed_at, status);
CREATE INDEX idx_cr_tenant_active_dates_prio ON commission_rules (tenant_id, is_active, active_from, active_to, priority);
CREATE INDEX idx_ms_tenant_date_gran_channel ON metric_snapshots (tenant_id, metric_date, granularity, channel);
CREATE INDEX idx_products_tenant_name ON products (tenant_id, name);
CREATE INDEX idx_ks_tenant_type_status ON knowledge_sources (tenant_id, source_type, status);
ALTER TABLE knowledge_chunks ADD FULLTEXT INDEX ftx_kc_content (content);
```

### 3.5 Seed data
```sql
INSERT INTO metric_snapshots (
  id, tenant_id, metric_date, granularity, channel,
  leads_count, responses_count, conversions_count, closed_sales_count, revenue_total
)
VALUES
  (UUID(), 'TENANT_ID', CURDATE(), 'day', 'whatsapp', 0, 0, 0, 0, 0),
  (UUID(), 'TENANT_ID', CURDATE(), 'day', 'email', 0, 0, 0, 0, 0);
```

## 4) Endpoints (request/response resumido)

| Metodo | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | /api/v1/auth/login | Publico | email, password | session criada |
| GET | /api/v1/auth/session | Sim | - | user_id, tenant_id |
| GET/POST | /api/v1/products | Sim | filtro / payload produto | lista / produto criado |
| POST | /api/v1/products/{id}/assets/upload | Sim | multipart file/url | asset registrado |
| POST | /api/v1/knowledge/sources/{id}/reindex | Sim | - | job_id |
| GET/POST | /api/v1/personas | Sim | payload persona | lista/persona |
| POST | /api/v1/personas/{id}/publish | Sim | version_no | persona publicada |
| POST | /api/v1/integrations/chatwoot/connect | Sim | config webhook | integracao ativa |
| POST | /api/v1/webhooks/chatwoot/inbound | Assinatura | payload evento | ack |
| GET | /api/v1/conversations/{id}/messages | Sim | - | mensagens |
| GET/POST | /api/v1/sales | Sim | venda/filtros | venda/lista |
| GET/POST | /api/v1/commissions/rules | Sim | regra/filtros | regra/lista |
| PATCH | /api/v1/commissions/rules/{id} | Sim | patch regra | regra atualizada |
| GET | /api/v1/metrics/dashboard | Sim | periodo/canal | KPIs |
| GET | /api/v1/metrics/export.csv | Sim | periodo | csv |

## 5) Agent graph (IA)
- Runtime: LangGraph.
- State: tenant_id, lead_id, conversation_id, message_text, attachments, lead_stage, intent, objections, retrieved_context, draft_reply, confidence_score.
- Nos:
- ingest_input
- transcribe_audio
- analyze_image
- classify_intent
- qualify_lead
- retrieve_rag (Qdrant)
- search_allowed_web
- handle_objection
- compose_chunks
- close_or_followup
- persist_events
- send_chatwoot
- Transicoes: entrada -> classificacao -> qualificacao -> RAG/web -> objecao/fechamento -> persistencia -> envio.
- Streaming: SSE.

## 6) Auth middleware (padrao iron-session -> proxy -> X-User-Id)
- Frontend autenticado por iron-session (cookie httpOnly).
- API route do Next.js valida sessao e injeta `X-User-Id`, `X-Tenant-Id`, `X-Request-Id`.
- FastAPI valida headers e associacao em `tenant_users`.
- Sem chamada direta frontend -> FastAPI.

## 7) Integracoes externas
- OpenAI: inferencia, analise de imagem, transcricao de audio.
- Chatwoot: recepcao/envio de mensagens via webhook/API.
- Redis: cache, rate limit, locks simples.
- Qdrant: vetor para RAG.
- Celery: filas de ingestao, follow-up, processamento assincrono de webhook/metricas.

## 8) Requisitos nao-funcionais (backend)
- Performance:
- CRUD p95 < 900ms.
- TTFT SSE ate 2s.
- Ingestao assincrona sem bloquear atendimento.
- Logging:
- JSON estruturado com request_id, tenant_id, user_id, latencia, status.
- Error handling:
- excecoes de dominio especificas.
- mensagens sem vazar stack/SQL para cliente.

## 9) Security checklist (backend)
- [ ] Sessao segura (httpOnly, secure, sameSite=lax).
- [ ] Validacao de `X-User-Id` e `X-Tenant-Id` em toda rota protegida.
- [ ] Isolamento por tenant_id em 100% das queries de dominio.
- [ ] Rate limiting por rota sensivel com Redis.
- [ ] CORS restritivo sem wildcard em producao.
- [ ] Upload validando MIME/extensao/tamanho (20MB).
- [ ] Webhooks Chatwoot com assinatura + idempotencia.
- [ ] Segredos fora de codigo (somente .env).

## 10) Stack e dependencias (requirements.txt)
```txt
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
alembic
asyncmy
redis
celery
qdrant-client
httpx
openai
python-multipart
orjson
structlog
python-dotenv
tenacity
```
