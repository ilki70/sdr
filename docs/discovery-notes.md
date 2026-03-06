# Discovery Notes -- Produto em Definicao
> Arquivo gerado automaticamente durante o workflow /build-saas.
> Fonte de verdade para geracao dos PRDs. Nao edite manualmente.

## Visao
- **Problema**: Dificuldade em ter bons vendedores em diversas areas e produtos; necessidade de padronizar e elevar a qualidade comercial.
- **Solucao proposta**: Agentes conversacionais (bots de IA) especialistas em vendas para conduzir leads no funil ate o fechamento.
- **Diferencial desejado**: Bot capaz de entender profundamente a dor do lead e dominar os produtos/servicos vendidos.
 - **Pitch**: "Terceirize seu time de vendas. Contrate o maior vendedor do mundo!"
- **Publico-alvo (uso diario)**: Times comerciais de outras empresas que desejam terceirizar operacao de vendas.
- **Referencia de mercado**: Nao definida no momento.

## Funcionalidades
- **Top 3 acoes principais**:
- 1) Definir e cadastrar produtos/servicos a venda com documentacao de referencia.
- 2) Definir aspectos relevantes da persona do bot vendedor.
- 3) Definir e acompanhar funil e metricas de conversao por etapa para otimizar fechamento.
- **IA no produto**: Sim, e o core (agente/chatbot de vendas).
- **Uploads/fontes de conhecimento**: Sim.
- **Tipos principais**: documentos, links de paginas da empresa do cliente na internet e videos do YouTube.
- **Integracoes externas obrigatorias (MVP)**: email e WhatsApp via CRM omnichannel (Chatwoot com kanban).
- **Base de conhecimento aprovada**: RAG com ingestao de documentos + busca web restrita as paginas do cliente.
- **Canal aprovado para MVP**: integracao apenas via webhooks do Chatwoot.
- **Analytics aprovado**: funil operacional no Chatwoot; plataforma exibe dashboard proprio de metricas.

## Monetizacao
- **Modelo de negocio (inicial)**: Empresa dona da plataforma opera os bots em sua propria infraestrutura para vender produtos/servicos de terceiros.
- **Receita**: Comissao por desempenho (resultado de vendas/fechamentos).
- **Modelo confirmado no discovery**: Comissao + formato adicional ainda nao definido (pode incluir mensalidade/setup no futuro).
- **Faixa de comissao (MVP)**: 2% a 3% por venda efetivada (referencia inicial).
- **Regra comercial aprovada**: comissao deve ser configuravel em painel (percentual, variacoes e regras futuras).

## Tecnico
- **Stack escolhida**: Next.js (frontend) + FastAPI (backend) + MySQL (database), em vez de Supabase/PostgreSQL.
- **Plataforma MVP**: So web responsivo.
- **Infra backend adicional aprovada**: Redis (cache/rate limit/filas leves) + Qdrant (vetor RAG) + Celery (filas robustas).

## Contexto
- **Referencia visual/wireframe**: Nao possui no momento.
- **Prazo ideal MVP**: 30 dias.
- **Observacoes adicionais**: Nenhuma no momento.

## PRD -- User Stories
- **US01**: Como gestor comercial de uma empresa cliente, quero alimentar uma base RAG com documentos e links das paginas da minha empresa para que o bot responda e venda com conhecimento atualizado.
- **Criterios de aceite US01**:
- 1) Usuario consegue cadastrar produto com nome, descricao, preco e condicoes comerciais.
- 2) Usuario consegue anexar documentos e URLs para indexacao vetorial por tenant.
- 3) Sistema faz busca semantica (RAG) e busca web apenas em dominios permitidos do cliente.
- 4) Bot utiliza apenas materiais vinculados ao tenant em respostas de venda.

- **US02**: Como gestor comercial, quero configurar a persona e o script-base do bot para que ele fale no tom da minha marca e siga minha estrategia.
- **Criterios de aceite US02**:
- 1) Usuario define tom de voz, regras de abordagem e objecoes comuns.
- 2) Configuracao pode ser testada em ambiente de simulacao antes de publicar.
- 3) Alteracoes de persona entram em vigor em novas conversas em ate 60 segundos.

