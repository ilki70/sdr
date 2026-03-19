# Project Context

## Project
`sdr`

## Purpose
Plataforma interna de operacao comercial com agentes de IA, backend FastAPI, frontend Next.js e stack local para testes quase-producao.

## Current Architecture
- Backend: FastAPI com auth, tenant context, migrations Alembic e stream SSE para mensagens.
- Frontend: Next.js com iron-session, landing, login e modulos operacionais do MVP.
- Infra local: Docker Compose com MySQL, Redis, Qdrant e Adminer.
- Fluxo principal: login por tenant, proxy autenticado frontend -> backend, laboratorio de agente para simulacao de conversas e central operacional interna.

## Current Priorities
- Reposicionar o produto para uso interno da equipe em consorcios/Turn2C.
- Preservar o contexto multi-tenant entre frontend, backend e banco.
- Evoluir o frontend para configurar comportamento do agente, ingerir conhecimento, acompanhar atendimentos em tempo real e separar o `consorcios studio` em subareas explicitas.
- Manter o bootstrap local funcional enquanto a nova linha de produto evolui.

## Key References
- Main overview: `/home/ilki/sdr/README.md`
- Product/backend docs: `/home/ilki/sdr/docs/`
- Frontend app: `/home/ilki/sdr/frontend`
- Backend app: `/home/ilki/sdr/backend`
- Deploy stack: `/home/ilki/sdr/deploy/sdr`

## Notes For Future Sessions
- Ler `docs/WORKLOG.md` antes de editar para captar o estado mais recente.
- Registrar progresso transiente no worklog, mantendo aqui apenas contexto duravel.
- O foco atual e a adaptacao do `sdr` para um sistema interno de SDR/closer assistido para consorcios, com RAG de documentos e videos YouTube, monitoria de conversas, handoff humano quando necessario e stack `sdr` substituindo a antiga `atendente3`.
