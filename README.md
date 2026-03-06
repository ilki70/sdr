# Agente Vendedor

Plataforma SaaS para operacao comercial com agentes de IA focados em qualificacao, objecao, conducao e fechamento.

## Estado atual
- Landing publica com demo interativa e captura de lead.
- App logado com dashboard, knowledge, personas, integracoes, conversations, commissions e sales.
- Backend FastAPI com auth por sessao via proxy Next.js.
- RAG com ingestao de URL, upload e indexacao em Qdrant.
- Laboratorio de simulacao com caso VINAC e avaliacao automatica.
- Gateway WhatsApp em Go com `whatsmeow`, QR code no dashboard e sessao persistente.

## Como o produto funciona
O produto tem dois modos de uso complementares:

1. Modo publico
- A landing apresenta a proposta comercial.
- A demo publica conversa com o backend real.
- O formulario da landing captura um caso comercial real e abre uma conversa persistida.

2. Modo operacional
- O usuario entra no app com tenant.
- Configura cliente, produto, fontes de conhecimento, persona e integracoes.
- Testa o agente no `Agent Lab`.
- Acompanha metricas, historico de conversa e sinais de qualificacao no dashboard.

## Logica de uso
Fluxo recomendado para usar o MVP do jeito certo:

1. Criar ou acessar um tenant
- Login em `/login`.
- Sessao criada com `iron-session`.
- Toda chamada autenticada passa pelo proxy do Next.js, que injeta `X-User-Id` e `X-Tenant-Id` no backend.

2. Estruturar contexto comercial
- Criar cliente.
- Criar produto.
- Subir conhecimento no painel `Knowledge` por URL ou arquivo.
- Publicar persona/playbook em `Personas`.

3. Testar antes de ligar canal real
- Usar `Agent Lab` para abrir conversas locais persistidas.
- Rodar cenarios de objecao, qualificacao e fechamento.
- Ajustar persona, playbook e base de conhecimento.

4. Simular operacao comercial
- Usar a demo publica para validar primeira conversa.
- Capturar leads pela landing.
- Conferir no dashboard leads, conversas, qualificacao iniciada e handoff pronto.

5. Evoluir para omnichannel
- Configurar integracoes.
- Plugar Chatwoot.
- Manter o mesmo nucleo de memoria, RAG, persona e metricas.

## Modulos principais

### Landing publica
- Rota: `/`
- Objetivo: apresentar valor, capturar demanda e mandar o lead para o backend.

### Demo publica
- Rota: `/demo`
- Objetivo: mostrar a agente em streaming, usando sessao persistida no backend.

### Agent Lab
- Rota: `/agent-lab`
- Objetivo: laboratorio controlado para testar memoria, follow-up e qualidade da resposta antes de integrar canais reais.

### Knowledge
- Rota: `/knowledge`
- Objetivo: ingerir conhecimento, reindexar fontes e testar recuperacao semantica.

### Personas
- Rota: `/personas`
- Objetivo: editar e publicar o playbook comercial sem mexer em codigo.

### Dashboard
- Rota: `/dashboard`
- Objetivo: acompanhar setup do tenant, sinais de operacao comercial e o pareamento do WhatsApp por QR code.

### WhatsApp Gateway
- Pasta: `services/whatsapp-gateway`
- Objetivo: manter a sessao do dispositivo, exibir QR code e encaminhar mensagens do WhatsApp para o backend responder com o agente.

## Fluxos tecnicos

### Auth
1. Frontend envia credenciais para `/api/auth/login`.
2. Backend valida usuario, tenant e senha.
3. Frontend salva sessao segura em cookie `httpOnly`.
4. Middleware protege todas as rotas do app.

### Demo publica
1. Frontend chama `/api/demo/stream`.
2. Route handler encaminha para `/api/v1/public/demo/stream`.
3. Backend cria ou reaproveita `conversation_id`.
4. Agente responde via SSE.
5. Mensagens ficam persistidas no banco.

### Captura de lead
1. Landing envia formulario para `/api/marketing/leads`.
2. Backend cria `lead` + `conversation`.
3. O historico inicial fica salvo para retomada comercial posterior.

### Dashboard
1. Frontend chama `/api/proxy/dashboard/overview`.
2. Backend agrega metricas do tenant.
3. O frontend so renderiza; a logica de contagem fica centralizada no backend.

### WhatsApp
1. Dashboard chama `/api/proxy/whatsapp/bootstrap` para criar/configurar o canal.
2. Dashboard chama `/api/proxy/whatsapp/session/connect` para gerar o QR code.
3. O gateway Go abre a sessao `whatsmeow` e persiste a credencial do dispositivo.
4. Mensagens recebidas sao enviadas para `/api/v1/whatsapp/inbound`.
5. O backend processa com o agente e devolve o texto de resposta.
6. O gateway envia a resposta automaticamente ao lead no WhatsApp.

## Enderecos locais
- Landing: `http://127.0.0.1:3000/`
- Demo: `http://127.0.0.1:3000/demo`
- Login: `http://127.0.0.1:3000/login`
- Dashboard: `http://127.0.0.1:3000/dashboard`
- Agent Lab: `http://127.0.0.1:3000/agent-lab`
- Knowledge: `http://127.0.0.1:3000/knowledge`
- Backend health: `http://127.0.0.1:8000/health`

## Ambiente local

### Infra
- MySQL
- Redis
- Qdrant
- Adminer

Suba com:

```powershell
docker compose up -d
```

### Bootstrap

```powershell
.\scripts\start-local-tests.ps1
```

Se o ambiente estiver corrompido:

```powershell
.\scripts\reset-local-tests.ps1
.\scripts\start-local-tests.ps1
```

## Credenciais seed
- Email: `admin@agentevendedor.example.com`
- Senha: `12345678`
- Tenant: `tenant-lab`

## Referencias oficiais do WhatsApp
- Repositorio `whatsmeow`: https://github.com/tulir/whatsmeow
- API docs `whatsmeow`: https://pkg.go.dev/go.mau.fi/whatsmeow

## Validacoes importantes
- `python -m compileall backend`
- `npm run typecheck`
- `npm run build`
- `go build ./...` em `services/whatsapp-gateway`

## Documentacao complementar
- Logica de uso detalhada: [docs/project-usage.md](C:/Users/ilki/OneDrive/Desktop/Agente%20Vendedor/docs/project-usage.md)
- Plano de implementacao: [docs/implementation-plan.md](C:/Users/ilki/OneDrive/Desktop/Agente%20Vendedor/docs/implementation-plan.md)
- Gateway WhatsApp: [docs/whatsapp-gateway.md](C:/Users/ilki/OneDrive/Desktop/Agente%20Vendedor/docs/whatsapp-gateway.md)
- PRD backend: [docs/prd-backend.md](C:/Users/ilki/OneDrive/Desktop/Agente%20Vendedor/docs/prd-backend.md)
- PRD frontend: [docs/prd-frontend.md](C:/Users/ilki/OneDrive/Desktop/Agente%20Vendedor/docs/prd-frontend.md)



