# Worklog

## 2026-03-20
- Preparei o release candidate do `sdr` para commit/push/release/redeploy:
  - estabilizei as mudancas de autenticação, contexto multimodal, WhatsApp, knowledge, dashboard e deploy da stack
  - a validacao local passou com `PYTHONPYCACHEPREFIX=/tmp/sdr-pyc python3 -m compileall -q app tests`
  - o frontend passou em `npx tsc --noEmit --incremental false` e em `./node_modules/.bin/next build --webpack` na copia limpa em `/home/ilki/tmp/frontend-check`
- Proximo passo recomendado:
  - publicar o commit, criar a release e reaplicar a stack `sdr` no Portainer

## 2026-03-20
- Smoke multimodal do `sdr` validado em producao:
  - audio local em `/app/test-media/smoke-speech.mp3` foi transcrito como `Quero comprar uma casa em seis meses e tenho duzentos mil de lance`
  - imagem local em `/app/test-media/smoke-image.png` foi analisada e entrou no contexto da conversa
  - o agente respondeu usando `property`, prazo e lance, com `reply_fragments` curtos
- Corrigido o fallback de transcricao em `conversation_media.py` para usar `whisper-1` quando `openai_audio_transcription_model` nao existe no settings
- A stack `sdr` foi reaplicada no Portainer com bind mounts temporarios para backend, frontend `.next` e gateway, apenas para reiniciar os containers e validar o smoke sem depender de push/GHCR
- Proximo passo recomendado:
  - formalizar o fallback de transcricao em config/testes e decidir se o caminho temporario de redeploy local deve virar regressao automatizada

## 2026-03-20
- Fechei o buffer de mensagens picotadas no `sdr`:
  - mensagens curtas e fragmentadas agora podem ficar temporariamente em Redis por conversa
  - se um novo pedaço chegar dentro da janela curta, o backend combina os trechos antes de chamar o agente
  - o comportamento ficou consistente nos dois caminhos de inbound do WhatsApp
- Go foi instalado localmente na VPS e o gateway agora compila com toolchain real
- Validacao executada:
  - `PYTHONPYCACHEPREFIX=/dev/shm/sdr-pyc python3 -m py_compile ...`
  - `go build ./...` e `go test ./...` em `services/whatsapp-gateway`
- Proximo passo recomendado:
  - fazer smoke real no WhatsApp com uma conversa picotada e anexos de audio/imagem

## 2026-03-20
- Instalei Go localmente na VPS para eliminar a limitacao de toolchain no `sdr`:
  - `go version` agora responde `go1.26.1 linux/amd64`
  - o binario ficou em `~/.local/bin/go` e `~/.local/bin/gofmt`
  - o gateway `services/whatsapp-gateway` compilou com `go build ./...`
  - `go test ./...` no gateway passou
- Proximo passo recomendado:
  - fazer commit/push do gateway multimodal e redeploy da stack `sdr`

## 2026-03-20
- Evolução multimodal e de fluxo humano no `sdr`:
  - a resposta do agente agora pode sair em fragmentos curtos para simular conversa mais natural no WhatsApp
  - a base de conversa continua usando Redis para reter contexto curto entre turnos
  - o inbound ganhou suporte para anexos de `audio` e `image`, com resumo/transcrição/análise no backend
  - o gateway WhatsApp passou a baixar e expor mídia localmente para o backend conseguir ler a URL interna
- Validação executada:
  - `PYTHONPYCACHEPREFIX=/dev/shm/sdr-pyc python3 -m py_compile ...` nos arquivos Python alterados
- Proximo passo recomendado:
  - compilar/testar o gateway Go e fazer um smoke real com audio e imagem no WhatsApp

## 2026-03-20
- Adicionado Redis como cache de contexto por conversa no `sdr`:
  - novo snapshot estruturado com tipo de imovel, valor do bem, prazo, lance e ultima intencao
  - o inbound do WhatsApp grava esse contexto antes e depois da resposta do agente
  - o prompt do agente passa a ler o contexto do Redis quando disponivel
  - o TTL do contexto foi padronizado para 24h via `CONVERSATION_CONTEXT_TTL_SECONDS`
- Validacao executada:
  - compilacao direta dos arquivos Python alterados com `compile()`
- Proximo passo recomendado:
  - testar um fluxo real de WhatsApp para confirmar que o agente para de perder o fio da conversa

