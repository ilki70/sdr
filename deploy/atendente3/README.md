# atendente3 deploy

Esta pasta versiona a definicao atual da stack `atendente3` observada em producao no Docker Swarm/Portainer em 2026-03-10.

## O que foi alinhado

- Servicos atuais: `postgres`, `backend`, `frontend`, `db-admin` e `whatsapp-service`
- Rotas Traefik:
  - `atendente3.orfi.com.br` -> `frontend`
  - `atendente3-db.orfi.com.br` -> `db-admin`
- Volumes persistentes da stack
- Variaveis de ambiente observadas nos servicos
- Compatibilidade do manifesto com os Dockerfiles versionados neste repositório
- Isolamento interno entre servicos de app/banco em uma rede overlay propria para evitar colisao de aliases na `orfinet3`

## Estado do alinhamento

As tres imagens da stack agora podem ser geradas a partir deste repositório:

- `ghcr.io/ilki70/sdr/backend:latest`
- `ghcr.io/ilki70/sdr/frontend:latest`
- `ghcr.io/ilki70/sdr/whatsapp-service:latest`

O `whatsapp-service` versionado recebe mensagens inbound, encaminha ao backend em `/api/v1/whatsapp/webhook` e mantém um log local em `/data/events.jsonl`.

## Build das imagens locais

```bash
docker build -t ghcr.io/ilki70/sdr/backend:latest ./backend
docker build -t ghcr.io/ilki70/sdr/frontend:latest ./frontend
docker build -t ghcr.io/ilki70/sdr/whatsapp-service:latest ./whatsapp-service
```

## Publicacao automatica

O workflow [`build-atendente3-images.yml`](/home/ilki/sdr/.github/workflows/build-atendente3-images.yml) publica automaticamente no GHCR:

- `ghcr.io/ilki70/sdr/backend:latest`
- `ghcr.io/ilki70/sdr/frontend:latest`
- `ghcr.io/ilki70/sdr/whatsapp-service:latest`

Para a VPS usar as imagens do GitHub, ajuste o `.env` da stack a partir de `.env.example`, principalmente `DATABASE_URL`, `SESSION_SECRET`, `WHATSAPP_WEBHOOK_SECRET` e os hosts publicos.

## Contrato do canal WhatsApp

1. Crie uma integracao no app com:
   - `provider`: `whatsapp-service`
   - `inbox_ref`: mesmo valor de `WHATSAPP_DEFAULT_INBOX_REF`
   - `api_base_url`: URL publica ou interna do `whatsapp-service`
   - `webhook_secret`: mesmo valor de `WHATSAPP_WEBHOOK_SECRET`
2. Envie uma mensagem para `POST /api/messages/inbound` do `whatsapp-service`.
3. O serviço repassa a carga ao backend, que cria/continua lead e conversa, executa o agente e devolve `reply_text`.

## Uso

1. Ajuste um arquivo `.env` a partir de `.env.example`.
2. Verifique que a rede externa `orfinet3` existe no Swarm.
3. O manifesto cria uma rede overlay interna da stack para trafego entre `postgres`, `backend`, `frontend`, `db-admin` e `whatsapp-service`, mantendo a `orfinet3` apenas para o que precisa passar pelo Traefik.
4. Faça o deploy:

```bash
docker stack deploy -c deploy/atendente3/stack.yml atendente3
```

## Proximo passo recomendado

Validar a stack completa contra a VPS e, se necessario, adaptar o `whatsapp-service` para o provedor real de WhatsApp usado em producao.
