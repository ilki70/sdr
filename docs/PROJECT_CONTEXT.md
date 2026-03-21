# Project Context

## Project
`sdr`

## Purpose
Plataforma interna de operacao comercial com agentes de IA, backend FastAPI, frontend Next.js e stack local para testes quase-producao.

## Current Architecture
- Backend: FastAPI com auth, tenant context, migrations Alembic e stream SSE para mensagens.
- Frontend: Next.js com iron-session, landing, login e modulos operacionais do MVP.
- Infra local: Docker Compose com MySQL, Redis, Qdrant e Adminer.
- Produção Swarm: stack `sdr` com `redis`, `postgres`, `backend`, `worker`, `frontend`, `db-admin` e `whatsapp-gateway`.
- URL interna do backend no stack: usar `http://sdr_backend:8000` para evitar colisao com alias genérico `backend`.
- Fluxo principal: login por tenant, proxy autenticado frontend -> backend, laboratorio de agente para simulacao de conversas e central operacional interna.

## Current Priorities
- Reposicionar o produto para uso interno da equipe em consorcios/Turn2C.
- Preservar o contexto multi-tenant entre frontend, backend e banco.
- Evoluir o frontend para configurar comportamento do agente, ingerir conhecimento e acompanhar atendimentos em tempo real.
- Consolidar `Conversations` como inbox/CRM operacional com funil persistido por conversa.
- Manter o bootstrap local funcional enquanto a nova linha de produto evolui.
- Manter um caminho administrativo de recuperacao de acesso para usuarios/tenants, sem expor reset publico irrestrito.
- Garantir que o deploy `sdr` siga bootstrapando migrations no backend e use `sdr_backend` como alias interno no Swarm.
- Garantir que o deploy `sdr` tenha um worker Celery consumindo a fila de knowledge/quality via Redis, para evitar jobs eternamente em `queued`.

## Key References
- Main overview: `/home/ilki/sdr/README.md`
- Product/backend docs: `/home/ilki/sdr/docs/`
- Frontend app: `/home/ilki/sdr/frontend`
- Backend app: `/home/ilki/sdr/backend`
- Deploy stack: `/home/ilki/sdr/deploy/atendente3` (pasta historica; namespace da stack em producao: `sdr`)

## Notes For Future Sessions
- Ler `docs/WORKLOG.md` antes de editar para captar o estado mais recente.
- Registrar progresso transiente no worklog, mantendo aqui apenas contexto duravel.
- O foco atual e a adaptacao do `sdr` para um sistema interno de SDR/closer assistido para consorcios, com RAG de documentos e videos YouTube, monitoria de conversas e handoff humano quando necessario.
- A stack de producao deve ser tratada como `sdr`; `atendente3` continua apenas como nome historico em alguns caminhos, variaveis e recursos legados.
- A base de conhecimento ja aceita videos YouTube como fonte e tenta extrair transcript completo quando a legenda estiver disponivel, usando o oEmbed como fallback.
- O contexto curto de conversa agora e cacheado em Redis por `conversation_id` para evitar repeticao de perguntas e preservar `imovel`, `valor`, `prazo` e `lance` entre turnos.
- O fluxo de WhatsApp agora tambem leva `audio` e `image` para o backend via anexos, com transcricao/analisador multimodal quando houver arquivo disponivel.
- O agente pode responder em fragmentos curtos para simular conversa mais humana no canal.
- O schema de `Conversation` agora inclui `pipeline_status`, `summary` e `next_step`, usados pela tela de `Conversas` em formato CRM/inbox.
- Em producao, ja houve um drift entre codigo e banco nesse bloco; depois de rollouts que mexam em schema, vale conferir a revisao Alembic aplicada no Postgres da stack `sdr`.
- O clone legado em `/home/ilki/sdr` ficou com arquivos `root:root` dentro de `.git`; se for necessario reaproveita-lo, usar `GIT_OBJECT_DIRECTORY=/home/ilki/sdr/.git/objects-user` para gravar novos objetos.