## 2026-03-20
- Corrigido o comportamento de perda de contexto no agente de conversa:
  - adicionei memoria estruturada de conversa para guardar tipo de imovel, valor do bem, prazo e lance
  - o prompt agora recebe essa memoria e nao deve recomeçar a qualificacao quando o lead ja informou os dados
  - o roteamento de intencao passou a distinguir imovel e lance em vez de cair sempre em `generic`
  - removi referencias visiveis a VINAC do prompt interno do agente para evitar vazamento de marca antiga
  - aumentei a janela de historico recente para manter mais turnos crús no contexto
- Validacao executada:
  - checagem de sintaxe por `compile()` direto no texto dos arquivos alterados
  - o host local continua sem um Python do backend ou Docker acessivel para rodar `pytest` completo
- Proximo passo recomendado:
  - testar um fluxo real com um lead que informa valor, prazo e lance para confirmar que o agente para de repetir perguntas

## 2026-03-20
- Removidas as referencias visiveis a VINAC da tela de `Knowledge`:
  - a hero agora fala em `laboratório do produto`
  - os botoes de acao usam copy generica de base oficial e laboratorio
  - o painel lateral passou a mostrar `Caso de laboratório: base ativa do produto`
  - as mensagens de sucesso e erro da fila tambem foram neutralizadas
- Validação executada:
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npx tsc --noEmit --incremental false`
- Proximo passo recomendado:
  - se quiser, a proxima passada pode remover nomes internos legados de `vinac` nas rotas e helpers, sem mudar o comportamento

## 2026-03-20
- Ajuste de copy no frontend para alinhar a tela de `Knowledge` com o texto operacional desejado:
  - `CommandBar` agora exibe `Acessos rápidos` com acentuação correta
  - o hero da `Knowledge` recebeu microcopy com acentos corrigidos
  - o painel do produto ativo ganhou um destaque visível com o nome atual selecionado
  - a copy de YouTube/URL foi refinada para mencionar `legenda pública` e `indexação`
- Validação executada:
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npx tsc --noEmit --incremental false`
- Proximo passo recomendado:
  - se quiser mais polimento, podemos continuar refinando a tela de `Knowledge` com os atalhos e cards de laboratório

## 2026-03-20
- Limpeza dos jobs antigos de `Knowledge` concluida:
  - os 3 jobs `queued` criados antes do worker existir foram removidos do banco
  - a UI agora mostra apenas o job novo de YouTube que terminou `completed`
  - isso deixa a fila historica limpa sem afetar o teste validado em producao
- Proximo passo recomendado:
  - seguir com novas ingestoes normalmente; a fila atual esta saudavel

## 2026-03-20
- Descoberto um problema separado no `sdr` que afetava o login do frontend:
  - o container do frontend conseguia resolver `backend:8000`, mas o alvo retornava `ECONNREFUSED`
  - o mesmo container respondeu `200` quando apontado para `sdr_backend:8000`
  - o manifesto da stack foi corrigido para usar `sdr_backend:8000` como URL interna do backend
- O teste real de Knowledge continua valido:
  - um job novo de ingestao de YouTube entrou em `completed`
- Proximo passo recomendado:
  - redeploy da stack `sdr` para aplicar o backend interno correto e revalidar o login do frontend

## 2026-03-20
- Validado em producao o fluxo novo de fila do `sdr`:
  - a stack `sdr` agora sobe com `redis` e um worker Celery dedicado
  - o backend e o worker convergem no mesmo digest do GHCR
  - um job novo de `Knowledge` para o video do YouTube foi enfileirado e saiu de `queued` para `completed`
  - o job de teste terminou com `celery_task_id` preenchido e `result_json` com a fonte indexada
- Estado observado:
  - os jobs antigos que haviam sido criados antes do worker entrar em operacao continuam presos em `queued`
  - o caminho novo, com broker e worker ativos, esta processando corretamente
- Proximo passo recomendado:
  - decidir se os jobs antigos devem ser reencaminhados ou deixados como historico morto

## 2026-03-20
- Corrigido o gargalo de processamento da fila `Knowledge` no `sdr`:
  - a stack de producao passou a incluir `redis` e um `worker` Celery dedicado
  - o backend e o worker agora recebem `REDIS_URL=redis://redis:6379/0`
  - o worker usa a mesma imagem do backend e consome as filas de ingestao e avaliacao
  - sem esse componente, os jobs ficavam eternamente em `queued` mesmo quando a URL era aceita pela API
