# whatsapp-service

Servico leve para versionar a ultima dependencia externa da stack `atendente3`.

## Funcao atual

- Recebe mensagens inbound por HTTP.
- Encaminha o payload padronizado ao backend em `/api/v1/whatsapp/webhook`.
- Persiste um log local em `/data/events.jsonl` para inspeção operacional.
- Expõe um endpoint de consulta dos ultimos eventos para debug.

## Variaveis de ambiente

- `BACKEND_WEBHOOK_URL`: URL do webhook do backend.
- `WHATSAPP_DEFAULT_INBOX_REF`: inbox default usado quando o caller nao informa `inbox_ref`.
- `WHATSAPP_WEBHOOK_SECRET`: secret default usado quando o caller nao informa `webhook_secret`.
- `WHATSAPP_SERVICE_DATA_DIR`: diretório de persistência local. Default: `/data`.
- `WHATSAPP_SERVICE_PORT`: porta HTTP. Default: `8080`.

## Endpoints

- `GET /health`
- `POST /api/messages/inbound`
- `GET /api/events`
