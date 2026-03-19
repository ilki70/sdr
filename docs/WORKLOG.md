# Worklog

## 2026-03-19
- Evolucao do `sdr` para o cenario de consorcios/Turn2C foi refinada em tres subareas explicitas no frontend:
  - `playbook`
  - `knowledge`
  - `inbox`
- O hub de `consorcios` agora encaminha para essas telas dedicadas, enquanto o `playbook` publica a configuracao do agente e o `knowledge` concentra RAG, ingestao de fontes e laboratorio.
- Adicionada a rota `inbox` para acompanhamento de conversas com filtros, detalhe do atendimento e foco em handoff humano.
- Criado um novo manifesto de deploy em `deploy/sdr`, com nomes de router/servico em `sdr` e volumes preservados dos dados da stack antiga `atendente3`.
- Validacao local executada com sucesso:
  - `python3 -m py_compile` nos arquivos backend alterados
  - `npm run typecheck` no frontend
  - `npm run build` no frontend
- Proximo passo:
  - versionar e publicar a mudanca
  - atualizar o Portainer para a stack `sdr`
  - remover a dependencia operacional do nome antigo `atendente3`

## 2026-03-10
- Clonado o repositorio `sdr` em `/home/ilki/sdr`.
- Criados `docs/PROJECT_CONTEXT.md` e `docs/WORKLOG.md` para persistencia de contexto local.
- Portado para este repositório o material inicial de deploy da stack `atendente3`: `deploy/atendente3/stack.yml`, `.env.example` e `README.md`.
- Adicionados Dockerfiles e `.dockerignore` para `backend` e `frontend`.
- Ajustado o backend para aceitar `DATABASE_URL` generico com compatibilidade inicial para Postgres via `asyncpg`/`psycopg`.
- Adicionado workflow GitHub Actions para publicar imagens `backend` e `frontend` no GHCR do proprio repositório `sdr`.
- Atualizado o `README.md` raiz para apontar para o deploy versionado do `atendente3`.
- Corrigido o manifesto de deploy para usar as variaveis e portas realmente esperadas pelo código versionado (`DATABASE_URL`, `OPENAI_MODEL`, `BACKEND_INTERNAL_URL`, `SESSION_SECRET` e frontend em `3000`).
- Adicionado `whatsapp-service` versionado ao repositório, com Dockerfile, API mínima de relay para o backend e log local em `/data/events.jsonl`.
- Adicionado ao backend o webhook público `/api/v1/whatsapp/webhook` para processar mensagens inbound, manter lead/conversa e devolver a resposta do agente.
- Atualizados workflow GHCR, stack e documentação para usar a imagem `ghcr.io/ilki70/sdr/whatsapp-service:latest`.

## 2026-03-11
- Retomada a revisão das mudanças locais do `sdr` antes de qualquer alinhamento da stack `atendente3` na VPS.
- Confirmado que o repositório local já contém a linha de deploy versionada (`deploy/atendente3`), workflow GHCR, Dockerfiles e a integração mínima de WhatsApp no backend e no serviço dedicado.
- Identificado um risco importante no manifesto versionado: todos os serviços da stack estavam ligados direto à rede externa `orfinet3`, o que expunha o alias `postgres` a colisões com outros stacks no mesmo Swarm.
- Corrigido `deploy/atendente3/stack.yml` para usar uma rede overlay interna da stack (`internal`) entre `postgres`, `backend`, `frontend`, `db-admin` e `whatsapp-service`, mantendo `orfinet3` apenas onde há roteamento Traefik.
- Atualizada a documentação do deploy em `deploy/atendente3/README.md` para refletir o isolamento interno da stack.
- Limpos os diretórios `__pycache__` do workspace e validada a renderização do manifesto com `docker compose config`.
- Validada a sintaxe dos arquivos Python novos/alterados com `python3 -m py_compile`.
- Consolidado o trabalho em dois commits locais:
  - `f59f303` `Version atendente3 deploy and Postgres support`
  - `b4d25f1` `Add versioned WhatsApp webhook flow`