- **US03**: Como gestor comercial, quero conectar canais via Chatwoot para que leads conversem com o bot em canais reais usando webhooks.
- **Criterios de aceite US03**:
- 1) Integracao com Chatwoot concluida por webhook de entrada e webhook de saida.
- 2) Conversas recebidas via webhook chegam ao bot com identificacao de conta, inbox e contato.
- 3) Se webhook falhar, sistema registra erro, aplica retry e alerta o gestor.

- **US04**: Como gestor comercial, quero acompanhar metricas comerciais da operacao para otimizar taxa de fechamento.
- **Criterios de aceite US04**:
- 1) Funil operacional fica no Chatwoot; plataforma mostra dashboard proprio de metricas.
- 2) Metricas podem ser filtradas por periodo e canal.
- 3) Dados do dashboard atualizam em no maximo 5 minutos apos eventos.

- **US05**: Como operador da plataforma, quero registrar vendas fechadas e configurar regras de comissao em painel para manter o modelo comercial flexivel e auditavel.
- **Criterios de aceite US05**:
- 1) Venda fechada registra valor, cliente, origem e timestamp.
- 2) Sistema calcula comissao conforme regra ativa definida no painel (padrao inicial 2% a 3%).
- 3) Painel permite alterar percentual e condicoes por cliente/conta sem deploy.
- 4) Relatorio mensal exportavel com total vendido e comissao gerada por conta.

## PRD -- Requisitos Funcionais
- **Auth**
- RF-AUTH-01: Sistema deve permitir login seguro por email/senha para usuarios internos (time operador).
- RF-AUTH-02: Sistema deve suportar sessao com cookie httpOnly via iron-session no frontend.
- RF-AUTH-03: Todas as rotas protegidas devem exigir contexto de tenant e user autenticado.

- **Core Features**
- RF-CORE-01: Cadastrar clientes (contas) e produtos/servicos com atributos comerciais.
- RF-CORE-02: Ingerir documentos (PDF/DOC/TXT), URLs de paginas do cliente e links de videos YouTube.
- RF-CORE-03: Processar ingestao para base RAG (chunking, embeddings e indexacao por tenant).
- RF-CORE-04: Executar busca semantica na base RAG para suportar respostas do agente.
- RF-CORE-05: Executar busca web restrita a dominios permitidos do cliente (allowlist).
- RF-CORE-06: Configurar persona do bot (tom, abordagem, objecoes, regras comerciais).
- RF-CORE-07: Versionar configuracoes de persona e base de conhecimento com historico de alteracoes.
- RF-CORE-08: Receber eventos de mensagem do Chatwoot via webhook e iniciar processamento do agente.
- RF-CORE-09: Enviar respostas do agente ao Chatwoot via webhook/API de saida.
- RF-CORE-10: Implementar retries idempotentes para falhas de webhook/canal.
- RF-CORE-11: Registrar eventos de conversa (lead, etapa, intento, resposta, status).
- RF-CORE-12: Registrar vendas fechadas com vinculo ao lead, canal e tenant.

- **Dashboard / Metrics**
- RF-DASH-01: Exibir dashboard de metricas (nao o funil operacional) com KPIs comerciais.
- RF-DASH-02: KPIs minimos: total de leads atendidos, taxa de resposta, taxa de conversao, taxa de fechamento, ticket medio, tempo medio de fechamento, receita gerada.
- RF-DASH-03: Filtros por periodo, canal, cliente e produto.
- RF-DASH-04: Atualizacao de metricas em ate 5 minutos apos novos eventos.
- RF-DASH-05: Exportar relatorios de performance e comissoes em CSV.