- Ajustes de documentação:
  - `README.md` raiz menciona a nova peça de infra
  - `deploy/atendente3/README.md` agora descreve explicitamente `redis` e `worker`
  - `docs/PROJECT_CONTEXT.md` passou a registrar a topologia de producao atual
- Validação já executada antes do redeploy:
  - criação do cliente e produto de teste via API funcionou
  - a submissão da URL do YouTube foi aceita e gerou jobs `queued`, confirmando que o problema era a falta do consumidor assíncrono
- Proximo passo recomendado:
  - commit/push/release da stack atualizada e redeploy no Portainer para ativar o worker

## 2026-03-20
- Corrigido o fluxo de ingestao de URL no `Knowledge` para aceitar links de YouTube colados sem `https://`:
  - o backend agora normaliza `www.youtube.com/...`, `youtube.com/...` e `youtu.be/...` para URL completa antes de resolver a fonte
  - o frontend tambem passa a completar o esquema automaticamente e avisa isso na UI
  - isso evita a queda para o caminho de arquivo local, que fazia a acao parecer ignorada quando o usuario colava apenas o link cru
- Validacao executada:
  - `cd backend && python3 -m pytest -q tests/test_knowledge_youtube.py` -> `3 passed`
  - `cd frontend && npx tsc --noEmit --incremental false` -> ok
  - `npm run build` em workspace limpo -> ok
- Proximo passo recomendado:
  - publicar o commit e reaplicar a stack `sdr` no Portainer para puxar o frontend e o backend corrigidos

## 2026-03-20
- Publicada a release `v0.2.0` no GitHub para consolidar a rodada de frontend e knowledge:
  - `main` foi empurrado com o commit `161446b`
  - a release foi criada a partir da tag `v0.2.0`
  - o GitHub Actions do repositório concluiu com `success` para esse commit
- Redeploy da stack `sdr` concluido no Portainer:
  - stack `35` / endpoint `1` reaplicada com `PullImage=true`
  - `frontend`, `backend` e `whatsapp-gateway` receberam novos digests do GHCR
  - smoke publico validado em `https://pulse.orfi.com.br/`, `https://pulse.orfi.com.br/health` e `https://pulse.orfi.com.br/api/auth/providers`
- Proximo passo recomendado:
  - acompanhar o proximo ciclo funcional no `pulse.orfi.com.br` e validar o comportamento real do fluxo de knowledge/WhatsApp sobre os novos containers

## 2026-03-20
- Melhorada a tela de `Knowledge` no frontend para deixar a ingestao de YouTube mais legivel para o operador:
  - badges de `source_type` agora aparecem com rótulos amigaveis
  - a UI avisa que videos do YouTube entram com transcript quando a legenda publica estiver disponivel
  - a tela de ingestao de URL tambem explica os formatos aceitos
- Refinamento adicional na mesma tela:
  - fontes `youtube_video` agora mostram um badge `Transcript` no inventario e nos resultados da busca
  - isso deixa claro visualmente quais fontes vieram do YouTube e podem carregar transcricao
- Validacao executada em workspace limpo em `/home/ilki/tmp/frontend-check`:
  - `npm run typecheck` -> ok
  - `npm run build` -> ok
- Proximo passo recomendado:
  - publicar o ajuste no branch principal e, se necessario, seguir para a tela de `Knowledge` com mais sinais de origem/transcript no inventario

## 2026-03-20
- Melhorado o `Dashboard` operacional do frontend:
  - o `CommandBar` saiu do placeholder e virou um conjunto de atalhos para `Dashboard`, `Knowledge`, `Agent Lab` e `Quality`
  - o layout interno agora exibe essa barra no topo das telas autenticadas
  - o `Dashboard` ganhou estados vazios reutilizando `EmptyState` para jobs recentes, agentes sem dados, ultima avaliacao e conversas recentes
- Validacao executada em workspace limpo em `/home/ilki/tmp/frontend-check`:
  - `npm run typecheck` -> ok
  - `npm run build` -> ok
- Proximo passo recomendado:
  - seguir o mesmo padrao de estados vazios e atalhos nas outras telas do app, especialmente `settings` e `conversations`

## 2026-03-20
- Continuacao do acabamento do frontend:
  - `Conversations` agora usa `EmptyState` quando a lista filtrada fica vazia
  - `Settings` ganhou `EmptyState` para o caso de sessao ausente e um campo extra de escopo operacional
