# Implementation Plan - Agente Vendedor IA

## Batch 1: Infraestrutura
- Task 1.1: Criar estrutura base de pastas backend/frontend | Arquivos: `backend/app/*`, `frontend/app/*` | Verificacao: repositorio compila sem erro de import inicial.
- Task 1.2: Configurar `.env.example` backend/frontend | Arquivos: `backend/.env.example`, `frontend/.env.example` | Verificacao: todas variaveis obrigatorias listadas sem valores reais.
- Task 1.3: Configurar lint/typecheck no frontend | Arquivos: `frontend/package.json`, `frontend/tsconfig.json` | Verificacao: `npm run typecheck` executa sem erro de config.
- Task 1.4: Configurar format/logging base no backend | Arquivos: `backend/app/core/logging.py`, `backend/app/main.py` | Verificacao: endpoint `/health` loga request_id.

## Batch 2: Database
- Task 2.1: Criar migration inicial de tabelas core | Arquivos: `backend/alembic/versions/001_init_schema.py` | Verificacao: migration aplica em banco limpo.
- Task 2.2: Criar FKs e indexes de performance | Arquivos: `backend/alembic/versions/002_indexes.py` | Verificacao: `SHOW INDEX` retorna indices esperados.
- Task 2.3: Criar triggers de regra padrao e calculo comissao | Arquivos: `backend/alembic/versions/003_triggers.py` | Verificacao: inserir tenant cria regra 2%-3%; inserir venda cria calculo.
- Task 2.4: Seed inicial de canais e snapshots | Arquivos: `backend/scripts/seed_initial.sql` | Verificacao: registros iniciais existem por tenant teste.

## Batch 3: Backend Core
- Task 3.1: Implementar auth dependency (`X-User-Id`, `X-Tenant-Id`) | Arquivos: `backend/app/core/security.py` | Verificacao: rota protegida retorna 401 sem headers.
- Task 3.2: Implementar CRUD de clients/products | Arquivos: `backend/app/api/v1/clients/routes.py`, `backend/app/api/v1/products/routes.py` | Verificacao: criar/listar/editar funciona por tenant.
- Task 3.3: Implementar upload de assets com validacao | Arquivos: `backend/app/api/v1/products/routes.py`, `backend/app/services/uploads.py` | Verificacao: bloqueia tipo invalido e arquivo >20MB.
- Task 3.4: Implementar regras/comissoes | Arquivos: `backend/app/api/v1/commissions/routes.py` | Verificacao: atualizar regra no painel altera calculo de nova venda.

## Batch 4: Backend IA
- Task 4.1: Configurar cliente OpenAI + Qdrant | Arquivos: `backend/app/services/llm.py`, `backend/app/services/vector_store.py` | Verificacao: consulta vetorial retorna chunks do tenant.
- Task 4.2: Implementar pipeline de ingestao (Celery) | Arquivos: `backend/app/workers/tasks/ingestion.py` | Verificacao: job indexa doc/url/youtube e atualiza status.
- Task 4.3: Implementar LangGraph state/nodes/tools | Arquivos: `backend/app/agents/{state.py,nodes.py,tools.py,graph.py}` | Verificacao: fluxo de simulacao completa ida ate `send_chatwoot`.
- Task 4.4: Implementar SSE de resposta | Arquivos: `backend/app/api/v1/messages/routes.py` | Verificacao: cliente recebe stream parcial em ate 2s.

## Batch 5: Frontend Setup
- Task 5.1: Inicializar Next.js App Router + Tailwind + shadcn | Arquivos: `frontend/app/layout.tsx`, `frontend/tailwind.config.ts` | Verificacao: app sobe com estilos base.
- Task 5.2: Implementar layout "Sales Command Center" | Arquivos: `frontend/components/layout/app-shell.tsx` | Verificacao: shell renderiza no desktop e mobile web.
- Task 5.3: Implementar sessao iron-session no Next | Arquivos: `frontend/lib/session.ts`, `frontend/middleware.ts` | Verificacao: rota privada redireciona sem login.
- Task 5.4: Implementar proxy API routes | Arquivos: `frontend/app/api/**/route.ts` | Verificacao: requests chegam ao backend com headers corretos.

## Batch 6: Frontend Pages
- Task 6.1: Criar paginas de clients/products | Arquivos: `frontend/app/(app)/clients/*`, `frontend/app/(app)/products/*` | Verificacao: CRUD basico funcionando via proxy.
- Task 6.2: Criar tela knowledge com drag and drop | Arquivos: `frontend/app/(app)/knowledge/page.tsx`, `frontend/components/knowledge/dropzone-upload.tsx` | Verificacao: upload envia arquivo e mostra status.
- Task 6.3: Criar tela personas com timeline de versoes | Arquivos: `frontend/app/(app)/personas/page.tsx` | Verificacao: publicar versao altera versao ativa.
- Task 6.4: Criar tela conversations (chat interface) | Arquivos: `frontend/app/(app)/conversations/[id]/page.tsx` | Verificacao: mensagens aparecem com streaming SSE.

## Batch 7: Integracao Frontend <-> Backend
- Task 7.1: Integrar setup Chatwoot webhook | Arquivos: `frontend/app/(app)/integrations/page.tsx`, `backend/app/api/v1/integrations/chatwoot/routes.py` | Verificacao: webhook teste retorna ack.
- Task 7.2: Sincronizar eventos Chatwoot em leads/conversations/messages | Arquivos: `backend/app/workers/tasks/webhooks.py` | Verificacao: evento inbound cria/atualiza registros corretos.
- Task 7.3: Integrar dashboard de metricas | Arquivos: `frontend/app/(app)/dashboard/page.tsx`, `backend/app/api/v1/metrics/routes.py` | Verificacao: filtros alteram KPIs corretamente.
- Task 7.4: Integrar simulador de comissao | Arquivos: `frontend/components/commissions/rule-simulator.tsx` | Verificacao: preview bate com backend para mesma venda.

## Batch 8: Billing
- Task 8.1: Implementar regras de comissao por escopo | Arquivos: `backend/app/services/commissions.py` | Verificacao: tenant/client/produto selecionam regra esperada.
- Task 8.2: Implementar trilha de auditoria de alteracoes | Arquivos: `backend/app/services/audit.py` | Verificacao: toda alteracao de regra gera log before/after.
- Task 8.3: Criar relatorio CSV de comissoes | Arquivos: `backend/app/api/v1/commissions/routes.py` | Verificacao: export baixa CSV com filtros aplicados.
- Task 8.4: Criar pagina de comissoes no frontend | Arquivos: `frontend/app/(app)/commissions/page.tsx` | Verificacao: editar regra e visualizar impacto sem reload.

## Definicao de pronto (MVP)
- Login seguro funcionando com proxy autenticado.
- Ingestao RAG operacional para docs/URLs/YouTube.
- Chatwoot integrado por webhook inbound/outbound.
- Agent vende com fluxo dinamico, objecoes e follow-up.
- Dashboard de metricas funcional.
- Comissao configuravel no painel e calculada automaticamente.