- **Billing / Comissionamento**
- RF-BILL-01: Calcular comissao automaticamente por venda conforme regra ativa.
- RF-BILL-02: Regra inicial padrao deve suportar faixa de 2% a 3%.
- RF-BILL-03: Painel administrativo deve permitir alterar regra de comissao sem deploy.
- RF-BILL-04: Regras devem suportar variacoes por cliente, produto, periodo e performance.
- RF-BILL-05: Toda mudanca de regra deve gerar trilha de auditoria (quem alterou, quando, antes/depois).

- **Status**: Secao 2.2 aprovada pelo usuario sem ajustes.

## PRD -- Requisitos Nao-Funcionais
- **Seguranca**
- RNF-SEC-01: Autenticacao frontend-backend deve usar iron-session com cookie httpOnly, secure e sameSite=lax.
- RNF-SEC-02: Frontend nao acessa backend diretamente; todas as chamadas passam por proxy autenticado no Next.js.
- RNF-SEC-03: Backend deve validar `X-User-Id` e contexto de tenant em 100% das rotas protegidas.
- RNF-SEC-04: Isolamento multi-tenant obrigatorio no banco (filtro por tenant_id/user_id em todas as consultas de dados sensiveis).
- RNF-SEC-05: Validacao de input obrigatoria em todas as rotas via Pydantic (sem payload livre).
- RNF-SEC-06: Rate limiting por user_id/tenant em rotas sensiveis (auth, webhooks, geracao IA, billing).
- RNF-SEC-07: CORS restritivo, permitindo apenas dominios do frontend autorizado.
- RNF-SEC-08: Upload deve validar MIME type, extensao e tamanho maximo antes de persistir.
- RNF-SEC-09: Logs e erros retornados ao frontend nao podem expor stack trace, SQL ou dados sensiveis.

- **Performance**
- RNF-PERF-01: Tempo medio de resposta de APIs CRUD < 500 ms (p95 < 900 ms) em condicao nominal.
- RNF-PERF-02: Respostas de IA devem usar streaming SSE para primeira resposta em ate 2 segundos (TTFT alvo).
- RNF-PERF-03: Processos de ingestao RAG devem ser assincronos e nao bloquear atendimento em tempo real.
- RNF-PERF-04: Dashboard deve carregar em ate 2 segundos para periodos de ate 30 dias (p95).
- RNF-PERF-05: Todas as integracoes externas (Chatwoot, LLM, scraping) devem ter timeout e retry configurados.

- **UX**
- RNF-UX-01: Aplicacao web responsiva (desktop e mobile web) com foco em operacao desktop.
- RNF-UX-02: Estados de loading, vazio e erro devem existir em todas as telas principais.
- RNF-UX-03: Fluxos criticos (conectar canal, publicar persona, alterar comissao) devem ser executados em no maximo 3 passos.
- RNF-UX-04: Painel de metricas deve permitir leitura rapida com KPIs de topo e filtros claros.
- RNF-UX-05: Interface deve manter consistencia visual e feedback imediato apos acoes sensiveis.

- **Status**: Secao 2.3 aprovada pelo usuario sem requisitos adicionais.

## Database -- Entidades e Relacoes
- **Entidades propostas**: users, tenants, tenant_users, clients, products, product_assets, knowledge_sources, knowledge_chunks, bot_personas, persona_versions, channel_integrations, chatwoot_webhook_events, leads, conversations, messages, sales, commission_rules, commission_calculations, audit_logs, metric_snapshots.
- **Status**: Lista de entidades aprovada pelo usuario sem adicoes.
- **commission_rules.condicoes**: Modelo misto aprovado (opcoes fixas + JSON extra para flexibilidade).
- **Delete strategy**: Misto aprovado (soft delete na maioria + hard delete em dados temporarios/tecnicos).
- **Versionamento aprovado**: persona + regras de comissao + produtos/conteudo de conhecimento.

