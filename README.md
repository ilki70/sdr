# Agente Vendedor

Projeto SaaS para operacao comercial com agentes de IA.

## Features

### 1) Scaffold backend FastAPI
Descricao curta: backend inicial com healthcheck, configuracao por ambiente, logging JSON e rotas base de auth/tenant.
Fluxo:
1. Subir backend com Uvicorn.
2. Chamar `GET /health` para validar disponibilidade.
3. Chamar `GET /api/v1/auth/session` com `X-User-Id` e `X-Tenant-Id`.

### 2) Sessao segura no frontend com iron-session
Descricao curta: login web salva sessao em cookie httpOnly e protege rotas operacionais.
Fluxo:
1. Abrir `/login` e informar email, senha e tenant.
2. Frontend cria sessao em `/api/auth/login`.
3. Middleware permite acesso a rotas como `/dashboard`.

### 3) Proxy autenticado Next.js -> FastAPI
Descricao curta: requests para backend passam por rota proxy que injeta `X-User-Id` e `X-Tenant-Id`.
Fluxo:
1. Frontend chama `/api/proxy/...`.
2. Proxy valida sessao.
3. Proxy encaminha para backend com headers de contexto.

### 4) Shell de aplicacao e paginas MVP
Descricao curta: estrutura inicial de landing + app logado com dashboard e modulos principais.
Fluxo:
1. Usuario acessa landing em `/`.
2. Usuario autentica em `/login`.
3. Usuario navega por dashboard, clientes, produtos, knowledge, personas, integracoes e comissoes.

### 5) Migrations de banco com Alembic
Descricao curta: cadeia de migrations para schema inicial, indexes de performance e triggers de comissao.
Fluxo:
1. Configurar `MYSQL_URL` no backend.
2. Executar `alembic upgrade head`.
3. Confirmar que revisao atual e `003_triggers`.

### 6) Backend core de dominio (clients, products, commissions)
Descricao curta: endpoints protegidos com contexto de tenant para CRUD inicial e upload validado.
Fluxo:
1. Chamar `POST /api/v1/clients` para criar cliente.
2. Chamar `POST /api/v1/products` para criar produto vinculado ao cliente.
3. Chamar `POST /api/v1/products/{id}/assets/upload` para enviar arquivo (ate 20MB).
4. Chamar `POST /api/v1/commissions/rules` para criar regra de comissao por tenant.

### 7) Agente inicial de mensagens (simulacao + SSE)
Descricao curta: pipeline inicial do agente comercial com classificacao de intencao, contexto e resposta em stream.
Fluxo:
1. Chamar `POST /api/v1/messages/simulate` com `message_text`.
2. Backend executa grafo inicial (`classify_intent -> retrieve_context -> compose_reply`).
3. Chamar `POST /api/v1/messages/stream` para receber tokens SSE da resposta.

### 8) Agent Lab (pagina de teste de conversacao)
Descricao curta: tela interna para testar conversacao em tempo real antes da integracao com Chatwoot.
Fluxo:
1. Fazer login em `/login` com email, senha e tenant.
2. Abrir `/agent-lab`.
3. Enviar mensagens e acompanhar resposta do agente em stream.

### 9) Autenticacao real com tenant e role
Descricao curta: login valida usuario, senha e acesso ao tenant no MySQL antes de criar sessao.
Fluxo:
1. Frontend envia credenciais para `/api/auth/login`.
2. Backend valida email/senha e membership em `tenant_users`.
3. Sessao iron-session armazena `userId`, `tenantId`, `role` e `email`.

### 10) Registro de usuario de teste
Descricao curta: cadastro para homologacao local com associacao de role no tenant.
Fluxo:
1. Abrir `/register`.
2. Informar nome, email, senha, tenant (slug ou id) e role.
3. Backend cria usuario e vinculo em `tenant_users`.

### 11) Stack local quase producao
Descricao curta: infraestrutura local com MySQL, Redis, Qdrant e Adminer via Docker Compose.
Fluxo:
1. Executar `docker compose up -d`.
2. Rodar `backend/scripts/bootstrap_local.ps1` para migrations e seed.
3. Iniciar backend (`uvicorn`) e frontend (`next dev`).

## Testes profundos locais
Pre-requisito:
- Docker Desktop em execucao.

1. Infra:
- `docker compose up -d`
2. Backend:
- `cd backend`
- `pip install -r requirements.txt`
- `alembic upgrade head`
- `python scripts/seed_deep_test_data.py`
- `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
3. Frontend:
- `cd frontend`
- `npm install`
- `npm run dev -- --hostname 127.0.0.1 --port 3000`
4. Acesso:
- login: `http://127.0.0.1:3000/login`
- email seed: `admin@agentevendedor.example.com`
- senha seed: `12345678`
- tenant: `tenant-lab`

Atalho PowerShell:
- `.\scripts\start-local-tests.ps1`

Se o MySQL local falhar na primeira inicializacao:
- `.\scripts\reset-local-tests.ps1`
- depois `.\scripts\start-local-tests.ps1`

## Deploy versionado da stack atendente3

A definicao atual observada em producao para a stack `atendente3` foi versionada em [`deploy/atendente3/README.md`](/home/ilki/sdr/deploy/atendente3/README.md) com stack Swarm e `.env.example`.

Estado atual:
- o repositório agora descreve a stack implantada;
- backend, frontend e `whatsapp-service` agora podem ser construidos/publicados pelo proprio repo;
- o canal WhatsApp passa a ter um webhook versionado no backend e um serviço dedicado no repositório.