- Mantidos fora dos commits apenas os arquivos locais de contexto `docs/PROJECT_CONTEXT.md` e `docs/WORKLOG.md`.
- Enviado `main` para o GitHub com os commits `f59f303` e `b4d25f1`.
- Feito build local na VPS das imagens `atendente3/backend:latest`, `atendente3/frontend:latest` e `atendente3/whatsapp-service:latest` a partir do repositório `sdr`.
- Substituida a definicao persistida da stack `atendente3` no Portainer pela versao alinhada do repositório, mantendo o uso das imagens locais para este rollout.
- Redeployada a stack `atendente3` no Swarm com os servicos `postgres`, `backend`, `frontend`, `db-admin` e `whatsapp-service`.
- Validacoes apos rollout:
  - todos os servicos ficaram `1/1`
  - `frontend` publico respondeu HTTP 200 em `https://atendente3.orfi.com.br`
  - `db-admin` respondeu HTTP 403 fora da allowlist esperada
  - `backend` e `whatsapp-service` subiram sem erro nos logs de bootstrap
  - `whatsapp-service` respondeu `{\"status\":\"ok\"...}` no endpoint `/health`
  - `backend`, `postgres` e `whatsapp-service` ficaram isolados na rede `atendente3_internal`

## Current Status
- Repositorio local preparado para evoluir o deploy do `atendente3`.
- A stack `atendente3` agora esta descrita no repositório e `backend`/`frontend`/`whatsapp-service` podem ser gerados por ele.
- O fluxo WhatsApp agora tem uma implementacao versionada ponta a ponta, ainda com contrato minimo e sem adaptador para um provedor real.
- O manifesto versionado do deploy ficou mais seguro para Swarm compartilhado e esta pronto para comparação final com a stack antiga do Portainer.
- A producao da stack `atendente3` foi alinhada com essa linha versionada usando imagens locais geradas a partir do repo.
- Permanecem secrets/defaults placeholder na stack em producao, principalmente `SESSION_SECRET` do frontend e `WHATSAPP_WEBHOOK_SECRET` do `whatsapp-service`.

## Next Recommended Step
- Substituir os placeholders de secret em producao por valores reais e, se desejado, trocar o rollout local por imagens publicadas em registry para evitar dependencia de build manual na VPS.

## 2026-03-11
- Implementada a evolucao multiagente do produto em 5 fases sem quebrar o MVP atual.
- Fase 1:
  - adicionados `Agent`, `AgentVersion`, `agent_id` em `conversations`, `channel_integrations` e `knowledge_sources`
  - criado seed/migracao do agente default `Vinac Consorcios`
  - adaptado runtime do agente, fluxo do lab e webhook WhatsApp para resolver contexto por `agent_id`
  - corrigidas migrations antigas para compatibilidade real com Postgres
  - corrigido uso de `datetime` aware em colunas `DateTime()` sem timezone por meio do helper `app/core/time.py`
- Fase 2:
  - criada pagina `Agents` no frontend para listar, criar, detalhar e publicar novas versoes de atendentes
  - conectado o `Agent Lab` ao agente selecionado para testes guiados por agente
- Fase 3:
  - evoluida a pagina `Integrations` para vincular canais a um agente via `agent_id`
  - evoluida a pagina `Conversations` para operar como inbox minima com filtro por agente
- Fase 4:
  - enriquecido o dashboard com metricas operacionais por agente (`conversation_count`, abertas, bindings e ultima atividade)
- Fase 5:
  - criado modulo `Quality` com API e tela de monitoria heuristica das conversas mais recentes
  - score inicial baseado em presenca de resposta, intent, follow-up, fragmentacao, tamanho de resposta e dependencia de `mock-llm`
- Validacoes executadas ao longo das fases:
  - `alembic upgrade head` em Postgres temporario
  - simulacao HTTP real de registro, listagem/criacao de agentes, criacao de conversa e `/messages/simulate`
  - `python3 -m py_compile` nos arquivos backend alterados
  - `npm run typecheck` e `npm run build` no frontend
  - login via frontend, proxy autenticado e leituras reais de `/api/proxy/agents`, `/api/proxy/integrations`, `/api/proxy/messages/conversations`, `/api/proxy/dashboard/overview` e `/api/proxy/quality/reviews`

## Current Status
- O `sdr` agora suporta multiplos agentes por tenant com runtime, canal, inbox, analytics e monitoria inicial orientados por agente.
- A rota de monitoria ainda e heuristica e on-demand; nao persiste revisoes em tabela propria.
- O frontend expoe os modulos `Agents` e `Quality`, e `Integrations`/`Conversations` passaram a refletir o modelo multiagente.
- O codigo foi versionado em dois commits:
  - `a5be7b6` `Add multi-agent backend foundation and quality APIs`
  - `d618233` `Add multi-agent studio, inbox, analytics and quality UI`