- Validacao executada em workspace limpo em `/home/ilki/tmp/frontend-check`:
  - `npm run typecheck` -> ok
  - `npm run build` -> ok
- Proximo passo recomendado:
  - passar o mesmo tratamento de estados vazios e linguagem operacional para telas restantes que ainda estejam muito espartanas

## 2026-03-20
- Padronizacao visual mais ampla do frontend:
  - criado `SidebarNav` com estado ativo real baseado na rota atual
  - o layout autenticado passou a usar esse sidebar em vez do nav estatico
  - `Clients`, `Products`, `Sales` e `Commissions` ganharam cabeçalhos mais descritivos e `EmptyState` nos casos sem dados
- Validacao executada em workspace limpo em `/home/ilki/tmp/frontend-check`:
  - `npm run typecheck` -> ok
  - `npm run build` -> ok
- Proximo passo recomendado:
  - repetir o mesmo nivel de acabamento nas telas de `Agents` e `Personas`, que ainda sao as mais densas do app

## 2026-03-20
- Ultimo bloco de padronizacao do frontend nesta rodada:
  - `Personas` recebeu cabeçalho mais claro, contadores de itens e `EmptyState` para listas vazias
  - o copy das telas foi uniformizado para usar linguagem operacional mais consistente
- `Agents` tambem foi trazido para o mesmo padrao apos corrigir a ownership do arquivo e aplicar a versao validada
- Validacao executada em workspace limpo em `/home/ilki/tmp/frontend-check`:
  - `npm run typecheck` -> ok
  - `npm run build` -> ok
- Proximo passo recomendado:
  - seguir daqui apenas com ajustes funcionais ou uma ultima passada de polish se algum fluxo ainda soar inconsistente

## 2026-03-19
- Implementada a ingestao de transcricao de videos YouTube na base de conhecimento:
  - o backend agora extrai transcript quando disponivel e inclui esse texto no `content` indexado para RAG
  - o caminho continua com fallback para o comportamento anterior via oEmbed quando o transcript nao existe ou nao pode ser obtido
  - adicionado helper de parsing de video ID para URLs `watch`, `youtu.be`, `shorts`, `embed` e `live`
- Dependencias atualizadas:
  - adicionado `youtube-transcript-api` em `backend/requirements.txt`
- Cobertura adicionada:
  - `backend/tests/test_knowledge_youtube.py`
- Validacao executada:
  - `PYTHONPYCACHEPREFIX=/dev/shm/sdr-pyc python3 -m py_compile backend/app/services/knowledge.py backend/tests/test_knowledge_youtube.py` -> ok
  - `cd backend && python3 -m pytest -q tests/test_knowledge_youtube.py` -> `2 passed`
- Proximo passo recomendado:
  - publicar o commit e, se desejado, ajustar a interface de knowledge para deixar claro quando uma fonte YouTube foi indexada com transcript completo

## 2026-03-19
- Ajustado o contexto do deploy para refletir o nome atual da stack em producao:
  - a stack deve ser referida como `sdr`
  - `atendente3` ficou como nome historico da pasta `deploy/atendente3` e de alguns recursos legados
- Proximo passo recomendado:
  - continuar usando `sdr` nas proximas atualizacoes de Portainer, documentação e releases, evitando criar mais referencias novas a `atendente3`

## 2026-03-19
- Corrigida a compatibilidade do frontend com a rota legacy `/api/auth/providers`:
  - adicionado handler Next.js em `frontend/app/api/auth/providers/route.ts`
  - a resposta expõe um provider `credentials` simples, suficiente para smoke checks e contratos antigos
- Validacao executada:
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run typecheck` -> ok
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npx next build --webpack` -> ok
- Observacao de ambiente:
  - o build Turbopack no checkout principal esbarra em artefatos `.next` e `tsconfig.tsbuildinfo` root-owned; a validacao ficou consistente usando uma copia efemera em `/dev/shm` com Webpack
- Proximo passo recomendado:
  - confirmar em producao se `/api/auth/providers` volta a responder `200` no rollout seguinte da stack `sdr`

## 2026-03-19
- Reescrito o `README.md` raiz para refletir o estado atual do `sdr` como `Orfi Pulse`.
- O README agora descreve a plataforma interna de operacao comercial para consorcios/Turn2C, os modulos do menu, o fluxo recomendado de uso, a autenticacao multi-tenant, o caminho administrativo de reset e o deploy atual com `sdr_backend` e migrations no boot.
- Proximo passo recomendado:
  - manter README, `PROJECT_CONTEXT.md` e `WORKLOG.md` alinhados sempre que o escopo do produto ou a estrategia de deploy mudar.

