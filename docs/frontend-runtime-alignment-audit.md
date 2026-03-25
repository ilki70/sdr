# Frontend Runtime Alignment Audit

Data: 2026-03-24

## Objetivo

Avaliar se as areas do frontend ligadas a operacao de agentes estao alinhadas com a nova estrutura do runtime publicada:

- `conversation_runtime_state`
- `conversation_runtime_context`
- `conversation_semantics`
- `conversation_policy`
- `channel_formatter`
- `langgraph_runtime` como orquestrador

## Resumo Executivo

O frontend nao esta uniformemente alinhado ao runtime novo.

- Alinhado de verdade:
  - `Agent Lab`
- Parcialmente alinhado:
  - `Conversations`
  - `Knowledge`
- Desalinhado:
  - `Agents`
  - `Personas`
  - `Training`

## Evidencias

### 1. Agent Lab

Status: alinhado

Motivos:

- Usa o fluxo de `messages/stream`, que chama `run_configured_sales_runtime`:
  - [`backend/app/api/v1/messages/routes.py`](/home/ilki/sdr/backend/app/api/v1/messages/routes.py)
  - [`backend/app/services/runtime_router.py`](/home/ilki/sdr/backend/app/services/runtime_router.py)
- A UI consome metadados do runtime novo:
  - `reply_fragments`
  - `follow_up_suggestion`
  - [`frontend/app/(app)/agent-lab/page.tsx`](/home/ilki/sdr/frontend/app/(app)/agent-lab/page.tsx)

Observacao:

- A tela ainda exibe `intent detectado`, mas no caminho novo isso hoje nao representa um estado rico da conversa. Serve mais como sinal tecnico do que como telemetria util.

### 2. Conversations

Status: parcialmente alinhado

Motivos:

- Usa dados reais de conversa e `pipeline_status`.
- Mas ainda depende de fallback heuristico na propria UI:
  - `inferMockStatus`
  - `buildMockSummary`
  - [`frontend/app/(app)/conversations/page.tsx`](/home/ilki/sdr/frontend/app/(app)/conversations/page.tsx)

Implicacao:

- A tela ainda nao foi redesenhada para ler o `conversation_runtime_state` como fonte primaria de verdade operacional.
- Parte da experiencia ainda e "maquiada" no frontend.

### 3. Knowledge

Status: parcialmente alinhado

Motivos:

- A area esta bem conectada ao backend de knowledge:
  - [`frontend/app/(app)/knowledge/page.tsx`](/home/ilki/sdr/frontend/app/(app)/knowledge/page.tsx)
  - [`backend/app/api/v1/knowledge/routes.py`](/home/ilki/sdr/backend/app/api/v1/knowledge/routes.py)
- O frontend proxy apenas encaminha para o backend:
  - [`frontend/app/api/proxy/[...path]/route.ts`](/home/ilki/sdr/frontend/app/api/proxy/[...path]/route.ts)

Implicacao:

- Como subsistema de ingestao/RAG, a area esta ok.
- Mas o runtime novo principal nao consome explicitamente configuracao de knowledge no caminho de resposta atual, entao o ciclo operacional ainda nao esta fechado ponta a ponta.

### 4. Agents

Status: desalinhado

Motivos:

- A tela administra:
  - `prompt_system`
  - `policy_json`
  - `tool_config_json`
  - `knowledge_config_json`
  - `channel_config_json`
  - [`frontend/app/(app)/agents/page.tsx`](/home/ilki/sdr/frontend/app/(app)/agents/page.tsx)
- Essas estruturas continuam existindo no backend:
  - [`backend/app/api/v1/agents/routes.py`](/home/ilki/sdr/backend/app/api/v1/agents/routes.py)
  - [`backend/app/services/agents.py`](/home/ilki/sdr/backend/app/services/agents.py)
- Mas o runtime novo nao le esses campos no caminho principal:
  - [`backend/app/services/runtime_router.py`](/home/ilki/sdr/backend/app/services/runtime_router.py)
  - [`backend/app/services/langgraph_runtime.py`](/home/ilki/sdr/backend/app/services/langgraph_runtime.py)

Implicacao:

- `Agents` hoje funciona como CRUD administrativo/versionamento.
- Nao funciona como painel realmente controlador do comportamento do runtime publicado.

### 5. Personas

Status: desalinhado

Motivos:

- A tela segue gerindo:
  - `tone`
  - `prompt_system`
  - `approach_rules`
  - `objection_playbook`
  - [`frontend/app/(app)/personas/page.tsx`](/home/ilki/sdr/frontend/app/(app)/personas/page.tsx)
- O backend preserva essas entidades:
  - [`backend/app/api/v1/personas/routes.py`](/home/ilki/sdr/backend/app/api/v1/personas/routes.py)
  - [`backend/app/services/personas.py`](/home/ilki/sdr/backend/app/services/personas.py)
- Mas o runtime novo nao consome isso diretamente.

Implicacao:

- A area esta operacional como cadastro/versionamento.
- Nao esta acoplada ao cerebro atual do agente.

### 6. Training

Status: desalinhado de forma critica

Motivos:

- O treinamento ainda usa o fluxo legado:
  - `run_sales_agent`
  - [`backend/app/services/training.py`](/home/ilki/sdr/backend/app/services/training.py)
- O runtime publicado hoje, por outro lado, esta atras de:
  - `run_configured_sales_runtime`
  - [`backend/app/api/v1/messages/routes.py`](/home/ilki/sdr/backend/app/api/v1/messages/routes.py)
  - [`backend/app/services/runtime_router.py`](/home/ilki/sdr/backend/app/services/runtime_router.py)

Implicacao:

- `Training` esta medindo e aplicando melhoria em cima do motor antigo.
- Isso e o maior desalinhamento funcional do produto hoje.

## Prioridade de Correcao

### P0

- Migrar `Training` para usar o runtime novo.

### P1

- Fazer `Agents` e `Personas` deixarem de ser apenas CRUD legado e passarem a alimentar a `conversation_policy` e/ou os parametros estruturados do runtime novo.

### P2

- Fazer `Conversations` ler `conversation_runtime_state` real em vez de inferir estado e resumo no frontend.

### P3

- Decidir explicitamente como `Knowledge` entra no runtime novo:
  - como tool
  - como prefetch
  - como etapa de grounding sob demanda

## Recomendacao Objetiva

Nao vale tentar "alinhar tudo de uma vez".

Sequencia recomendada:

1. Replugar `Training` no runtime novo.
2. Redefinir contrato de configuracao viva de `Agents` e `Personas`.
3. Expor `conversation_runtime_state` na API de `Conversations`.
4. Fechar o papel de `Knowledge` no runtime principal.

## Conclusao

Hoje o frontend ainda mistura:

- areas realmente operando sobre o runtime novo
- areas administrativas validas, mas desconectadas do motor publicado
- areas que ainda usam o legado como referencia operacional

O desalinhamento mais serio esta em `Training`, seguido por `Agents` e `Personas`.