- Os commits foram enviados ao GitHub em `main`.
- A stack `atendente3` em producao recebeu:
  - rebuild local de `atendente3/backend:latest`, `atendente3/frontend:latest` e `atendente3/whatsapp-service:latest`
  - migracao `006_agents_foundation` aplicada no Postgres da stack
  - rollout dos servicos `backend`, `frontend` e `whatsapp-service`
  - correcao do `SESSION_SECRET` do frontend e do `WHATSAPP_WEBHOOK_SECRET` na definicao persistida do Portainer
- Validacao final em producao publica:
  - `https://atendente3.orfi.com.br/` respondeu `200`
  - `register`, `login` e `session` do frontend voltaram a funcionar apos corrigir o `SESSION_SECRET`
  - fluxo real em HTTPS de criacao de agente, binding de integracao, criacao de conversa, `/messages/simulate`, `/dashboard/overview` e `/quality/reviews` passou com sucesso no tenant de homologacao criado durante a validacao
- Ativada a LLM real para testes e simulacoes em producao:
  - o backend recebeu `OPENAI_API_KEY` valida no runtime do Swarm
  - o modelo operacional do `atendente3` foi alinhado para `gpt-4.1-mini`, que ja estava funcional em outros servicos deste host
  - uma tentativa com `gpt-5-mini` falhou com `400 Bad Request` da OpenAI
  - validacao final em HTTPS publico mostrou resposta sem prefixo `mock-llm` e monitoria `Quality` sem achado relacionado a modo mock
- Tornada duravel a entrega da chave OpenAI:
  - criado secret de Swarm `atendente3_openai_api_key`
  - backend passou a suportar `OPENAI_API_KEY_FILE` com fallback seguro em `app/core/config.py`
  - o runtime do `atendente3_backend` agora monta `/run/secrets/atendente3_openai_api_key` e nao depende mais de `OPENAI_API_KEY` injetada manualmente
  - validacao final em HTTPS publico continuou retornando resposta real apos a migracao para secret do Swarm

## Next Recommended Step
- Decidir a proxima iteracao entre:
  - persistir revisoes de quality e historico de monitoria
  - introduzir adapter Chatwoot com binding por inbox
  - ampliar os criterios de score da monitoria agora que a LLM real esta ativa nas simulacoes

## 2026-03-11
- Reavaliado o alinhamento do produto com o escopo original apos a fase multiagente e a ativacao da LLM real.
- Feito benchmark de posicionamento com referencias de mercado focadas em operacao conversacional:
  - Intelia Converx
  - Blip
  - Botmaker
  - Intercom Fin
  - Chatwoot
- Conclusao do benchmark:
  - o `sdr` ja se alinhou ao eixo correto de produto, saindo de um atendente verticalizado para uma plataforma operacional multiagente
  - ainda faltam narrativa comercial mais forte, inbox mais madura, adaptadores de canal alem de WhatsApp e maior profundidade em analytics/quality
- Criada uma nova landing page institucional inspirada no modelo de plataforma modular observado no mercado, com foco em:
  - Studio, Inbox, Analytics e Quality
  - proposta de valor por operacao, nao por bot isolado
  - leitura explicita do que ja foi entregue no produto
- Ajustados metadata e idioma do layout para refletir o posicionamento comercial em portugues.
- Validacao executada:
  - `npm run build` no frontend apos a nova landing e ajuste de layout

## Current Status
- O produto esta tecnicamente mais proximo do escopo original de "varios atendentes configuraveis" do que do MVP inicial focado em Vinac.
- A narrativa comercial agora tambem comeca a refletir esse reposicionamento multiagente.
- A landing nova ainda precisa de rollout para a stack `atendente3` se a intencao for usa-la imediatamente em producao.

## Next Recommended Step
- Publicar a nova landing no `atendente3` e, na sequencia, aprofundar o produto em duas frentes:
  - adapter Chatwoot/inbox real
  - analytics e quality mais proximos de operacao comercial real

## 2026-03-11
- Refinada a landing comercial apos revisao de posicionamento.
- Removidas referencias excessivamente tecnicas, mencoes a roadmap e qualquer alusao ao caso Vinac.
- A landing passou a enfatizar:
  - proposta de valor comercial
  - modulos de negocio em linguagem simples
  - resultados operacionais esperados
  - CTA mais direto