## 2026-03-19
- Validação pública da stack `sdr` mostrou que o hub novo de consórcios ja esta ativo em `https://pulse.orfi.com.br/consorcios` com HTTP `200`.
- As subrotas novas ainda nao estao publicadas na stack em producao:
  - `/consorcios/playbook` -> `404`
  - `/consorcios/knowledge` -> `404`
  - `/consorcios/inbox` -> `404`
  - `/health` -> `404`
- O workflow do GitHub Actions para o commit `87bc7e5` concluiu com `success`, entao o bloqueio agora e de redeploy/stack e nao de build.
- Tentativa de autenticacao automatica no Portainer para atualizar a stack `sdr` nao passou com a credencial disponivel nesta sessao.
- Proximo passo:
  - atualizar a stack `sdr` no Portainer para puxar as imagens novas e reaplicar as rotas
  - repetir o smoke em `/consorcios/playbook`, `/consorcios/knowledge`, `/consorcios/inbox` e `/health`

## 2026-03-10
- Clonado o repositorio `sdr` em `/home/ilki/sdr`.
- Criados `docs/PROJECT_CONTEXT.md` e `docs/WORKLOG.md` para persistencia de contexto local.
- Portado para este repositório o material inicial de deploy da stack, hoje tratada em producao como `sdr`: `deploy/atendente3/stack.yml`, `.env.example` e `README.md`.
- Adicionados Dockerfiles e `.dockerignore` para `backend` e `frontend`.
- Ajustado o backend para aceitar `DATABASE_URL` generico com compatibilidade inicial para Postgres via `asyncpg`/`psycopg`.
- Adicionado workflow GitHub Actions para publicar imagens `backend` e `frontend` no GHCR do proprio repositório `sdr`.
- Atualizado o `README.md` raiz para apontar para o deploy versionado da stack `sdr`.
- Corrigido o manifesto de deploy para usar as variaveis e portas realmente esperadas pelo código versionado (`DATABASE_URL`, `OPENAI_MODEL`, `BACKEND_INTERNAL_URL`, `SESSION_SECRET` e frontend em `3000`).
- Adicionado `whatsapp-service` versionado ao repositório, com Dockerfile, API mínima de relay para o backend e log local em `/data/events.jsonl`.
- Adicionado ao backend o webhook público `/api/v1/whatsapp/webhook` para processar mensagens inbound, manter lead/conversa e devolver a resposta do agente.
- Atualizados workflow GHCR, stack e documentação para usar a imagem `ghcr.io/ilki70/sdr/whatsapp-service:latest`.

## 2026-03-11
- Retomada a revisão das mudanças locais do `sdr` antes de qualquer alinhamento da stack `sdr` na VPS.
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
- Substituida a definicao persistida da stack `sdr` no Portainer pela versao alinhada do repositório, mantendo o uso das imagens locais para este rollout.
- Redeployada a stack `sdr` no Swarm com os servicos `postgres`, `backend`, `frontend`, `db-admin` e `whatsapp-service`.
- Validacoes apos rollout:
  - todos os servicos ficaram `1/1`
  - `frontend` publico respondeu HTTP 200 em `https://pulse.orfi.com.br`
  - `db-admin` respondeu HTTP 403 fora da allowlist esperada
  - `backend` e `whatsapp-service` subiram sem erro nos logs de bootstrap
  - `whatsapp-service` respondeu `{\"status\":\"ok\"...}` no endpoint `/health`
  - `backend`, `postgres` e `whatsapp-service` ficaram isolados na rede `sdr_internal`

## Current Status
- Repositorio local preparado para evoluir o deploy do `sdr`.
- A stack `sdr` agora esta descrita no repositório e `backend`/`frontend`/`whatsapp-service` podem ser gerados por ele.
- O fluxo WhatsApp agora tem uma implementacao versionada ponta a ponta, ainda com contrato minimo e sem adaptador para um provedor real.
- O manifesto versionado do deploy ficou mais seguro para Swarm compartilhado e esta pronto para comparação final com a stack antiga do Portainer.
- A producao da stack `sdr` foi alinhada com essa linha versionada usando imagens locais geradas a partir do repo.
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
- O workflow GitHub Actions `Build atendente3 images` do commit `73c6774` concluiu com sucesso para `backend`, `frontend` e `whatsapp-gateway`.
- Ainda nao foi feito rollout nem smoke end-to-end em stack real.