### Tabelas (campos principais)
- `users`: id, email (unique), password_hash, full_name, is_active, created_at, updated_at.
- `tenants`: id, name, slug (unique), status, created_at, updated_at, deleted_at (soft).
- `tenant_users`: id, tenant_id, user_id, role (`owner|admin|operator|viewer`), created_at.
- `clients`: id, tenant_id, name, segment, website_url, status, created_at, updated_at, deleted_at.
- `products`: id, tenant_id, client_id, name, description, base_price, currency, sales_terms_json, is_active, version_no, created_at, updated_at, deleted_at.
- `product_assets`: id, tenant_id, product_id, asset_type (`document|url|youtube`), title, storage_path, source_url, mime_type, size_bytes, checksum_sha256, created_by_user_id, created_at, deleted_at.
- `knowledge_sources`: id, tenant_id, product_id, source_type (`document|url|youtube|webpage`), source_ref, status, version_no, last_indexed_at, created_at, updated_at, deleted_at.
- `knowledge_chunks`: id, tenant_id, source_id, chunk_index, content, embedding_ref, token_count, created_at.
- `bot_personas`: id, tenant_id, name, description, active_version_no, is_active, created_at, updated_at, deleted_at.
- `persona_versions`: id, tenant_id, persona_id, version_no, tone, approach_rules_json, objection_playbook_json, prompt_system, is_published, created_by_user_id, created_at.
- `channel_integrations`: id, tenant_id, provider (`chatwoot`), inbox_ref, api_base_url, webhook_secret_enc, config_json, status, created_at, updated_at, deleted_at.
- `chatwoot_webhook_events`: id, tenant_id, integration_id, event_uid (unique), event_type, payload_json, received_at, processed_at, process_status, retry_count, last_error.
- `leads`: id, tenant_id, integration_id, external_contact_id, name, email, phone, source_channel, lifecycle_status, first_seen_at, last_seen_at, metadata_json, created_at, updated_at, deleted_at.
- `conversations`: id, tenant_id, lead_id, integration_id, external_conversation_id, channel, status, started_at, ended_at, created_at, updated_at.
- `messages`: id, tenant_id, conversation_id, external_message_id, sender_type (`lead|bot|human`), direction (`inbound|outbound`), content, model_name, token_input, token_output, metadata_json, sent_at, created_at.
- `sales`: id, tenant_id, lead_id, product_id, conversation_id, status, amount, currency, closed_at, source_channel, notes, created_at, updated_at, deleted_at.
- `commission_rules`: id, tenant_id, name, priority, rule_scope (`tenant|client|product`), client_id, product_id, percent_min, percent_max, fixed_percent, condition_type (`fixed|performance|tiered|hybrid`), conditions_json, active_from, active_to, is_active, version_no, created_by_user_id, created_at, updated_at, deleted_at.
- `commission_calculations`: id, tenant_id, sale_id, rule_id, applied_percent, commission_amount, calc_snapshot_json, calculated_at, created_at.
- `audit_logs`: id, tenant_id, user_id, entity_type, entity_id, action, before_json, after_json, ip_address, user_agent, created_at.
- `metric_snapshots`: id, tenant_id, metric_date, granularity (`hour|day|week|month`), channel, client_id, product_id, leads_count, responses_count, conversions_count, closed_sales_count, revenue_total, avg_close_time_seconds, created_at.

### Relacoes principais
- `tenant_users.tenant_id -> tenants.id`; `tenant_users.user_id -> users.id`.
- `clients.tenant_id -> tenants.id`.
- `products.tenant_id -> tenants.id`; `products.client_id -> clients.id`.
- `product_assets.product_id -> products.id`; `product_assets.tenant_id -> tenants.id`.
- `knowledge_sources.product_id -> products.id`; `knowledge_chunks.source_id -> knowledge_sources.id`.
- `bot_personas.tenant_id -> tenants.id`; `persona_versions.persona_id -> bot_personas.id`.
- `channel_integrations.tenant_id -> tenants.id`; `chatwoot_webhook_events.integration_id -> channel_integrations.id`.
- `leads.integration_id -> channel_integrations.id`; `conversations.lead_id -> leads.id`.
- `messages.conversation_id -> conversations.id`.
- `sales.lead_id -> leads.id`; `sales.product_id -> products.id`; `sales.conversation_id -> conversations.id`.
- `commission_rules.tenant_id -> tenants.id`; `commission_calculations.sale_id -> sales.id`; `commission_calculations.rule_id -> commission_rules.id`.