- Validacao executada:
  - `npm run build` no frontend apos a reescrita comercial

## Current Status
- A home publica do produto esta mais coerente com uma proposta comercial B2B e menos com uma pagina de status de roadmap.

## Next Recommended Step
- Publicar a versao refinada da landing na stack `atendente3` e, depois disso, iterar em prova social, logos, casos de uso e secao de integracoes.

## 2026-03-11
- Aplicado rebranding comercial do produto para `Orfi Pulse`.
- Ajustados frontend e marketing para refletir a nova marca:
  - metadata global
  - landing page
  - login
  - cadastro
  - header interno
- Criado helper de marca em `frontend/lib/brand.ts` para evitar divergencia de nomenclatura.
- Atualizado o deploy versionado para usar `https://pulse.orfi.com.br` como URL principal e aceitar o host antigo como compatibilidade temporaria.
- Atualizada a definicao persistida do Portainer da stack `atendente3` com o novo host publico `pulse.orfi.com.br`.
- Rebuildado o frontend local `atendente3/frontend:latest` e reaplicada a stack no Swarm.
- Validacoes executadas:
  - `npm run build` no frontend
  - `docker stack deploy` da stack `atendente3`
  - `pulse.orfi.com.br` respondendo `200`
  - login em `https://pulse.orfi.com.br/login` exibindo `Orfi Pulse`

## Current Status
- A marca publica do produto agora e `Orfi Pulse`.
- O dominio principal ativo para o frontend e `https://pulse.orfi.com.br`.
- O stack ainda preserva compatibilidade de roteamento com `atendente3.orfi.com.br` como fallback temporario no Traefik.

## Next Recommended Step
- Fazer uma segunda rodada de branding para renomear modulos internos e menus (`Agents`, `Quality`, `Agent Lab`) para uma linguagem comercial mais coerente com `Orfi Pulse`.

## 2026-03-12
- Executada uma revisao sucinta de seguranca da VPS com foco em superficie exposta e configuracao Docker/Swarm.
- Achados principais:
  - container temporario `sdr-phase1-pg` exposto em `0.0.0.0:55432->5432` com credenciais fracas `test:test`
  - portas de cluster Docker Swarm escutando em todas as interfaces (`2377/tcp`, `7946/tcp+udp`, `4789/udp`) sem firewall local ativo (`ufw` ausente)
  - Portainer publico em `portainer3.orfi.com.br`, mantendo uma superficie administrativa critica exposta na internet
  - Traefik montado com `/var/run/docker.sock` em modo read-only, o que amplia impacto de eventual comprometimento do proxy
  - uso recorrente de imagens `latest` em stacks como Nextcloud, Firecrawl, Redis, Portainer Agent e outros, aumentando risco de drift e rollouts nao auditados
  - permanencia de containers e artefatos temporarios/de laboratorio fora do Swarm de producao
- Controles positivos observados:
  - `fail2ban` ativo para `sshd`
  - `PasswordAuthentication no`
  - `PermitRootLogin prohibit-password` em hardening complementar
  - `db-admin` da stack `atendente3` segue atras de allowlist

## Current Status
- A VPS esta funcional, mas com exposicoes evitaveis de alto impacto, principalmente a porta publica do Postgres temporario e a abertura ampla das portas do Swarm sem firewall local.

## Next Recommended Step
- Prioridade imediata:
  - remover ou isolar `sdr-phase1-pg`
  - fechar as portas do Swarm para IPs estritamente necessarios
  - revisar a exposicao publica do Portainer

## 2026-03-15
- Reimplementada a linha real de WhatsApp no `sdr` com gateway em Go baseado em `whatsmeow` e pareamento por QR code.
- O que entrou:
  - novo servico `services/whatsapp-gateway` com sessao persistida em SQLite, QR code e callback inbound para o backend
  - backend com endpoints autenticados de sessao (`/api/v1/whatsapp/bootstrap`, `/session`, `/session/connect`, `/session/disconnect`) e callback do gateway em `/api/v1/whatsapp/inbound`
  - preservada a rota webhook simplificada atual em `/api/v1/whatsapp/webhook` para nao quebrar compatibilidade imediata
  - dashboard com painel de QR/status do WhatsApp
  - tela de integracoes ajustada para default `whatsapp`
  - workflow/build e stack `atendente3` trocados de `whatsapp-service` para `whatsapp-gateway`