## Next Recommended Step
- Fazer o build das imagens e o rollout da stack real:
  - backend/frontend/gateway atualizados na `atendente3`
  - usar as imagens publicadas pela CI a partir do commit `73c6774`
  - depois testar QR real e um roundtrip inbound/outbound de WhatsApp

## 2026-03-19
- Iniciado o reposicionamento do `sdr` para uso interno da equipe em consorcios/Turn2C.
- Direcao definida:
  - a Turn2C sera tratada como backoffice de fechamento
  - a operacao comercial principal fica fora da plataforma, com agentes de IA, RAG e acompanhamento de conversas
  - o MVP nao vai depender de automacao pesada de tela nem de API da Turn2C
- Contexto duravel atualizado em [docs/PROJECT_CONTEXT.md](/home/ilki/sdr/docs/PROJECT_CONTEXT.md).
- Criado o plano de adaptacao em [docs/turn2c-adaptation-plan.md](/home/ilki/sdr/docs/turn2c-adaptation-plan.md).

## 2026-03-19
- Adicionado reset administrativo de usuario no `sdr` para recuperar acesso sem depender de login valido:
  - backend ganhou o endpoint `POST /api/v1/auth/admin/reset-user-password`
  - frontend ganhou proxy `POST /api/auth/admin/reset-user-password`
  - o reset aceita chave de recuperacao via header `X-Admin-Reset-Key` ou, quando inexistente, exige contexto autenticado `owner/admin`
  - o fluxo preserva tenant e membership, atualizando apenas a senha e criando vinculo se faltar
- Adicionado script reutilizavel em `backend/scripts/reset_user_password.py` para operacao assistida por tenant/email/senha.
- O deploy versionado passou a expor `ADMIN_RESET_SECRET` como variavel de recuperacao.
- Proximo passo:
  - publicar a nova imagem, ligar uma chave temporaria de recuperacao no Portainer e usar o reset para a conta `ilki70@gmail.com`

## 2026-03-19
- Recuperacao concluida no `sdr`:
  - stack `sdr` foi ajustada no Portainer para usar `sdr_backend` no `BACKEND_INTERNAL_URL`
  - backend passou a subir com `alembic upgrade head && uvicorn ...`, criando o schema automaticamente no boot
  - `SESSION_SECRET`, `WHATSAPP_GATEWAY_SECRET` e `ADMIN_RESET_SECRET` foram repassados via `Env` do stack para evitar defaults invalidos
  - reset administrativo da conta `ilki70@gmail.com` em `tenant-lab` foi executado com sucesso
  - smoke final ok em `/api/auth/login`, `/api/auth/session`, `/api/proxy/dashboard/overview` e `/health`
- Proximo passo:
  - se precisar, adicionar uma tela interna de admin para executar resets sem curl
- Principais lacunas mapeadas:
  - configurador operacional de agente para consorcios
  - knowledge studio com docs, URLs e YouTube organizados por tema/agente
  - inbox/control room com takeover humano e notas
  - quality persistente com foco em compliance e conversao
- Proximo passo recomendado:
  - implementar a primeira fatia do "consorcios studio" no frontend e expandir os schemas/backend para playbooks de agente e knowledge organizado

## 2026-03-15
- Tentado rollout da nova stack `atendente3` pelo Portainer usando as imagens publicadas pela CI em `ghcr.io/ilki70/sdr/{backend,frontend,whatsapp-gateway}:latest`.
- A atualizacao de stack foi aceita pelo Portainer e os servicos chegaram a ser recriados com a nova composicao (`backend`, `frontend`, `whatsapp-gateway`, `postgres`, `db-admin`).
- O rollout nao estabilizou:
  - os workers do Swarm rejeitaram `backend`, `frontend` e `whatsapp-gateway` com erro `No such image` para as imagens `ghcr.io/ilki70/sdr/*:latest`
  - o frontend publico em `https://pulse.orfi.com.br` caiu em `404 page not found` enquanto os servicos novos estavam rejeitados
