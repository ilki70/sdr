# Turn2C Adaptation Plan

## Goal
Adaptar o `sdr` para uso interno da equipe em operacao de consorcios com a Turn2C como backoffice de fechamento.

## Product Direction
- O produto deixa de ser um SaaS generico voltado a terceiros.
- O foco passa a ser operacao interna: SDR de IA, pre-venda, follow-up, monitoria e handoff humano.
- A Turn2C sera usada como sistema de fechamento e registro operacional, nao como alvo de automacao pesada no MVP.

## What Already Exists
- Backend FastAPI com auth multi-tenant, agentes, knowledge, mensagens, dashboard, quality e WhatsApp.
- Frontend Next.js com paginas para agentes, knowledge, conversations, dashboard, integrations, quality e agent lab.
- Ingestao de documentos, URLs e YouTube via RAG.
- Streaming SSE para simulacao de conversas.
- WhatsApp gateway real com QR pairing.

## Gaps For This Scenario
1. O front de agentes ainda e generico e precisa virar um configurador operacional de playbooks de consorcio.
2. A tela de knowledge precisa suportar curadoria de docs, URLs e videos por tema, agente e objetivo comercial.
3. A tela de conversations precisa virar inbox operacional com takeover humano, notas, tags e proximos passos.
4. A quality page precisa persistir revisoes e priorizar risco, conversao e compliance.
5. Falta um painel de operacao ao vivo com fila de atendimentos e visao de escalonamento humano.
6. Falta limpar a narrativa e os seeds do caso Vinac para um dominio interno mais neutro.

## Recommended MVP Phases
### Phase 1: Product Repositioning
- Renomear narrativa interna do projeto para consorcios/Turn2C.
- Atualizar prompts, seeds e telas para remover dependencia conceitual do caso Vinac.
- Adicionar configs de agente focadas em:
  - qualificacao
  - objecoes
  - compliance
  - handoff humano
  - follow-up

### Phase 2: Knowledge Studio
- Permitir organizar conhecimento por:
  - produto
  - tema
  - prioridade
  - tipo de fonte
  - agente alvo
- Melhorar ingestao de YouTube para transcricao/indexacao util, nao apenas oembed.
- Expor diff e reingestao com mais contexto operacional.

### Phase 3: Control Room
- Criar tela de conversas com:
  - filtros por agente/canal/status
  - timeline completa
  - notas internas
  - takeover humano
  - proximo passo
- Exibir metricas de carga e conversas por agente.

### Phase 4: Quality and Governance
- Persistir revisoes de qualidade.
- Adicionar score por:
  - compliance
  - grounding
  - proximo passo
  - conversao
- Marcar conversas que exigem intervencao humana.

### Phase 5: Turn2C Handoff
- Modelar ficha de lead padronizada para alimentacao na Turn2C.
- Estruturar handoff em vez de automacao de tela.
- Tratar automacao de browser como etapa posterior e opcional.

## Non-Goals For MVP
- Automatizar a Turn2C inteira sem API.
- Tornar o produto publico ou multi-cliente antes de validar a operacao interna.
- Reescrever a stack inteira.

## Next Concrete Step
- Priorizar a criacao de um novo "consorcios studio" no frontend e expandir os schemas/backend para playbooks de agente, knowledge organizado e inbox operacional.