### Isolamento multi-tenant (politica equivalente a RLS no MySQL)
- `SELECT`: permitido apenas se `record.tenant_id` pertencer a tenant associado ao `X-User-Id` (validado via `tenant_users`).
- `INSERT`: permitido apenas com `tenant_id` do contexto autenticado; rejeitar inserts cross-tenant.
- `UPDATE`: permitido apenas para registros do mesmo tenant e com role autorizada (`owner|admin|operator`).
- `DELETE`: soft delete para tabelas de negocio; hard delete permitido apenas em tabelas tecnicas (`chatwoot_webhook_events`) via job autenticado.
- Regra geral: toda query de dominio inclui `tenant_id` obrigatorio e validacao de associacao do usuario.

### Triggers
- `trg_set_updated_at_*` (BEFORE UPDATE): atualiza `updated_at` em tabelas mutaveis.
- `trg_sales_after_insert_commission` (AFTER INSERT em `sales`): enfileira/calcula comissao com regra ativa e grava em `commission_calculations`.
- `trg_tenant_after_insert_default_rule` (AFTER INSERT em `tenants`): cria regra inicial de comissao (2% a 3%).

### Indexes recomendados
- Todos FKs indexados.
- Compostos por performance:
- `leads (tenant_id, source_channel, created_at)`.
- `conversations (tenant_id, external_conversation_id)`.
- `messages (tenant_id, conversation_id, sent_at)`.
- `sales (tenant_id, closed_at, status)`.
- `commission_rules (tenant_id, is_active, active_from, active_to, priority)`.
- `metric_snapshots (tenant_id, metric_date, granularity, channel, client_id, product_id)`.
- Busca:
- `products (tenant_id, name)`.
- `knowledge_sources (tenant_id, source_type, status)`.
- `knowledge_chunks FULLTEXT(content)` (fallback textual alem da busca vetorial).

### Seed data inicial
- Regra de comissao padrao por tenant: `percent_min=2.0`, `percent_max=3.0`, `condition_type=hybrid`, `is_active=true`.
- Persona padrao por tenant: "Closer Consultivo" (rascunho inicial editavel).
- Canais base de metrica habilitados: `whatsapp`, `email`.

### Diagrama ER (texto)
- `users` N:N `tenants` via `tenant_users`.
- `tenants` 1:N `clients`.
- `clients` 1:N `products`.
- `products` 1:N `product_assets` e 1:N `knowledge_sources`.
- `knowledge_sources` 1:N `knowledge_chunks`.
- `tenants` 1:N `bot_personas`; `bot_personas` 1:N `persona_versions`.
- `tenants` 1:N `channel_integrations`; `channel_integrations` 1:N `chatwoot_webhook_events`.
- `channel_integrations` 1:N `leads`; `leads` 1:N `conversations`; `conversations` 1:N `messages`.
- `leads/products/conversations` 1:N `sales` (cada venda referencia 1 lead, 1 produto e opcionalmente 1 conversa).
- `tenants` 1:N `commission_rules`; `sales` 1:N `commission_calculations` (1 registro principal por venda no MVP).
- `tenants` 1:N `audit_logs` e 1:N `metric_snapshots`.

- **Status**: Etapa 3 (Database) aprovada pelo usuario.

## Backend -- Endpoints e Integracoes
- **APIs externas MVP aprovadas**: OpenAI + Chatwoot.

### Estrutura de pastas (backend)
- `app/main.py`
- `app/core/config.py`
- `app/core/security.py`
- `app/core/logging.py`
- `app/api/v1/auth/routes.py`
- `app/api/v1/tenants/routes.py`
- `app/api/v1/clients/routes.py`
- `app/api/v1/products/routes.py`
- `app/api/v1/knowledge/routes.py`
- `app/api/v1/personas/routes.py`
- `app/api/v1/integrations/chatwoot/routes.py`
- `app/api/v1/conversations/routes.py`
- `app/api/v1/messages/routes.py`
- `app/api/v1/sales/routes.py`
- `app/api/v1/commissions/routes.py`
- `app/api/v1/metrics/routes.py`
- `app/services/*` (dominios)
- `app/schemas/*` (Pydantic)
- `app/repositories/*`
- `app/workers/celery_app.py`
- `app/workers/tasks/{ingestion,followup,metrics,webhooks}.py`
- `app/agents/{graph.py,state.py,nodes.py,tools.py,prompts/}`