- Acao corretiva executada no mesmo turno:
  - rollback imediato da stack `atendente3` para o compose anterior baseado em `atendente3/backend:latest`, `atendente3/frontend:latest` e `atendente3/whatsapp-service:latest`
  - validado via Portainer que todos os servicos antigos voltaram para `running`
  - smoke publico restaurado com `200` em `/` e `/login` em `https://pulse.orfi.com.br`

## Current Status
- A producao foi restaurada e o `pulse.orfi.com.br` voltou a responder normalmente.
- A implementacao nova com `whatsapp-gateway` continua pronta no codigo e validada localmente/na CI.
- O bloqueio real para deploy agora e de distribuicao de imagem no ambiente Swarm:
  - ou as imagens do GHCR estao privadas/inacessiveis para os workers
  - ou o cluster nao tem autenticacao/configuracao para pull dessas imagens
- Confirmado com `curl -i 'https://ghcr.io/token?service=ghcr.io&scope=repository:ilki70/sdr/backend:pull'` que o GHCR exige autenticao (`401 Unauthorized`), o que justifica a rejeicao dos novos containers.
- Diagnostico refinado:
  - o PAT fornecido pelo usuario autentica na API GitHub, mas possui apenas escopos `repo, workflow`
  - ao tentar ler manifests do GHCR para `ghcr.io/ilki70/sdr/{backend,frontend,whatsapp-gateway}`, a resposta foi `403 requested access to the resource is denied`
  - foi testado cadastrar o GHCR no Portainer com esse PAT, mas o swarm continuou sem conseguir puxar as imagens
  - o registry temporario foi removido do Portainer para nao deixar credencial sem efeito persistida no ambiente
  - mesmo apos o repositorio `https://github.com/ilki70/sdr` ficar publico, o GHCR continuou exigindo autenticacao para os packages, indicando que a visibilidade do pacote ainda nao esta publica

## Next Recommended Step
- Antes de um novo rollout:
  - gerar um PAT com `read:packages` para pull, ou `write:packages`/`delete:packages` se a intencao for administrar/publicar os packages
  - ou abrir manualmente cada package do GHCR (`backend`, `frontend`, `whatsapp-gateway`) e mudar a visibilidade para `public`
  - alternativamente, tornar os packages do GHCR publicos com uma credencial que tenha permissao de pacote
  - so depois reaplicar a stack nova com `whatsapp-gateway` e validar QR pairing real

## 2026-03-15
- Concluido o destravamento do deploy via GHCR:
  - os tres packages `backend`, `frontend` e `whatsapp-gateway` passaram a responder anonimamente no GHCR com manifest `200`
  - a stack `atendente3` foi reaplicada no Portainer usando:
    - `ghcr.io/ilki70/sdr/backend:latest`
    - `ghcr.io/ilki70/sdr/frontend:latest`
    - `ghcr.io/ilki70/sdr/whatsapp-gateway:latest`
- Estado final do Swarm:
  - `atendente3_backend` em `running` por digest `sha256:69068d2bfd63b786f456bc2e565ac0fa81df61d6804b6ef111e1967e37009d49`
  - `atendente3_frontend` em `running` por digest `sha256:c3c9a631900eaba7048f951c8278907f81472c8056057b9f2a152cf5daf3e56f`
  - `atendente3_whatsapp-gateway` em `running` por digest `sha256:9c2a5f6fd0ed6f17a30fe425b9ed9093bbf1248a1add2530207191e77efab41a`
- Validacao publica:
  - `https://pulse.orfi.com.br/` -> `200`
  - `https://pulse.orfi.com.br/login` -> `200`
- Observacao de validacao:
  - `https://pulse.orfi.com.br/api/auth/providers` retornou `404` nesta build nova; como `/` e `/login` respondem com a aplicacao Next correta, isso parece ser mudanca/regressao especifica da rota de auth e precisa ser revisada separadamente

## Current Status
- A stack nova com `whatsapp-gateway` esta publicada em producao.
- O frontend e o backend novos subiram a partir das imagens do GHCR.
- O ponto funcional ainda nao validado em producao e o fluxo real de QR pairing/pareamento no dashboard.
- Existe um possivel ajuste pendente na rota `/api/auth/providers`, que esta respondendo `404` nesta release.

## Next Recommended Step
- Validar no app:
  - abrir o dashboard autenticado
  - gerar o QR code
  - testar pareamento real do WhatsApp
  - checar se a auth esperada do frontend realmente mudou de contrato ou se `/api/auth/providers` regrediu e precisa de correcao
