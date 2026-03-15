# atendente3 deploy

Esta pasta versiona a definicao atual da stack `atendente3` observada em producao no Docker Swarm/Portainer.

## O que foi alinhado

- Servicos atuais: `postgres`, `backend`, `frontend`, `db-admin` e `whatsapp-gateway`
- Rotas Traefik:
  - `pulse.orfi.com.br` -> `frontend`
  - `pulse-db.orfi.com.br` -> `db-admin`
- Volumes persistentes da stack
- Variaveis de ambiente observadas nos servicos
- Compatibilidade do manifesto com os Dockerfiles versionados neste repositório
- Isolamento interno entre servicos de app/banco em uma rede overlay propria para evitar colisao de aliases na rede Traefik externa

## Estado do alinhamento

As tres imagens da stack agora podem ser geradas a partir deste repositorio:

- `ghcr.io/ilki70/sdr/backend:latest`
- `ghcr.io/ilki70/sdr/frontend:latest`
- `ghcr.io/ilki70/sdr/whatsapp-gateway:latest`

O `whatsapp-gateway` versionado usa `whatsmeow`, expoe pareamento por QR code, persiste a sessao em `/data/session.db` e encaminha mensagens recebidas ao backend em `/api/v1/whatsapp/inbound`.

## Build das imagens locais

```bash
docker build -t ghcr.io/ilki70/sdr/backend:latest ./backend
docker build -t ghcr.io/ilki70/sdr/frontend:latest ./frontend
docker build -t ghcr.io/ilki70/sdr/whatsapp-gateway:latest ./services/whatsapp-gateway
```

## Publicacao automatica

O workflow [`build-atendente3-images.yml`](/home/ilki/sdr/.github/workflows/build-atendente3-images.yml) publica automaticamente no GHCR:

- `ghcr.io/ilki70/sdr/backend:latest`
- `ghcr.io/ilki70/sdr/frontend:latest`
- `ghcr.io/ilki70/sdr/whatsapp-gateway:latest`

Para a VPS usar as imagens do GitHub, ajuste o `.env` da stack a partir de `.env.example`, principalmente `DATABASE_URL`, `SESSION_SECRET`, `WHATSAPP_GATEWAY_SECRET` e os hosts publicos do Pulse.

## Contrato do canal WhatsApp

1. Crie uma integracao no app com:
   - `provider`: `whatsapp`
   - `inbox_ref`: `whatsapp-primary`
   - `api_base_url`: mesmo valor de `WHATSAPP_GATEWAY_BASE_URL`
   - `webhook_secret`: mesmo valor de `WHATSAPP_GATEWAY_SECRET`
2. No dashboard, use `Criar canal WhatsApp` e depois `Gerar QR code`.
3. O gateway pareia o dispositivo e repassa a carga ao backend, que cria/continua lead e conversa, executa o agente e devolve `reply_text`.

## Uso

1. Ajuste um arquivo `.env` a partir de `.env.example`.
2. Verifique que a rede externa configurada em `TRAEFIK_NETWORK` existe no Swarm.
3. O manifesto cria uma rede overlay interna da stack para trafego entre `postgres`, `backend`, `frontend`, `db-admin` e `whatsapp-gateway`, mantendo a rede Traefik externa apenas para o que precisa passar pelo proxy.
4. Faça o deploy:

```bash
docker stack deploy -c deploy/atendente3/stack.yml atendente3
```

## Proximo passo recomendado

Publicar as imagens e validar a stack completa contra a VPS, com teste real de QR pairing e roundtrip inbound/outbound de WhatsApp.