- Validacao executada:
  - parse sintatico dos arquivos Python alterados com `ast.parse`
  - `go build ./...` do gateway com toolchain portatil `Go 1.25.0`
  - `npm run build` do frontend em copia limpa com toolchain portatil `Node 20.20.1`
  - importacao completa do backend com Python compativel (`Miniforge` portatil) validando `app.main`, rotas WhatsApp e servico do gateway
  - startup do `uvicorn app.main:app` validado localmente em `127.0.0.1:8010`
  - revisao manual do diff para preservar as mudancas locais ja existentes em `deploy/atendente3/stack.yml`
- Limitacoes de validacao restantes no ambiente local:
  - `docker` continua indisponivel para o usuario atual por falta de acesso ao `docker.sock`
  - foi tentado build rootless da imagem com `buildkit` standalone, mas o host bloqueou os `mount` necessarios do solver OCI com `operation not permitted`

## Current Status
- A implementacao real de WhatsApp voltou para o codigo e para o deploy versionado.
- Gateway Go e frontend ja passaram em build local com toolchains portateis.
- Backend tambem passou em import/runtime real com Python compativel.
- Ainda nao foi feito rollout nem smoke end-to-end em stack real.

## Next Recommended Step
- Fazer o build das imagens e o rollout da stack real:
  - imagem do gateway `services/whatsapp-gateway`
  - backend/frontend/gateway atualizados na `atendente3`
  - para isso, liberar acesso ao daemon Docker para o usuario atual ou executar o build/publicacao via CI
  - depois testar QR real e um roundtrip inbound/outbound de WhatsApp

## 2026-03-19
- Iniciado o reposicionamento do `sdr` para uso interno da equipe em consorcios/Turn2C.
- Direcao definida:
  - a Turn2C sera tratada como backoffice de fechamento
  - a operacao comercial principal fica fora da plataforma, com agentes de IA, RAG e acompanhamento de conversas
  - o MVP nao vai depender de automacao pesada de tela nem de API da Turn2C
- Contexto duravel atualizado em [docs/PROJECT_CONTEXT.md](/home/ilki/sdr/docs/PROJECT_CONTEXT.md).
- Criado o plano de adaptacao em [docs/turn2c-adaptation-plan.md](/home/ilki/sdr/docs/turn2c-adaptation-plan.md).
- Principais lacunas mapeadas:
  - configurador operacional de agente para consorcios
  - knowledge studio com docs, URLs e YouTube organizados por tema/agente
  - inbox/control room com takeover humano e notas
  - quality persistente com foco em compliance e conversao
- Proximo passo recomendado:
  - implementar a primeira fatia do "consorcios studio" no frontend e expandir os schemas/backend para playbooks de agente e knowledge organizado
## 2026-03-19
- Evolucao do `sdr` para o cenario de consorcios/Turn2C foi refinada em tres subareas explicitas no frontend:
  - `playbook`
  - `knowledge`
  - `inbox`
- O hub de `consorcios` agora encaminha para essas telas dedicadas, enquanto o `playbook` publica a configuracao do agente e o `knowledge` concentra RAG, ingestao de fontes e laboratorio.
- Adicionada a rota `inbox` para acompanhamento de conversas com filtros, detalhe do atendimento e foco em handoff humano.
- Criado um novo manifesto de deploy em `deploy/sdr`, com nomes de router/servico em `sdr` e volumes preservados dos dados da stack antiga `atendente3`.
- Validacao local executada com sucesso:
  - `python3 -m py_compile` nos arquivos backend alterados
  - `npm run typecheck` no frontend
  - `npm run build` no frontend
- Proximo passo:
  - versionar e publicar a mudanca
  - atualizar o Portainer para a stack `sdr`
  - remover a dependencia operacional do nome antigo `atendente3`

## 2026-03-19
- Revisao e consolidacao da linha `Turn2C` para o `sdr`:
  - o produto passou a ser tratado explicitamente como uso interno da equipe
  - a estrategia de operacao interna foi detalhada em `docs/turn2c-adaptation-plan.md`
  - o novo `consorcios studio` foi separado em `playbook`, `knowledge` e `inbox`
  - a stack versionada foi renomeada para `sdr` com preservacao dos volumes antigos da `atendente3`
- Validacoes executadas:
  - `python3 -m py_compile` nos arquivos backend alterados
  - `npm run typecheck` e `npm run build` no frontend
- O rebase posterior precisou reconciliar a documentacao com o historico consolidado acima.
