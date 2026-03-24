# Orfi Pulse

Orfi Pulse e a plataforma interna de operacao comercial do `sdr`.
Ela concentra configuracao de agentes, base de conhecimento, monitoria de conversas, integrações e apoio ao fechamento comercial.

O foco atual do produto e uso interno pela equipe, principalmente para operações de consorcio e fluxo comercial apoiado pela Turn2C.

## O que o sistema faz

- Configura perfis de atendimento e comportamento de agentes.
- Ingerir conhecimento por documentos, URLs, PDFs, DOCX, TXT e YouTube.
- Acompanhar conversas e handoff humano em tempo real.
- Operar um funil comercial por conversa, com status, resumo e proximo passo persistidos.
- Operar canais e integrações de entrada.
- Revisar qualidade das interações e apoiar melhoria contínua.
- Organizar a operação comercial por produtos, personas e comissões.

## Menu atual

O painel publica os modulos:

- Dashboard
- Agents
- Clients
- Products
- Knowledge
- Personas
- Integrations
- Conversations
- Quality
- Agent Lab
- Sales
- Commissions
- Settings

## Fluxo recomendado de uso

1. Defina as `Personas` e o tom operacional.
2. Configure os `Agents` com objetivo, limites e regras de handoff.
3. Cadastre `Products` e a estrutura comercial associada.
4. Alimente `Knowledge` com documentos, URLs e videos relevantes.
5. Ajuste `Integrations` para os canais de entrada.
6. Teste o comportamento no `Agent Lab`.
7. Acompanhe o atendimento em `Conversations`.
8. Revise respostas, risco e aderencia em `Quality`.
9. Monitore desempenho e resultado em `Dashboard` e `Commissions`.

Para operações de consorcio, o atalho recomendado e entrar em `Consorcios` e trabalhar em cima de:

- `Playbook`
- `Knowledge`
- `Inbox`

## Conversations

O modulo `Conversations` agora funciona como uma central operacional de funil SDR:

- tabela estilo CRM/inbox em dark mode
- colunas de entrada, ultima interacao, lead, status, agente, proximo passo e resumo
- filtros, busca, ordenacao e paginacao
- painel lateral para leitura da conversa
- acoes rapidas para `handoff`, `agendado`, `desqualificado` e retorno para `qualificacao`

O backend persiste esses dados diretamente em `Conversation`:

- `pipeline_status`
- `summary`
- `next_step`

Isso permite acompanhar o estado comercial da conversa sem depender apenas de inferencia em tempo de leitura.

## Login e multi-tenant

O sistema usa autenticação por:

- email
- senha
- `tenantId`

O tenant de homologacao mais usado no ambiente atual e `tenant-lab`.

Fluxo comum:

1. Acesse `https://pulse.orfi.com.br/login`.
2. Entre com email, senha e tenant.
3. Se for primeiro acesso em um tenant novo, use o cadastro.

## Recuperacao administrativa

Existe um caminho administrativo para reset de senha de usuario interno.
Ele e usado para suportar recuperacao de acesso sem expor um reset publico irrestrito.

Endpoint backend:

- `POST /api/v1/auth/admin/reset-user-password`

Proxy frontend:

- `POST /api/auth/admin/reset-user-password`

## RAG e base de conhecimento

A base de conhecimento foi desenhada para suportar operacao interna com fontes variadas:

- documentos internos
- links oficiais
- materiais de treinamento
- videos do YouTube
- textos de apoio comercial e compliance

O objetivo e alimentar o agente com contexto suficiente para qualificar lead, responder objeções e encaminhar para humano quando necessario.

## WhatsApp e atendimento

O fluxo de WhatsApp da plataforma foi reimplementado com gateway proprio baseado em `whatsmeow`, QR pairing e sessao persistida.

O frontend expoe a operacao e o backend concentra o processamento das mensagens e o handoff para a logica do agente.

## Deploy

O deploy de producao roda como stack `sdr` no Portainer.

Pontos importantes do deploy atual:

- o backend sobe com `alembic upgrade head` no boot
- a stack inclui `redis` e um worker Celery dedicado para consumir a fila de `Knowledge` e `Quality`
- o alias interno do backend no Swarm e `sdr_backend`
- os segredos esperados incluem `SESSION_SECRET`, `WHATSAPP_GATEWAY_SECRET` e `ADMIN_RESET_SECRET`
- quando o schema mudar, vale validar explicitamente a revisao Alembic publicada no Postgres da stack para evitar drift entre imagem e banco

## Desenvolvimento local

Requisitos:

- Docker
- Node.js para o frontend
- Python para o backend

Comandos tipicos:

```bash
docker compose up -d
cd backend && alembic upgrade head
```

Depois disso, suba backend e frontend conforme o seu ambiente local.

## Estrutura do repositório

- `backend/`: API FastAPI, auth, agentes, conhecimento e integrações.
- `frontend/`: app Next.js, dashboard e modulos operacionais.
- `deploy/`: stack e documentação de deploy.
- `docs/`: contexto duravel, worklog e notas de evolucao do produto.

## Status atual

O `sdr` esta orientado para uso interno da equipe como plataforma operacional de SDR/closer assistido.
A direção atual prioriza:

- configuração de agente
- RAG com conhecimento interno
- acompanhamento de conversas
- funil operacional por conversa
- suporte a consorcios/Turn2C
- handoff humano no momento certo
- migracao do motor principal de conversa para um runtime interno stateful com `langgraph`, sem dependencia de licenca no core do produto

## Observacoes

- O projeto nao deve depender de defaults temporarios de ambiente.
- O deploy precisa manter bootstrap de migrations no backend.
- O acesso multi-tenant deve ser preservado entre frontend, backend e banco.