### Endpoints principais (metodo | path | auth)
- `GET | /health | publico`
- `POST | /api/v1/auth/login | publico`
- `POST | /api/v1/auth/logout | autenticado`
- `GET | /api/v1/auth/session | autenticado`
- `GET | /api/v1/tenants/current | autenticado`
- `GET/POST | /api/v1/clients | autenticado`
- `GET/PATCH/DELETE | /api/v1/clients/{id} | autenticado`
- `GET/POST | /api/v1/products | autenticado`
- `GET/PATCH/DELETE | /api/v1/products/{id} | autenticado`
- `POST | /api/v1/products/{id}/assets/upload | autenticado`
- `POST | /api/v1/knowledge/sources | autenticado`
- `POST | /api/v1/knowledge/sources/{id}/reindex | autenticado`
- `GET | /api/v1/knowledge/sources | autenticado`
- `GET/POST | /api/v1/personas | autenticado`
- `POST | /api/v1/personas/{id}/publish | autenticado`
- `POST | /api/v1/integrations/chatwoot/connect | autenticado`
- `POST | /api/v1/webhooks/chatwoot/inbound | publico (assinatura obrigatoria)`
- `POST | /api/v1/webhooks/chatwoot/status | publico (assinatura obrigatoria)`
- `GET | /api/v1/conversations | autenticado`
- `GET | /api/v1/conversations/{id}/messages | autenticado`
- `POST | /api/v1/messages/simulate | autenticado`
- `GET/POST | /api/v1/sales | autenticado`
- `GET/POST | /api/v1/commissions/rules | autenticado`
- `PATCH | /api/v1/commissions/rules/{id} | autenticado`
- `GET | /api/v1/commissions/report | autenticado`
- `GET | /api/v1/metrics/dashboard | autenticado`
- `GET | /api/v1/metrics/export.csv | autenticado`

### Middleware/auth e integracao FE-BE
- Fluxo: `Next.js (iron-session cookie)` -> `API proxy Next.js` -> header `X-User-Id`, `X-Tenant-Id`, `X-Request-Id` -> `FastAPI`.
- FastAPI valida headers + associacao `tenant_users` em todas as rotas protegidas.
- Rate limit por `tenant_id + user_id` via Redis.
- Webhooks Chatwoot validam assinatura/HMAC + idempotencia por `event_uid`.

### Padroes de implementacao
- Error handling com excecoes de dominio (`UnauthorizedTenantError`, `CommissionRuleError`, etc).
- Logging estruturado JSON com `request_id`, `tenant_id`, `user_id`, latencia e status.
- Schemas 100% Pydantic para request/response, sem payload dinamico direto.
- Timeouts/retries para OpenAI/Chatwoot com backoff exponencial.

## Backend -- Agent Graph
- **Capacidades aprovadas (MVP+)**:
- Busca RAG.
- Busca web em dominios permitidos do cliente.
- Qualificacao de lead.
- Tratamento de objecoes.
- Conducao para fechamento.
- Analise de imagem.
- Transcricao de audio.
- Capacidade de picotar mensagens longas em blocos curtos/contextuais.
- Follow-up automatico conforme regras do tenant.
- **Fluxo do agente**: Dinamico com decisoes do agente (LangGraph com roteamento por estado).
- **Streaming de IA**: SSE aprovado.

