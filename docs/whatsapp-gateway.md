# WhatsApp Gateway

## Objetivo
Este microservico conecta o sistema ao WhatsApp via `whatsmeow`.

Ele faz quatro coisas:
1. abre o pareamento por QR code
2. persiste a sessao do dispositivo
3. recebe mensagens do WhatsApp
4. repassa ao backend para o agente responder automaticamente

## Referencias oficiais
- Repositorio: https://github.com/tulir/whatsmeow
- API docs: https://pkg.go.dev/go.mau.fi/whatsmeow

## Arquitetura

### Componentes
- `services/whatsapp-gateway/main.go`
- backend FastAPI em `/api/v1/whatsapp/*`
- dashboard em `/dashboard`

### Responsabilidade de cada camada
- Go gateway:
  - transporte WhatsApp
  - sessao persistente
  - QR code
  - envio e recebimento de mensagens
- Backend:
  - multitenancy
  - lead, conversation e message
  - execucao do agente
  - resposta comercial
- Frontend:
  - controle do canal
  - polling de status
  - exibicao do QR code

## Fluxo de conexao
1. Usuario entra no dashboard.
2. Clica em `Criar canal WhatsApp`.
3. O backend cria ou reaproveita a integracao `provider=whatsapp`.
4. O backend configura o gateway com:
- `tenant_id`
- `integration_id`
- `callback_url`
- `callback_secret`
5. Usuario clica em `Gerar QR code`.
6. O gateway chama `GetQRChannel()` e `Connect()` do `whatsmeow`.
7. O dashboard passa a exibir o QR code.
8. Usuario escaneia com o WhatsApp no celular.
9. O gateway persiste a sessao do dispositivo.

## Fluxo de mensagem recebida
1. O lead envia mensagem no WhatsApp.
2. O `whatsmeow` recebe o evento `events.Message`.
3. O gateway extrai o texto da mensagem.
4. O gateway faz callback para `POST /api/v1/whatsapp/inbound`.
5. O backend:
- resolve a integracao
- cria ou reaproveita lead
- cria ou reaproveita conversation
- roda o agente
- salva as mensagens
- devolve `reply_text`
6. O gateway envia a resposta ao lead com `SendMessage()`.

## Persistencia

### Sessao do dispositivo
- arquivo SQLite em `services/whatsapp-gateway/data/session.db`
- mantida pelo `sqlstore` do `whatsmeow`

### Configuracao do gateway
- arquivo JSON em `services/whatsapp-gateway/data/runtime.json`
- guarda tenant, integration e callback atual

## Endpoints do gateway
- `GET /health`
- `PUT /api/v1/session/config`
- `POST /api/v1/session/connect`
- `POST /api/v1/session/disconnect`
- `GET /api/v1/session/status`

Todos, exceto `/health`, exigem header:
- `X-WhatsApp-Gateway-Secret`

## Endpoints do backend
- `POST /api/v1/whatsapp/bootstrap`
- `GET /api/v1/whatsapp/session`
- `POST /api/v1/whatsapp/session/connect`
- `POST /api/v1/whatsapp/session/disconnect`
- `POST /api/v1/whatsapp/inbound`

## Variaveis importantes

### Backend
- `BACKEND_INTERNAL_URL`
- `WHATSAPP_GATEWAY_BASE_URL`
- `WHATSAPP_GATEWAY_SECRET`

### Gateway
- `WHATSAPP_GATEWAY_PORT`
- `WHATSAPP_GATEWAY_DATA_DIR`
- `WHATSAPP_GATEWAY_SECRET`

## Como rodar localmente

### Pelo script principal
```powershell
.\scripts\start-local-tests.ps1
```

### Manualmente
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd services\whatsapp-gateway
& "C:\Program Files\Go\bin\go.exe" run .
```

## Como testar
1. Login em `http://127.0.0.1:3000/login`
2. Abrir `http://127.0.0.1:3000/dashboard`
3. Criar o canal WhatsApp
4. Gerar o QR code
5. Escanear com o celular
6. Enviar uma mensagem para o numero pareado
7. Confirmar que a resposta voltou automaticamente

## Limitacoes atuais
- uma sessao WhatsApp por gateway
- ainda sem painel dedicado de historico do canal no dashboard
- sem automacao de reconciliacao com Chatwoot
- segredo unico para controle e callback; em producao o ideal e separar