### Agent graph (LangGraph)
- **State tipado**: tenant_id, lead_id, conversation_id, channel, message_text, attachments, lead_stage, intent, objections, retrieved_context, next_action, draft_reply, confidence_score.
- **Nos**:
- `ingest_input`: normaliza texto/audio/imagem.
- `transcribe_audio`: transcreve audio para texto (quando houver).
- `analyze_image`: extrai sinais comerciais de imagem (quando houver).
- `classify_intent`: identifica intencao e etapa do funil.
- `qualify_lead`: aplica criterios de qualificacao.
- `retrieve_rag`: consulta Qdrant por tenant/produto.
- `search_allowed_web`: busca web so em dominios permitidos.
- `handle_objection`: escolhe estrategia de contorno de objecao.
- `compose_chunks`: divide mensagem em blocos curtos e progressivos.
- `close_or_followup`: decide fechamento agora ou follow-up.
- `persist_events`: grava mensagens/eventos/venda.
- `send_chatwoot`: envia resposta ao Chatwoot (SSE para operador/simulador).
- **Transicoes**:
- entrada -> classificacao -> (qualificacao) -> (rag/web conforme necessidade) -> objecao/fechamento -> persistencia -> envio.
- loops curtos quando `confidence_score` baixo ou resposta incompleta.
- **Tools**:
- `tool_rag_search`, `tool_web_search_allowlist`, `tool_product_lookup`, `tool_commission_preview`, `tool_followup_scheduler`.

- **Status**: Etapa 4 (Backend Architecture) aprovada pelo usuario.

## Frontend -- Paginas e Componentes
- **Landing no MVP**: Landing simples + app logado.

### Mapa de paginas (Next.js App Router)
- `app/(marketing)/page.tsx` (landing simples com proposta de valor e CTA).
- `app/(marketing)/demo/page.tsx` (simulacao curta do bot).
- `app/(auth)/login/page.tsx`.
- `app/(app)/layout.tsx` (shell autenticado).
- `app/(app)/dashboard/page.tsx` (metricas principais).
- `app/(app)/clients/page.tsx`.
- `app/(app)/clients/[id]/page.tsx`.
- `app/(app)/products/page.tsx`.
- `app/(app)/products/[id]/page.tsx`.
- `app/(app)/knowledge/page.tsx` (fontes RAG).
- `app/(app)/personas/page.tsx`.
- `app/(app)/integrations/page.tsx` (Chatwoot webhook setup).
- `app/(app)/conversations/page.tsx`.
- `app/(app)/conversations/[id]/page.tsx` (chat interface).
- `app/(app)/sales/page.tsx`.
- `app/(app)/commissions/page.tsx` (regras + simulacao).
- `app/(app)/settings/page.tsx`.

### Arvore de componentes
- `components/layout/{app-shell,command-bar,tenant-switcher}.tsx`
- `components/metrics/{kpi-card,metric-chart,metric-filters,export-button}.tsx`
- `components/knowledge/{dropzone-upload,source-list,reindex-button}.tsx`
- `components/chat/{chat-thread,message-bubble,quick-replies,typing-stream}.tsx`
- `components/persona/{persona-form,version-timeline,publish-dialog}.tsx`
- `components/commissions/{rule-table,rule-form,rule-simulator,audit-drawer}.tsx`
- `components/shared/{empty-state,error-state,loading-skeleton,confirm-dialog}.tsx`

### Camada de API (frontend)
- `lib/api/fetcher.ts`: wrapper com timeout, correlation-id, tratamento padrao de erro.
- `lib/api/client.ts`: funcoes tipadas por dominio.
- `hooks/use-session.ts`, `hooks/use-tenant.ts`.
- `hooks/use-sse-chat.ts`: streaming SSE para simulador/operador.
- `hooks/use-metrics.ts`, `hooks/use-commission-rules.ts`.
- Todas chamadas passam por rotas proxy em `app/api/*` (sem acesso direto ao FastAPI).

### Auth flow (Next.js + iron-session)
- Login cria sessao httpOnly.
- Middleware protege rotas `/(app)` e redireciona para `/login` quando sem sessao.
- API routes de proxy leem sessao, injetam `X-User-Id` e `X-Tenant-Id`, e encaminham ao backend.
- Logout invalida cookie e limpa estado cliente.

## Frontend -- Design System
- **Referencia visual**: Nao ha referencia externa; usuario solicitou sugestao de direcao visual.
- **Layout dashboard**: "Me surpreenda" (direcao autoral, sem template padrao).
- **Paleta/tema**: "Me surpreenda" (direcao visual propria, sem depender de tema padrao).
- **Componentes especiais MVP**: chat interface + drag and drop upload.

### Direcao visual proposta (autoral)
- Estetica: "Sales Command Center" com identidade forte, foco em performance comercial.
- Layout: painel assimetrico com cards modulares e trilha lateral contextual (nao sidebar tradicional fixa).
- Tipografia sugerida: `Space Grotesk` (titulos) + `IBM Plex Sans` (texto).
- Cores base:
- `--bg-0: #0B1020`, `--bg-1: #111831`
- `--surface: #18233F`
- `--accent: #19C37D` (acao/conversao)
- `--warning: #F59E0B`, `--danger: #EF4444`, `--info: #38BDF8`
- Motion: entrada em stagger para cards, transicoes curtas (120-180ms), destaque de metricas em atualizacao.
- Componentes base: shadcn/ui + blocos custom para chat e metricas.
- Referencias de UX sugeridas: Linear (clareza), Stripe Dashboard (densidade util), interacoes de comandos estilo "ops cockpit".

- **Status**: Etapa 5 (Frontend Architecture) aprovada pelo usuario.

## Security -- Decisoes
- **Auth/sessao**: iron-session com cookie httpOnly + secure + sameSite=lax (sem OAuth social no MVP).
- **Rate limiting**: Diferenciado por rota (politica por sensibilidade/risco).
- **Upload permitido (MVP)**: pdf/doc/txt/imagem/audio/video ate 20MB por arquivo.

### Checklist de seguranca (MVP)
- **Session config**
- Cookie: `httpOnly=true`, `secure=true`, `sameSite=lax`, `path=/`, `maxAge` curto com renovacao controlada.
- `SESSION_SECRET` com 32+ caracteres em `.env` (nunca no codigo).

- **Auth flow**
- Login: valida credenciais, cria sessao, associa `user_id` + `tenant_id`.
- Logout: invalida sessao no servidor e cookie no cliente.
- Sessao expirada: proxy retorna 401 controlado e frontend redireciona para `/login`.

- **Isolamento multi-tenant (RLS equivalente no MySQL)**
- Toda query de dominio filtra por `tenant_id` obrigatorio.
- Backend valida `X-User-Id` + associacao em `tenant_users`.
- Operacoes cross-tenant bloqueadas e auditadas.

- **CORS**
- Permitir apenas dominios do frontend oficial (dev/stage/prod explicitos).
- Bloquear `*` em ambiente de producao.

- **Input validation**
- 100% das entradas validadas via Pydantic.
- Sanitizacao de URLs para allowlist em busca web.
- Validacao de MIME/extensao/tamanho em upload.

- **Webhooks**
- Chatwoot: validar assinatura + idempotencia por `event_uid`.
- Stripe: validacao de assinatura obrigatoria se billing Stripe for habilitado futuramente.

- **.env.example (obrigatorio)**
- `SESSION_SECRET=`
- `NEXT_PUBLIC_APP_URL=`
- `BACKEND_INTERNAL_URL=`
- `MYSQL_URL=`
- `REDIS_URL=`
- `QDRANT_URL=`
- `OPENAI_API_KEY=`
- `CHATWOOT_BASE_URL=`
- `CHATWOOT_API_TOKEN=`
- `CHATWOOT_WEBHOOK_SECRET=`
- `RATE_LIMIT_DEFAULT_PER_MIN=`
- `ALLOWED_ORIGINS=`

- **Status**: Etapa 6 (Security) aprovada pelo usuario.
- **Etapa 7**: Documentos finais gerados em `docs/prd-backend.md`, `docs/prd-frontend.md`, `docs/implementation-plan.md`.
