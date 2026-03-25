# Worklog

## 2026-03-24
- `sdr`: limpeza final, commit, push e deploy do runtime novo com `langgraph` foram concluídos.
- O que mudou nesta passada:
  - removi o caminho morto de `Rasa` do codigo ativo, configs locais e `docker-compose.yml`
  - mantive o repositorio coerente com `langgraph` como unico caminho recomendado para o runtime novo
  - commit publicado: `0f734a9` `feat: migrate sdr runtime to langgraph`
  - backend buildado no Portainer como `sdr-backend:prod-20260324-0f734a9`
  - stack `sdr` reaplicada mantendo `FRONTEND_IMAGE=sdr-frontend:prod-20260324-04110b8`
- Validacao executada:
  - `python3 -m py_compile ...` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` -> `15 passed`
  - services vivos: `sdr_backend` convergiu para `sdr-backend:prod-20260324-0f734a9`
  - `https://pulse.orfi.com.br/health` -> `ok`
- Status atual:
  - `main` no GitHub foi atualizado ate `0f734a9`
  - deploy produtivo do backend novo ja esta ativo
- Proximo passo recomendado:
  - rodar uma bateria local de simulacoes espelhando conversas reais para medir os desvios finais do comportamento comercial

## 2026-03-24
- `sdr`: o `langgraph_runtime` agora segura o estado de proposta/simulacao em andamento sem regredir para qualificacao.
- O que mudou nesta passada:
  - entrou leitura de `proposal_commitment_state` a partir do historico recente e do `pipeline_status`
  - quando a SDR ja prometeu simulacao ou proposta, o runtime passa a responder em modo `proposal_in_progress`
  - nesse estado, se faltar cadastro, ele pede apenas o dado cadastral faltante; se nao faltar, ele retoma a simulacao sem reiniciar perguntas
  - corrigi tambem o caminho compilado do graph para usar o `RuntimeContext` atual em vez de funcoes antigas
- Validacao executada:
  - `python3 -m py_compile backend/app/services/langgraph_runtime.py backend/tests/test_langgraph_runtime.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py` -> `10 passed`
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` -> `5 passed`
- Status atual:
  - o runtime novo ja consegue manter qualificacao, objecoes, handoff e etapa de simulacao/proposta sem reiniciar a conversa quando o compromisso ja existe
- Proximo passo recomendado:
  - montar simulacoes locais mais proximas dos casos reais reportados para medir onde o runtime novo ainda diverge do comportamento comercial esperado

## 2026-03-24
- `sdr`: enriqueci o `langgraph_runtime` com confirmacao curta de dados novos e tratamento deterministico de objecoes sem perder o fluxo.
- O que mudou nesta passada:
  - o runtime agora confirma apenas os dados novos relevantes antes da proxima pergunta, sem repetir o resumo inteiro
  - entrou tratamento deterministico para objecoes comuns como taxa, confianca, comparacao com financiamento, lance e prazo
  - as objecoes agora respondem o ponto do lead e em seguida retomam o slot faltante correto
  - ajustei a ordem do fluxo para `lead_name` nao travar a qualificacao comercial quando o lead ja respondeu bem/objetivo/valor/prazo
  - corrigi o gating de nome para evitar falso positivo em frases como `quero um imovel`
- Validacao executada:
  - `python3 -m py_compile backend/app/services/langgraph_runtime.py backend/tests/test_langgraph_runtime.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py` -> `8 passed`
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` -> `5 passed`
- Status atual:
  - o runtime novo ja cobre qualificacao, gate cadastral, handoff, confirmacao curta e objecoes basicas, reaproveitando o snapshot e a estrutura atual
- Proximo passo recomendado:
  - consolidar transicoes de proposta e compromisso de simulacao usando o historico e o `pipeline_status`, para reduzir regressao depois que a SDR promete avancar

## 2026-03-24
- `sdr`: refatorei o `langgraph_runtime` para reaproveitar melhor a estrutura e os dados que o projeto ja mantem.
- O que mudou nesta passada:
  - o runtime agora le `ConversationContextSnapshot` como fonte primaria quando existir
  - passei a reaproveitar `extracted_slots`, `current_question_slot`, `last_confirmed_slot`, `summary` e `memory_notes`
  - o runtime tambem passou a respeitar `required_profile_fields_missing` e `pipeline_status` vindos do metadata atual
  - a logica de follow-up ficou alinhada ao slot faltante real, usando primeiro o estado persistido e so depois heuristica local
- Validacao executada:
  - `python3 -m py_compile backend/app/services/langgraph_runtime.py backend/tests/test_langgraph_runtime.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py` -> `6 passed`
- Status atual:
  - o `langgraph_runtime` deixou de depender so de parser ad hoc e passou a orquestrar melhor a memoria e as pendencias ja existentes no projeto
- Proximo passo recomendado:
  - puxar agora objecoes e confirmacoes do fluxo legado para dentro do runtime novo, reaproveitando o mesmo snapshot e sem duplicar regras

## 2026-03-24
- `sdr`: levei o runtime novo com `langgraph` tambem para os dois inbounds de WhatsApp e centralizei a escolha do motor em um roteador unico.
- O que mudou nesta passada:
  - `backend/app/services/runtime_router.py` passou a concentrar a escolha entre `langgraph`, `rasa` e runtime legado
  - `backend/app/services/langgraph_runtime.py` agora tambem aproveita o snapshot real de `conversation_context` para inicializar slots
  - `backend/app/services/whatsapp.py` e `backend/app/services/whatsapp_gateway.py` agora usam o mesmo roteador do `agent-lab`
  - o handoff vindo do runtime novo ja projeta `pipeline_status=handoff` e `status=waiting_human` nos fluxos de WhatsApp
  - corrigi compatibilidade local Python 3.9 em `backend/app/schemas/whatsapp.py`
  - ampliei a regressao para cobrir `agent-lab` e `whatsapp_gateway` no caminho novo
- Validacao executada:
  - `python3 -m py_compile backend/app/api/v1/messages/routes.py backend/app/schemas/whatsapp.py backend/app/services/langgraph_runtime.py backend/app/services/runtime_router.py backend/app/services/whatsapp.py backend/app/services/whatsapp_gateway.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` -> `8 passed`
- Status atual:
  - `agent-lab`, `whatsapp-service` e `whatsapp-gateway` ja conseguem compartilhar o mesmo motor novo por feature flag
- Proximo passo recomendado:
  - enriquecer o `langgraph_runtime` com objecoes, confirmacoes e transicoes de proposta sem depender mais do runtime legado

## 2026-03-24
- `sdr`: reorientei o plano de migracao para um runtime interno com `langgraph`, removendo Rasa do caminho principal por risco de licenca.
- O que mudou nesta passada:
  - criei `backend/app/services/langgraph_runtime.py` com um fluxo stateful inicial para qualificar lead, pedir cadastro faltante e acionar `handoff`
  - o `agent-lab` agora prefere `LANGGRAPH_RUNTIME_ENABLED=true` e usa o novo runtime antes de tentar o caminho de Rasa
  - adicionei `LANGGRAPH_RUNTIME_ENABLED` em `backend/app/core/config.py` e `backend/.env.example`
  - alinhei `backend/requirements.txt` para incluir `langgraph`
  - documentei a nova direcao em `docs/langgraph-runtime-plan.md` e atualizei o `README.md`
  - adicionei regressao cobrindo fluxo do runtime e integracao do `agent-lab`
- Validacao executada:
  - `python3 -m py_compile backend/app/services/langgraph_runtime.py backend/app/api/v1/messages/routes.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py` -> `5 passed`
- Status atual:
  - o caminho recomendado do projeto passou a ser `langgraph` library dentro do backend atual
  - o suporte anterior a `rasa_runtime` ficou apenas como trilha secundaria, nao como direcao principal
- Proximo passo recomendado:
  - expandir o `langgraph_runtime` para usar snapshot real de contexto da conversa e depois plugar o mesmo runtime no WhatsApp

## 2026-03-24
- `sdr`: deixei um caminho operacional minimo para subir o `rasa-sdr` localmente e ligar o `agent-lab` ao runtime novo.
- O que mudou nesta passada:
  - o `docker-compose.yml` ganhou os services `rasa-sdr` e `rasa-actions`
  - criei um action server minimo em `rasa-sdr/actions/` para devolver `slot_projection`, `follow_up_suggestion` e `handoff_requested`
  - criei o bootstrap `rasa-sdr/scripts/start-rasa.sh`, que treina no boot e sobe o REST webhook
  - o parser de `backend/app/services/rasa_runtime.py` agora aceita tambem o payload `custom.metadata` do REST channel do Rasa
  - alinhei `backend/.env.example`, `README.md` e `rasa-sdr/README.md` com as variaveis e passos de execucao local
- Validacao executada:
  - `python3 -m py_compile backend/app/services/rasa_runtime.py backend/tests/test_rasa_runtime.py rasa-sdr/actions/actions.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_rasa_runtime.py` -> `3 passed`
  - `docker compose config` -> ok
- Limitacoes encontradas:
  - este shell nao tem `RASA_LICENSE`/`RASA_PRO_LICENSE`, entao nao foi possivel subir o `rasa-sdr`
  - este shell tambem nao tem permissao no `docker.sock`, entao o build local de `rasa-actions` falhou antes do smoke completo
- Proximo passo recomendado:
  - rodar `docker compose up -d rasa-actions rasa-sdr` em um shell com licenca Rasa e acesso Docker, depois testar o `agent-lab` com `RASA_RUNTIME_ENABLED=true`

## 2026-03-24
- `sdr`: plugei o `agent-lab` ao runtime novo de Rasa por feature flag, sem mexer no WhatsApp.
- O que mudou nesta passada:
  - `backend/app/api/v1/messages/routes.py` agora consegue alternar entre o runtime antigo e o `rasa_runtime`
  - quando `RASA_RUNTIME_ENABLED=true`, o `agent-lab` envia a mensagem para o Rasa usando `conversation_id` como `sender`
  - a resposta do Rasa passa a projetar slots basicos em `Lead` (`name`, `phone`, `cpf`) e a carregar `rasa_slot_projection` no metadata
  - o fluxo de simulacao/stream do lab agora respeita `handoff_requested` vindo do Rasa
  - adicionei testes cobrindo projecao de slots e roteamento por feature flag
  - ajustei `backend/app/core/security.py` com `from __future__ import annotations` para manter compatibilidade de testes neste host com Python 3.9
- Validacao executada:
  - `python3 -m py_compile backend/app/core/security.py backend/app/api/v1/messages/routes.py backend/tests/test_messages_rasa_runtime.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_rasa_runtime.py backend/tests/test_messages_rasa_runtime.py` -> `4 passed`
- Proximo passo recomendado:
  - subir um `rasa-sdr` local e testar o `agent-lab` com `RASA_RUNTIME_ENABLED=true` antes de tocar no canal real

## 2026-03-24
- `sdr`: comecei a materializar a migracao para `Rasa CALM` dentro do repositorio.
- O que mudou nesta passada:
  - criei o esqueleto `rasa-sdr/` com `config.yml`, `domain.yml`, `nlu.yml`, `credentials.yml`, `endpoints.yml` e flows iniciais de qualificacao, cadastro, proposta e handoff
  - adicionei configuracoes de runtime Rasa em `backend/app/core/config.py`
  - criei o adaptador `backend/app/services/rasa_runtime.py` com contrato para enviar mensagens ao Rasa e interpretar a resposta
  - adicionei regressao cobrindo payload de envio e parsing da resposta em `backend/tests/test_rasa_runtime.py`
- Validacao executada:
  - `python3 -m py_compile backend/app/core/config.py backend/app/services/rasa_runtime.py backend/tests/test_rasa_runtime.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_rasa_runtime.py` -> `2 passed`
- Proximo passo recomendado:
  - plugar o `agent-lab` ao `rasa_runtime` por feature flag antes de substituir o runtime antigo no WhatsApp

## 2026-03-24
- `sdr`: consolidei a recomendacao de trocar o motor atual de conversa por `Rasa CALM`.
- O que mudou nesta passada:
  - documentei um plano de migracao em `docs/rasa-calm-migration-plan.md`
  - a proposta preserva CRM, WhatsApp, inbox e banco atual, trocando apenas o runtime de dialogo
  - defini arquitetura alvo, slots, flows centrais, adaptador backend->Rasa e rollout em fases
- Status atual:
  - a recomendacao tecnica do projeto passou a ser `Rasa CALM` como motor principal de dialogo
- Proximo passo recomendado:
  - criar o esqueleto do servico `rasa-sdr` e plugar primeiro no `agent-lab` antes de levar ao WhatsApp

## 2026-03-24
- `sdr`: commit e rollout da passada de confiabilidade/qualificacao foram concluídos no ambiente da stack `sdr`.
- O que mudou nesta passada:
  - commit local `d44fd4d` com os ajustes de abertura, captura de telefone, memoria curta e proximos passos da SDR
  - build remoto da imagem `sdr-backend:prod-20260324-d44fd4d` via proxy Docker do Portainer
  - stack `sdr` reaplicada com `BACKEND_IMAGE=sdr-backend:prod-20260324-d44fd4d` e `FRONTEND_IMAGE=sdr-frontend:prod-20260324-04110b8`
  - o primeiro task do backend foi rejeitado por timing de disponibilidade da imagem (`No such image`), mas a reaplicacao seguinte convergiu limpa
- Validacao executada:
  - `https://pulse.orfi.com.br/health` -> `ok`
  - service `sdr_backend` -> imagem `sdr-backend:prod-20260324-d44fd4d`, `UpdateStatus={}`
- Observacao operacional:
  - o `push` para `origin/main` segue bloqueado neste shell por falta de credencial GitHub HTTPS (`could not read Username for 'https://github.com'`)
- Proximo passo recomendado:
  - empurrar o commit `d44fd4d` para o GitHub a partir de um shell com credencial configurada e validar manualmente um fluxo real de lead ja qualificado

## 2026-03-24
- `sdr`: rodei uma bateria local de simulacoes do atendimento com foco em falhas de qualificacao e corrigi novas inconsistencias estruturais.
- O que mudou nesta passada:
  - montei um harness local em Python para simular conversas sem depender do modelo remoto e inspecionar memoria curta, abertura fixa e `follow_up_suggestion`
  - corrigi a perda de `asset_value` quando a mesma mensagem traz valor e prazo juntos, como `quero uma casa de 500mil em 180 meses`
  - corrigi o caso em que `500mil em 180 meses` podia perder o valor do bem por falta de tipo de ativo na mesma frase
  - corrigi o falso positivo em que `quero uma casa em 180 meses` podia transformar o prazo em `asset_value`
  - corrigi a limpeza do `current_question_slot` quando o lead responde mais de um slot na mesma mensagem
  - refinei o `follow_up_suggestion` para pedir exatamente o dado faltante e para nao mencionar `lance` quando o lead ainda nao informou lance
- Simulacoes verificadas:
  - lead qualificado sem lance -> passou a sugerir simulacao com valor do bem e prazo, sem inventar lance
  - proposta bloqueada por cadastro incompleto -> continuou pedindo apenas `CPF`
  - `500mil em 180 meses` -> passou a pedir o bem faltante
  - `quero uma casa em 180 meses` -> passou a pedir a faixa de valor faltante
- Validacao executada:
  - `python3 -m py_compile backend/app/services/conversation_context.py backend/app/agents/nodes.py backend/tests/test_conversation_context.py backend/tests/test_agent_memory.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_lead_capture.py backend/tests/test_conversation_context.py backend/tests/test_agent_memory.py` -> `28 passed`
- Proximo passo recomendado:
  - fazer uma proxima bateria local cobrindo objecoes comerciais e transicao para `handoff` humano para reduzir risco de regressao fora da qualificacao

## 2026-03-24
- `sdr`: revi o fluxo da SDR com foco em confiabilidade operacional e corrigi tres pontos que podiam desalinhar a conversa.
- O que mudou nesta passada:
  - a primeira resposta fixa agora so entra quando a mensagem inicial realmente e uma abertura sem sinal util; se o lead ja chega com bem, valor, prazo, lance ou intencao, a SDR responde em cima desses dados
  - a captura de lead passou a aceitar telefone quando o lead responde apenas com o numero, sem depender de palavras como `telefone` ou `whatsapp`
  - a memoria curta passou a aceitar nome completo com ate 6 palavras, alinhando o parser de contexto com a captura operacional do lead e reduzindo recaptura indevida
  - o fallback de contexto no `compose_reply()` agora inclui a mensagem corrente ao montar o snapshot, evitando prompt defasado no primeiro turno do Agent Lab
- Validacao executada:
  - `python3 -m py_compile backend/app/services/lead_capture.py backend/app/services/conversation_context.py backend/app/agents/nodes.py backend/tests/test_lead_capture.py backend/tests/test_conversation_context.py backend/tests/test_agent_memory.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_lead_capture.py backend/tests/test_conversation_context.py backend/tests/test_agent_memory.py` -> `21 passed`
- Proximo passo recomendado:
  - validar manualmente dois cenarios reais: primeiro lead que ja chega com dados completos e segundo lead que responde apenas com telefone para fechar cadastro

## 2026-03-24
- `sdr`: corrigi a leitura de perfil desatualizado do lead durante a propria rodada de resposta do agente.
- O que mudou nesta passada:
  - `AgentState` passou a carregar `lead_profile` para que o runtime use o lead ja atualizado da transacao corrente
  - `compose_reply()` agora prefere o `lead_profile` presente no estado em vez de abrir uma nova sessao e reler um registro possivelmente antigo
  - os fluxos de `agent-lab`, `whatsapp-service` e `whatsapp-gateway` passaram a injetar o `lead` atualizado no estado antes de chamar o agente
  - entrou regressao garantindo que a resposta usa o telefone ja capturado no estado e nao tenta reler o lead no banco durante a mesma rodada
- Validacao executada:
  - `python3 -m py_compile backend/app/agents/state.py backend/app/agents/nodes.py backend/app/api/v1/messages/routes.py backend/app/services/whatsapp.py backend/app/services/whatsapp_gateway.py backend/tests/test_agent_memory.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q tests/test_lead_capture.py tests/test_conversation_context.py tests/test_agent_memory.py` -> `18 passed`
- Proximo passo recomendado:
  - publicar o backend novo e repetir o fluxo em que o lead informa telefone e depois lance para confirmar que o agente nao volta a pedir telefone

## 2026-03-24
- `sdr`: corrigi uma perda objetiva de contexto na conversa quando nome, CPF, telefone, valor do bem e lance vinham na mesma troca.
- O que mudou nesta passada:
  - `lead_capture` passou a extrair `nome completo` mesmo em mensagens com numeros e tambem passou a capturar `telefone` diretamente do texto
  - a memoria curta deixou de confundir `valor do bem` com `lance` quando os dois aparecem na mesma mensagem
  - o parser de nome da memoria curta foi alinhado com o parser operacional do lead para nao perder `Ilki Amaro Junior` em mensagens com CPF
  - entrou regressao cobrindo exatamente o padrao de simulacao com `500mil` + `180 meses` + `100mil` + `nome` + `CPF`
- Validacao executada:
  - `python3 -m py_compile backend/app/services/lead_capture.py backend/app/services/conversation_context.py backend/tests/test_lead_capture.py backend/tests/test_conversation_context.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q tests/test_lead_capture.py tests/test_conversation_context.py` -> `10 passed`
- Proximo passo recomendado:
  - publicar o backend novo na stack `sdr` e repetir o fluxo do Agent Lab para confirmar que a agente nao volta a pedir nome ou telefone depois do cadastro ja informado

## 2026-03-24
- `sdr`: fechei o pacote de captura de lead + autoaprendizado com commit local e rollout direto no Swarm.
- O que mudou nesta passada:
  - commit local `04110b8` com as mudancas de captura obrigatoria de lead, handoff humano, memoria e historico/reversao de melhorias no `Training`
  - backend e frontend foram buildados no Docker proxy do Portainer com as tags `sdr-backend:prod-20260324-04110b8` e `sdr-frontend:prod-20260324-04110b8`
  - a stack `sdr` foi reaplicada com as imagens novas e ambos os services convergiram com `update completed`
  - executei `alembic upgrade head` dentro do container novo do backend apos o rollout
- Validacao executada:
  - `python3 -m py_compile ...` dos arquivos backend alterados -> ok
  - `npm run build` no frontend com Node 20 -> ok
  - `npm run typecheck` com Node 20 falhou por artefato gerado em `.next/types/validator.ts` apontando para `./routes.js`
  - `https://pulse.orfi.com.br/health` -> `ok`
- Observacao operacional:
  - o `push` para `origin/main` ficou bloqueado neste shell por falta de credencial GitHub HTTPS (`could not read Username for 'https://github.com'`)
- Proximo passo recomendado:
  - validar manualmente em producao os fluxos de `/conversations`, `/training` e `agent-lab`, e depois empurrar o commit `04110b8` para o GitHub a partir de um shell com credencial configurada

## 2026-03-24
- `sdr`: criei um ciclo de autoaprendizado auditável a partir das conversas reais e corrigi a persistência de contexto do Agent Lab.
- O que mudou nesta passada:
  - o Agent Lab passou a capturar `nome completo`, `CPF` e `telefone` antes de gerar a resposta, igual ao fluxo de WhatsApp
  - o prompt da agente agora reconhece estado de `simulação em andamento` e evita reiniciar qualificação ou recadastro após promessa de proposta/simulação
  - entrou a tabela `agent_improvements` com trilha de melhorias aplicadas, origem, versões base/aplicadas e dados de reversão
  - o backend ganhou autoanálise de conversas reais do agente, usando todas as conversas operacionais do agente para consolidar sinais heurísticos e recomendações
  - a página `/training` agora permite rodar `Aprender com conversas reais`, listar o histórico de melhorias e reverter cada melhoria aplicada
- Validacao executada:
  - `python3 -m py_compile backend/app/services/training.py backend/app/services/agent_improvements.py backend/app/services/llm.py backend/app/api/v1/agents/routes.py backend/app/api/v1/messages/routes.py backend/app/agents/nodes.py backend/app/models/entities.py backend/app/schemas/training.py backend/app/services/messages.py` -> ok
  - `npm run typecheck` no frontend com Node 20 -> ok
- Deploy:
  - imagem `sdr-backend:prod-20260324d` buildada no proxy Docker do Portainer
  - imagem `sdr-frontend:prod-20260324a` buildada no proxy Docker do Portainer com contexto enxuto
  - migration `009_agent_improvement_history` aplicada em container temporario
  - stack `sdr` reaplicada com `BACKEND_IMAGE=sdr-backend:prod-20260324d` e `FRONTEND_IMAGE=sdr-frontend:prod-20260324a`
  - services `sdr_backend` e `sdr_frontend` convergiram com `update completed`
- Smoke em producao:
  - backend novo respondeu `{"status":"ok","service":"Agente Vendedor Backend"}`
  - `https://pulse.orfi.com.br/health` respondeu `200`
- Próximo passo recomendado:
  - executar uma autoanálise real em `/training`, revisar o primeiro item do histórico e validar manualmente um caso de regressão no Agent Lab como o exemplo reportado

## 2026-03-24
- `sdr`: reforcei a captura obrigatoria de cadastro do lead e silenciei o agente apos handoff humano sem perder acompanhamento.
- O que mudou nesta passada:
  - adicionei `cpf` na tabela `leads` com migration `008_lead_profile_fields`
  - o backend agora tenta capturar `nome completo`, `CPF` e `telefone` de toda entrada e persiste pendencias no `metadata_json`
  - os dois fluxos de inbound WhatsApp passaram a seguir atualizando contexto, resumo e status mesmo em `handoff`, mas sem enviar nova resposta do agente
  - o prompt do agente passou a tratar `nome completo`, `CPF` e `telefone` como pre-requisito antes de simulacao/proposta
  - a API de conversas agora expoe `lead_name`, `lead_phone`, `lead_cpf`, pendencias cadastrais e flag de agente pausado
  - a tela `/conversations` passou a mostrar nome, telefone, CPF, pendencias e sinalizacao de agente pausado por handoff
- Validacao executada:
  - `python3 -m py_compile backend/app/services/whatsapp.py backend/app/agents/nodes.py backend/app/services/lead_capture.py backend/app/services/messages.py backend/app/schemas/messages.py backend/app/models/entities.py` -> ok
- Deploy:
  - imagem `sdr-backend:prod-20260324c` buildada pelo proxy Docker do Portainer
  - migration `008_lead_profile_fields` executada em container temporario na rede `sdr_internal`
  - stack `sdr` reaplicada com `BACKEND_IMAGE=sdr-backend:prod-20260324c`
  - service `sdr_backend` convergiu com `update completed`
- Smoke em producao:
  - `GET /health` no container novo respondeu `{"status":"ok","service":"Agente Vendedor Backend"}`
- Próximo passo recomendado:
  - validar um caso real com lead sem CPF, depois handoff humano, depois nova mensagem do lead sem resposta automatica da agente

## 2026-03-24
- `sdr`: implementei memoria longa incremental para a conversa e publiquei o backend novo.
- O que mudou nesta passada:
  - o snapshot do Redis ganhou `memory_notes`, com fatos deduplicados e persistentes entre turnos
  - `refresh_conversation_context_from_db()` agora mescla a memória anterior com o contexto novo da rodada
  - o prompt do agente passou a receber `memoria_longa=` junto do contexto estruturado
  - a imagem `sdr-backend:prod-20260324b` foi buildada e publicada na stack `sdr`
- Validacao executada:
  - `python3 -m py_compile backend/app/services/conversation_context.py backend/app/agents/nodes.py backend/tests/test_conversation_context.py` -> ok
- Próximo passo recomendado:
  - testar uma conversa real longa e ver se o agente passa a retomar fatos antigos sem perder o fio

## 2026-03-24
- `sdr`: adicionei Redis ao manifesto de produção para suportar o cache de contexto sem depender de localhost.
- O que mudou nesta passada:
  - o stack `sdr` ganhou um service `redis` persistente em volume próprio
  - o backend passou a receber `REDIS_URL=redis://redis:6379/0`
  - `CELERY_TASK_ALWAYS_EAGER=true` foi mantido para evitar regressão de filas sem worker dedicado nessa stack
  - a documentação e o `.env.example` de deploy foram alinhados com o novo service
- Próximo passo recomendado:
  - publicar a stack atualizada e repetir um inbound real de WhatsApp para confirmar que o cache de contexto funciona sem `callback status 500`

## 2026-03-24
- `sdr`: investiguei o `callback status 500` do WhatsApp e encontrei a causa no Redis do cache de contexto.
- O que mudou nesta passada:
  - os logs de producao mostravam `POST /api/v1/whatsapp/inbound 500` com `ConnectionRefusedError` em `127.0.0.1:6379`
  - `load_cached_conversation_context()` e `store_cached_conversation_context()` passaram a tratar Redis indisponivel como cache best-effort, sem quebrar o inbound
  - adicionei regressao para o caso de Redis fora do ar durante o callback do WhatsApp
- Validacao executada:
  - `python3 -m py_compile backend/app/services/conversation_context.py backend/tests/test_conversation_context.py backend/tests/test_whatsapp_gateway.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q tests/test_conversation_context.py tests/test_whatsapp_gateway.py` -> bloqueado pelo host com Python 3.9, mas o codigo alvo ficou sintaticamente valido
- Deploy:
  - imagem `sdr-backend:prod-20260324a` buildada via API do Portainer
  - stack `sdr` reaplicada com `BACKEND_IMAGE=sdr-backend:prod-20260324a`
  - service `sdr_backend` convergiu com `update completed`
- Próximo passo recomendado:
  - repetir um inbound real de WhatsApp e confirmar que o `callback status 500` sumiu

## 2026-03-24
- `sdr`: rebatizei a agente de `Márcia` para `Íris` no tenant `tenant-lab` e alinhei a UI de treino com o novo nome.
- O que mudou nesta passada:
  - o registro da agente foi atualizado via `PATCH /api/proxy/agents/{id}` com `name=Íris` e `slug=iris`
  - a página de treino passou a mostrar `Treino da Íris` e as copias auxiliares agora usam o novo nome
  - o prompt de primeira resposta já estava apontando para `Íris`, então o runtime ficou coerente com a mudança
- Validação executada:
  - `python3 -m py_compile backend/app/agents/nodes.py` -> ok
  - `GET /api/proxy/agents` e `GET /api/proxy/agents/{id}` -> retornaram `Íris`
  - `GET /api/auth/session` -> confirmou a sessão usada na alteração
  - `npm run lint` no frontend nao concluiu com o Node padrao `v12.22.12`
  - `npm run typecheck` com Node 20 -> ok
  - `npm run build` com Node 20 -> ok
- Próximo passo recomendado:
  - usar Node 20+ para os checks de frontend sempre que precisar validar esse app localmente

## 2026-03-23
- `sdr`: ajustei a abertura da agente para responder com duas mensagens iniciais fixas.
- O que mudou nesta passada:
  - a primeira resposta do atendimento agora sai como duas bolhas separadas:
    - `Olá! Aqui é da Orfi Consórcios 👋`
    - `Me conta: você está buscando imóvel ou veículo?`
  - a regra de estilo passou a limitar emojis a uso sutil e controlado
  - o backend agora poda emojis extras nas respostas geradas para manter o tom discreto
  - o treino da persona/agente também recebeu essa diretriz para não regredir em futuras publicações
- Validação executada:
  - `python3 -m py_compile backend/app/agents/nodes.py backend/app/services/agents.py backend/app/services/training.py backend/tests/test_agent_memory.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_agent_memory.py backend/tests/test_conversation_context.py` -> `12 passed`
- Deploy:
  - imagem `sdr-backend:prod-20260323c` buildada no Portainer a partir do backend local
  - stack `sdr` reaplicada com `BACKEND_IMAGE=sdr-backend:prod-20260323c`
  - service `sdr_backend` convergiu para a imagem nova
- Smoke em producao:
  - exec no container vivo confirmou exatamente as duas mensagens iniciais pedidas e `reply_fragments` com as duas entradas esperadas
- Próximo passo recomendado:
  - acompanhar uma conversa real na chegada para garantir que o tom permaneça natural depois da abertura

## 2026-03-23
- `sdr`: reestruturei a memória curta da conversa para slots mais robustos e genéricos.
- O que mudou nesta passada:
  - o snapshot em Redis saiu do eixo `property_*` e passou a guardar `lead_name`, `asset_type`, `asset_value`, `target_use_case`, `goal`, `timeline`, `lance`, `current_question_slot` e `last_confirmed_slot`
  - os slots extraídos foram separados do resumo textual em `extracted_slots` + `summary`
  - a atualização de slot agora depende de alta confiança no texto ou de pergunta explícita do turno anterior
  - o `nodes.py` passou a consumir essa memória curta estruturada em vez de manter uma heurística paralela solta
- Validação executada:
  - `python3 -m py_compile backend/app/services/conversation_context.py backend/app/agents/nodes.py backend/tests/test_agent_memory.py backend/tests/test_conversation_context.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_agent_memory.py backend/tests/test_conversation_context.py` -> `9 passed`
- Status atual:
  - ajuste publicado em produção e health pública validada
- Próximo passo recomendado:
  - repetir uma conversa curta da Márcia para validar retenção de nome, bem, valor, prazo e lance

## 2026-03-23
- `sdr`: corrigi a perda de contexto da Márcia quando o lead responde com valores curtos em sequência.
- O que mudou nesta passada:
  - a memória e o snapshot de conversa agora inferem o slot esperado a partir da última pergunta do assistente
  - respostas como `10mil` depois de uma pergunta sobre lance passam a alimentar `lance`, sem sobrescrever o valor do bem
  - o parser passou a reconhecer `moto`, `carro`, `veiculo` e afins como tipo de bem
  - respostas de prazo como `80 meses` deixaram de ser tratadas como valor monetário
- Validação executada:
  - `python3 -m py_compile backend/app/agents/nodes.py backend/app/services/conversation_context.py backend/tests/test_agent_memory.py backend/tests/test_conversation_context.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_agent_memory.py backend/tests/test_conversation_context.py` -> `9 passed`
- Status atual:
  - ajuste local pronto para publicar
- Próximo passo recomendado:
  - publicar e repetir a conversa da Márcia com sequências curtas de qualificacao

## 2026-03-23
- `sdr`: refinei de novo o comportamento da Márcia para reduzir repetição e melhorar a leitura de intenção.
- O que mudou nesta passada:
  - a classificação de intenção agora reconhece explicitamente mensagens de investimento/vale a pena como `investment`
  - o prompt de resposta passou a impor no maximo uma pergunta por turno e a confirmar apenas dados novos, sem repetir o resumo completo
  - a diretriz de treino da persona/agente foi alinhada para nao incentivar confirmacao repetitiva
  - a temperatura do gerador de respostas foi reduzida para diminuir eco e verbosidade
  - alguns modulos receberam `from __future__ import annotations` para permitir importacao dos testes nesse host com Python 3.9
- Validação executada:
  - `python3 -m py_compile backend/app/agents/nodes.py backend/app/agents/state.py backend/app/agents/tools.py backend/app/schemas/agents.py backend/app/schemas/messages.py backend/app/services/conversation_context.py backend/app/services/messages.py backend/app/services/training.py backend/app/services/agents.py backend/app/services/llm.py backend/tests/test_agent_memory.py backend/tests/test_conversation_context.py` -> ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_agent_memory.py backend/tests/test_conversation_context.py` -> `7 passed`
- Status atual:
  - ajuste publicado em produção e health pública validada
- Próximo passo recomendado:
  - repetir a simulacao da Márcia para confirmar menos repetição no fluxo real

## 2026-03-23
- `sdr`: ajustei o comportamento da Márcia para um primeiro atendimento mais simpático e humano.
- O que mudou nesta passada:
  - o prompt de resposta agora pede boas-vindas, apresentação, pergunta pelo nome do lead e oferta de ajuda sobre consórcios
  - a conversa passa a evitar repetição de saudação, pergunta e formulação
  - o treinador de persona/agente passou a reforçar essa diretriz nas revisões automáticas
  - a descrição base do playbook de consórcios foi alinhada com essa postura
- Validação executada:
  - `python3 -m py_compile backend/app/agents/nodes.py backend/app/services/agents.py backend/app/services/training.py` -> ok
- Status atual:
  - ajuste pronto para publicar
- Próximo passo recomendado:
  - commit/push e redeploy da stack `sdr`, depois smoke da conversa da Márcia

## 2026-03-23
- `sdr`: o laboratório de `Knowledge Ops` quebrou porque a stack de produção não tem worker/Redis e o backend estava chamando `delay()` com `localhost:6379`.
- O que mudou nesta passada:
  - ingestão e avaliação ganharam fallback para execução local em background quando `REDIS_URL` não estiver configurada
  - as tasks Celery foram preservadas, mas agora o backend pode operar sem broker nessa stack
  - o problema de `Clients` com `HttpUrl` já havia sido corrigido na mesma linha
- Validação executada:
  - `python3 -m py_compile backend/app/api/v1/knowledge/routes.py backend/app/workers/tasks/ingestion.py backend/app/workers/tasks/evaluation.py` -> ok
- Status atual:
  - correção publicada; o backend da stack `sdr` já está no novo digest e o `UpdateStatus` do serviço concluiu com sucesso
- Próximo passo recomendado:
  - smoke funcional do laboratório de conhecimento com uma ingestão real

## 2026-03-23
- `sdr`: corrigi o cadastro e a gestão de `Clients` depois de um erro de tipo no backend ao persistir `website_url`.
- O que mudou nesta passada:
  - `create_client()` e `update_client()` agora serializam o payload em `mode="json"` antes de tocar no Postgres
  - a tela `/clients` passou a suportar criação, seleção, edição e exclusão em um fluxo único
  - o formulário agora mostra o cliente selecionado com detalhes, status e confirmação antes de excluir
- Validação executada:
  - `python3 -m py_compile backend/app/services/clients.py` -> ok
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run typecheck` -> ok
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run build` -> ok
- Status atual:
  - correção pronta e publicada localmente
- Próximo passo recomendado:
  - smoke autenticado em `/clients` para validar criação, edição e exclusão com dados reais

## 2026-03-23
- `sdr`: a tela de `Products` foi publicada com CRUD funcional em produção.
- O que mudou nesta passada:
  - a página `/products` passou a permitir criar, selecionar, editar e excluir produtos
  - o inventário agora mostra cliente, versão, preço, estado e timestamps
  - a stack `sdr` foi reaplicada no Portainer com `pullImage=true`
  - os serviços convergiram para os novos digests de backend/frontend/whatsapp-gateway
- Validação executada:
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run typecheck` -> ok
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run build` -> ok
  - `https://pulse.orfi.com.br/health` -> `200`
  - `https://pulse.orfi.com.br/api/auth/providers` -> `200`
- Status atual:
  - CRUD de produtos corrigido e publicado
- Próximo passo recomendado:
  - smoke manual autenticado na página de produtos para validar criação, edição e exclusão no fluxo real

## 2026-03-23
- `sdr`: corrigi a tela de `Products` para suportar gestão completa de produto no frontend.
- O que mudou nesta passada:
  - a página `/products` passou a ter fluxo de criação, seleção, edição e exclusão
  - o painel agora lista produtos por cliente e mostra estado, versão, preço e timestamps
  - a edição ficou explícita no produto selecionado, com confirmação antes de excluir
- Validação executada:
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run typecheck` -> ok
  - `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run build` -> ok
- Status atual:
  - mudança pronta localmente e validada no frontend
- Próximo passo recomendado:
  - publicar a correção e fazer um smoke rápido na tela de produtos em produção

## 2026-03-23
- `sdr`: encontrei um erro no primeiro treino da Márcia em produção causado por `evaluation_runs.error_message` ficar curto demais para armazenar o traceback completo.
- O que mudou nesta passada:
  - `mark_evaluation_finished()` e `mark_job_finished()` agora compactam mensagens de erro antes de gravar no banco
  - a resposta final do trainer deixou de depender de `EvaluationRunResponse.model_validate()` em cima de ORM possivelmente expirado e passou a usar um build explícito do objeto refrescado
  - a compilação local dos módulos alterados passou com `python3 -m py_compile`
- Status atual:
  - correção local pronta para publicar
- Próximo passo recomendado:
  - redeploy da stack `sdr` e repetir o treino da Márcia para validar o caminho feliz e o caminho de falha

## 2026-03-23
- `sdr`: o treinamento da Márcia foi publicado em produção e recebeu uma correção pequena de hidratação da seleção do agente na página `/training`.
- O que mudou nesta passada:
  - commit `91d2a70` corrige a leitura do `agentId` ao abrir a tela de treino via link direto a partir de `Agents`
  - a stack `sdr` foi reaplicada no Portainer com `pullImage=true`
  - os serviços voltaram a convergir para os novos digests do `ghcr.io/ilki70/sdr/{backend,frontend,whatsapp-gateway}:latest`
  - `https://pulse.orfi.com.br/health` respondeu `200`
  - a rota `/training` respondeu `200` no frontend publicado
- Status atual:
  - trainer disponível em produção e link direto funcionando
- Próximo passo recomendado:
  - rodar um ciclo real com a persona da Márcia e calibrar os cenários de treino com base nas respostas geradas

## 2026-03-22
- `sdr`: adicionado um fluxo de treinamento para o agente vinculado a uma persona, com foco no primeiro atendimento da Márcia.
- O que entrou:
  - nova rota `POST /api/v1/agents/{agent_id}/training`
  - novo `Training Lab` em [`/training`](/home/ilki/sdr/frontend/app/(app)/training/page.tsx)
  - simulação de ciclos com `n` interações por ciclo, avaliação de qualidade e geração de recomendações
  - opção de aplicar as melhorias automaticamente, publicando nova versão da persona e nova versão do agente vinculado
  - atalho no menu lateral, command bar e link direto a partir da tela de `Agents`
- Validação executada:
  - `python3 -m py_compile` nos módulos backend alterados -> ok
  - `npm run build` no frontend -> ok
  - `npm run typecheck` no frontend -> ok
- Status atual:
  - fluxo de treino implementado e validado localmente
- Proximo passo recomendado:
  - rodar uma sessão de treino real para a Márcia em produção e ajustar os prompts gerados pelo trainer conforme os resultados

## 2026-03-22
- `sdr`: stack de producao reaplicada no Portainer com `pullImage=true` depois do commit `3dee802`.
- Estado do deploy:
  - Portainer autenticado com sucesso e stack localizada em `Id 35`, `endpointId 1`
  - update da stack aceito via API com `PUT /api/stacks/35?endpointId=1`
  - servicos convergiram para os novos digests do `ghcr.io/ilki70/sdr/{backend,frontend,whatsapp-gateway}:latest`
  - `https://pulse.orfi.com.br/health` respondeu `200`
  - `https://pulse.orfi.com.br/api/auth/providers` respondeu `200`
- Status atual:
  - deploy em producao concluido e funcional
- Proximo passo recomendado:
  - acompanhar o uso real das telas de `Personas` e `Agents` e, se necessario, ajustar microcopy/fluxos de edicao

## 2026-03-22
- Reestruturei as telas `Personas` e `Agents` para fluxo real de gestão:
  - `Personas` agora permite criar, editar metadados, ativar/inativar, publicar nova versão e excluir a persona selecionada
  - `Agents` agora permite criar, editar metadados, excluir, publicar nova versão e trocar explicitamente a persona vinculada em cada publicação
  - a UI passou a mostrar o vínculo ativo `agente -> persona` e o histórico de versões com ação de republicação
- Backend ampliado para sustentar o frontend:
  - novo `PATCH /api/v1/personas/{persona_id}`
  - novo `DELETE /api/v1/personas/{persona_id}`
  - novo `DELETE /api/v1/agents/{agent_id}`
  - criação/publicação de versão de agente agora valida se a persona existe, está ativa e tem versão publicada quando usada no vínculo
  - exclusão segue soft delete; no caso de agentes, a API bloqueia remover o último agente ativo do tenant
- Validação executada:
- `python3 -m py_compile backend/app/api/v1/personas/routes.py backend/app/api/v1/agents/routes.py backend/app/services/personas.py backend/app/services/agents.py backend/app/schemas/personas.py` -> ok
- `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm ci --no-audit --no-fund` em `frontend` -> ok
- `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run typecheck` em `frontend` -> ok
- `PATH=/home/ilki/.nvm/versions/node/v20.20.1/bin:$PATH npm run build` em `frontend` -> ok
- Smoke funcional local concluído pelo frontend autenticado/proxy:
  - login em `api/auth/login` -> ok
  - `POST/PATCH/DELETE` de personas via `api/proxy/personas` -> ok
  - `POST/DELETE` de agents e `POST` de novas versões via `api/proxy/agents` -> ok
  - troca de vinculação `agent -> persona` por nova versão publicada -> ok
  - proteção de exclusão de persona ainda vinculada a agente ativo -> ok, retornando `400`
  - após desvincular a persona em nova versão do agente, a exclusão da persona passou -> ok
- Ajustes de ambiente para o smoke local:
  - adicionei `.env` locais mínimos em `backend/` e `frontend/` para subir o fluxo local
  - o host só oferece `python3.9`, então foi necessário adicionar `from __future__ import annotations` em módulos do backend com tipagem moderna e instalar `eval_type_backport` para o runtime local aceitar as anotações
  - como o app completo ainda importa rotas fora do escopo com incompatibilidades adicionais nesse host, usei `app/smoke_main.py` para subir somente `auth`, `personas` e `agents` durante o smoke
- Status atual:
  - backend e telas principais ajustados para o CRUD pedido de personas e agentes
  - vínculo de persona no agente ficou publicável e trocável a cada nova versão
- Limitação atual do ambiente:
  - o smoke visual por Playwright não rodou neste host porque faltam bibliotecas nativas de browser; a validação desta passada foi HTTP/end-to-end via frontend proxy e backend local
- Próximo passo recomendado:
  - fazer uma passada visual real em navegador no ambiente de homologação ou num host com dependências de Playwright/Chrome instaladas, e então seguir para rollout

## 2026-03-20
- Refatorei a tela `Conversations` do frontend para um formato de acompanhamento de leads mais proximo de CRM:
  - a lista de cards foi substituida por tabela dark com filtros, busca, ordenacao e paginacao
  - a grade ganhou colunas de `Status`, `Agente responsavel`, `Proximo passo` e `Resumo da conversa`
  - o detalhe da conversa saiu de modal central e virou painel lateral estilo inbox operacional
  - as acoes rapidas do painel (`handoff`, `agendado`, `desqualificar`, `voltar para qualificacao`) agora chamam backend real para persistir o estagio operacional
- Ajustei o backend do modulo de mensagens para devolver novos campos derivados na listagem de conversas:
  - `summary`
  - `pipeline_status`
  - `next_step`
  - os valores sao inferidos a partir do estado da conversa, lifecycle do lead e metadata da ultima resposta do assistente
- Backend de mensagens ganhou novo endpoint:
  - `PATCH /api/v1/messages/conversations/{conversation_id}/pipeline-status`
  - ele atualiza `Conversation.status` e `Lead.lifecycle_status` sem exigir migracao de schema nesta passada
- O funil operacional deixou de ser apenas inferido e passou a ser modelado explicitamente em `Conversation`:
  - nova migration `007_conversation_pipeline_fields`
  - novos campos persistidos: `pipeline_status`, `summary` e `next_step`
  - os fluxos de Agent Lab e WhatsApp agora gravam esses campos diretamente
- Validacao executada:
  - `python3.11 -m py_compile backend/app/models/entities.py backend/app/schemas/messages.py backend/app/services/messages.py backend/app/api/v1/messages/routes.py backend/app/services/whatsapp.py backend/app/services/whatsapp_gateway.py backend/alembic/versions/007_conversation_pipeline_fields.py` -> ok
- Tentativa de aplicar migration local:
  - o bloqueio inicial por falta de MySQL local foi resolvido depois da instalacao do MariaDB no host
  - `python3.11 -m alembic upgrade head` aplicado com sucesso em `agente_vendedor`
  - a revisao ativa agora e `007_conversation_pipeline_fields`
  - a tabela `conversations` passou a ter `pipeline_status`, `summary` e `next_step`
- Limitacao atual:
  - o frontend local continua sem `node_modules`, entao a validacao por `tsc` ainda nao rodou neste workspace
- Validacao adicional apos migracao:
  - `DATABASE_URL=mysql+asyncmy://app:app@127.0.0.1:3306/agente_vendedor python3.11 -m pytest -q tests/test_messages_pipeline.py tests/test_whatsapp_gateway.py` -> `5 passed`
- Proximo passo recomendado:
  - popular conversas de desenvolvimento e validar a tela `Conversations` contra dados reais persistidos no MySQL local

## 2026-03-20
- Diagnostiquei uma falha de resposta no WhatsApp em producao:
  - o backend nao estava recebendo nenhum `POST /api/v1/whatsapp/inbound`
  - os logs do `whatsapp-gateway` mostravam falha de descriptografia/sincronizacao da sessao com `database is locked (SQLITE_BUSY)` logo apos autenticar
  - o mesmo periodo mostrou tentativas repetidas de `POST /api/v1/whatsapp/session/connect`, com a primeira em `200` e as seguintes em `500`
- Correcao local preparada no gateway:
  - a abertura do `session.db` agora habilita `journal_mode(WAL)`, `synchronous(NORMAL)` e `busy_timeout(5000)` alem de `foreign_keys(1)`
  - `handleConnect` passou a retornar o estado atual sem reiniciar a conexao quando a sessao ja esta `connecting`, `pairing` ou conectada
- Validacao executada:
  - `go test ./...` em `services/whatsapp-gateway` -> ok
- Publicacao e deploy:
  - commit `63947b0 fix: harden whatsapp gateway session store` publicado em `main`
  - release `v0.2.5` criada no GitHub
  - workflow `Build atendente3 images` concluiu com `success`
  - a stack `sdr` foi reaplicada no Portainer pelo editor da stack com confirmacao `Re-pull image and redeploy`
  - o servico `sdr_whatsapp-gateway` convergiu para `ghcr.io/ilki70/sdr/whatsapp-gateway:latest@sha256:6b935afb08e71692a9360adc4d19615d2e85240125adf3531225135e5bdb01da`
- Status atual:
  - frontend e health publico responderam `200` apos o rollout
  - o gateway novo subiu limpo; ainda falta validar um inbound real de WhatsApp depois da troca
- Proximo passo recomendado:
  - enviar uma mensagem real para a conta conectada e confirmar que o backend volta a registrar `/api/v1/whatsapp/inbound` e que o agente responde

## 2026-03-20
- Segunda passada no fluxo do WhatsApp apos o patch de SQLite:
  - o gateway voltou a autenticar sem `SQLITE_BUSY`, mas mensagens reais ainda nao chegavam ao backend
  - os logs mostraram `Successfully authenticated`, porem nenhum `/api/v1/whatsapp/inbound`
  - o backend ainda recebia `POST /api/v1/whatsapp/session/connect` repetido mesmo com a sessao ativa
- Correcao local preparada:
  - o `whatsapp-gateway` agora aceita chats `@lid` como inbound valido e tenta normalizar `lid -> numero` antes de encaminhar ao backend
  - `connect_whatsapp_gateway()` no backend passou a ser idempotente quando o status atual ja esta em `connected`, `connecting` ou `pairing`
- Validacao executada:
  - `go test ./...` em `services/whatsapp-gateway` -> ok
  - `python3.11 -m py_compile backend/app/services/whatsapp_gateway.py` -> ok
- Status atual:
  - correcao pronta localmente para publicacao e novo redeploy
- Proximo passo recomendado:
  - publicar esse patch e repetir o teste real com uma mensagem de WhatsApp

## 2026-03-20
- Migração concluída do clone problemático do `sdr` para um clone limpo no caminho padrão:
  - o clone limpo sincronizado foi promovido de `/home/ilki/tmp/sdr-sync-20260320` para `/home/ilki/sdr`
  - o clone antigo com `.git` quebrado foi preservado em `/home/ilki/sdr-broken-20260320`
  - o `origin` do clone novo foi sanitizado para `https://github.com/ilki70/sdr.git`, sem token gravado no config local
- Status atual:
  - `/home/ilki/sdr` esta limpo em `main`, alinhado a `origin/main`
- Proximo passo recomendado:
  - trabalhar somente no clone novo e descartar o backup antigo quando nao houver mais necessidade de consulta

## 2026-03-20
- Publicada a branch de sincronizacao `chore/resume-local-2026-03-20` no GitHub a partir do clone limpo em `/home/ilki/tmp/sdr-sync-20260320`.
- Delta publicado:
  - correção do `whatsapp_gateway` para persistir `payload.message_id` em `external_message_id`
  - teste de regressao dedicado em `backend/tests/test_whatsapp_gateway.py`
  - atualizacao dos docs locais de contexto (`PROJECT_CONTEXT`, `WORKLOG`, `turn2c-adaptation-plan`)
- Referencia:
  - branch remota `chore/resume-local-2026-03-20`
  - commit publicado `e283651 fix: align whatsapp gateway message id handling`
- Proximo passo recomendado:
  - abrir/revisar o PR da branch e decidir se o clone antigo em `/home/ilki/sdr` ainda precisa ser recuperado ou pode ser descartado em favor do clone limpo

## 2026-03-20
- Sincronizacao da retomada do `sdr` consolidada sobre o `main` remoto:
  - o clone legado em `/home/ilki/sdr` foi reorganizado em quatro commits locais, mas o `main` remoto ja continha quase toda essa linha por outros hashes
  - o delta real reaplicado sobre o `main` limpo ficou reduzido a uma correção no inbound do WhatsApp e ao teste correspondente
  - a correção salva `payload.message_id` em `external_message_id` no `whatsapp_gateway`, alinhando backend e payload real do gateway
- Status atual:
  - a base limpa de sincronizacao passou a viver em `/home/ilki/tmp/sdr-sync-20260320`
- Proximo passo recomendado:
  - validar o teste dedicado do gateway, revisar o branch limpo e publicar essa delta minima

## 2026-03-20
- Fechei o ciclo de publicacao do `sdr`:
  - commit, push, release `v0.2.3` e redeploy da stack `sdr` concluidos
  - o Portainer ficou alinhado ao `deploy/sdr/stack.yml` do repositorio
  - o workflow de build de imagens terminou com `success`
  - smoke publico passou em `/health` e `/api/auth/providers`
- Proximo passo recomendado:
  - acompanhar o proximo ciclo funcional em producao e usar a stack versionada como fonte de verdade para novos redeploys

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

## 2026-03-20
- Refatorada a pagina de `Conversas` para uma tabela operacional estilo CRM/inbox em [`frontend/app/(app)/conversations/page.tsx`](/home/ilki/sdr/frontend/app/(app)/conversations/page.tsx):
  - colunas de entrada, ultima interacao, nome/contato, status, agente responsavel, proximo passo, resumo e acao
  - busca, filtros, ordenacao, paginacao e painel lateral no lugar do modal
  - acoes rapidas do funil ligadas ao endpoint real de atualizacao de status
- Persistido o funil como dado de primeira classe em `Conversation`:
  - novos campos `pipeline_status`, `summary` e `next_step`
  - migration criada em [`backend/alembic/versions/007_conversation_pipeline_fields.py`](/home/ilki/sdr/backend/alembic/versions/007_conversation_pipeline_fields.py)
  - backend ajustado em `messages`, `whatsapp` e `whatsapp_gateway`
- Validacao local concluida:
  - MariaDB local instalado e banco `agente_vendedor` criado
  - `alembic upgrade head` aplicado ate `007_conversation_pipeline_fields`
  - testes `tests/test_messages_pipeline.py` e `tests/test_whatsapp_gateway.py` verdes
- Criado seed idempotente para demo da nova tela:
  - [`backend/scripts/seed_conversations_demo.py`](/home/ilki/sdr/backend/scripts/seed_conversations_demo.py)
  - popula `tenant-lab` com 5 conversas e 10 mensagens distribuidas entre `new`, `qualifying`, `handoff`, `scheduled` e `disqualified`
- Validacao de frontend concluida com toolchain local:
  - `npm ci` em [`frontend`](/home/ilki/sdr/frontend) usando `Node v20.20.1` via `~/.nvm/versions/node/v20.20.1/bin`
  - `npx tsc --noEmit --incremental false` passou
  - `npm run lint` nao serviu como validacao porque o script atual `next lint` falha nesta base com `Invalid project directory provided`

## Current Status
- O backend local ja persiste o funil operacional no banco.
- O banco MariaDB local tem dados reais suficientes para validar a nova tela de `Conversas`.
- O frontend compila localmente; ainda nao houve validacao visual no navegador neste host, porque o ambiente nao oferece browser local.
- O script de lint do frontend precisa ser revisto separadamente se a equipe quiser restaurar validacao ESLint local.

## Next Recommended Step
- Se quiser seguir no fluxo atual sem preview remoto, o proximo passo mais seguro e revisar o diff, ajustar detalhes finais da tabela e entao preparar commit.
- Opcionalmente, corrigir o script de lint do frontend antes de consolidar o commit.

## 2026-03-20
- Publicado o bloco `feat: add conversations funnel crm workflow` no `main` e atualizado o deploy da stack `sdr`.
- O workflow `Build atendente3 images` do commit `e5cdc8b` concluiu com sucesso e o Portainer reaplicou a stack com `PullImage=true`.
- Logo apos o rollout, o dashboard quebrou porque o Postgres da producao ainda nao tinha a migration `007_conversation_pipeline_fields` aplicada.
- Correcao executada em producao:
  - `alembic upgrade head` rodado dentro do container `sdr_backend`
  - revisao confirmada: `007_conversation_pipeline_fields`
  - colunas confirmadas na tabela `conversations`: `pipeline_status`, `summary`, `next_step`
- Validacao publica apos correcao:
  - `https://pulse.orfi.com.br/` -> `200`
  - `https://pulse.orfi.com.br/health` -> `200`
  - `https://pulse.orfi.com.br/api/auth/providers` -> `200`
- Digests ativos relevantes apos o rollout:
  - backend: `ghcr.io/ilki70/sdr/backend:latest@sha256:e2ff8dcf7bed7056644cfd5fd52ce17ff8c38bbe6bbfdee90e96e8bc7c254a8d`
  - frontend: `ghcr.io/ilki70/sdr/frontend:latest@sha256:e4012b019aa99585f4c7df4a74881644691d51f6ccdfb3295deae7cae131fc8b`
  - whatsapp-gateway: `ghcr.io/ilki70/sdr/whatsapp-gateway:latest@sha256:81f237300ced9f8017a5aff686612e036f6c0bc628c007a68931e423f323e358`

## Current Status
- A nova experiencia de `Conversations` esta publicada em producao.
- O funil operacional por conversa agora existe no schema e no backend de producao.
- A stack `sdr` esta saudavel depois da correcao manual de migration.
- O release `v0.2.7` foi criado no GitHub a partir do estado publicado em `main`.

## Next Recommended Step
- Em uma passada futura, reforcar no bootstrap/deploy um check explicito de schema para reduzir o risco de drift apos rollouts.
- Quando houver nova rodada de deploy com alteracao de schema, validar rollout + revisao Alembic como parte do checklist operacional.

## 2026-03-21
- Investigado o relato de que a sessao do WhatsApp "caia" apos inatividade.
- Diagnostico encontrado no `whatsapp-gateway` em producao:
  - o container estava com sessao persistida (`stored_session`) e numero pareado conhecido
  - apos restart do processo, o gateway nao chamava `Connect()` sozinho; ele so reconectava quando alguem acionava manualmente `/api/v1/session/connect`
  - por isso o frontend podia mostrar `Conectado: nao` mesmo com a sessao salva no SQLite
- Correcao aplicada em [`services/whatsapp-gateway/main.go`](/home/ilki/sdr/services/whatsapp-gateway/main.go):
  - reconexao automatica no boot quando existe sessao armazenada
  - tentativa de autocura quando a UI consulta o status e encontra `stored_session` desconectado
  - tratamento explicito de eventos `Disconnected`, `KeepAliveTimeout`, `ConnectFailure` e `TemporaryBan`
  - preservado o fluxo manual de pareamento para sessao nova via QR code
- Publicacao e deploy:
  - commit `232d937 fix: auto reconnect stored whatsapp sessions` publicado em `main`
  - workflow `Build atendente3 images` do commit `232d937` concluiu com `success`
  - stack `sdr` reaplicada no Portainer com `PullImage=true`
- Validacao em producao apos o rollout:
  - `sdr_whatsapp-gateway` convergiu para `ghcr.io/ilki70/sdr/whatsapp-gateway:latest@sha256:6db3752cac001cc8d287200624cf973f2c1626d78ec0a04d32fb4bc0756fb6b5`
  - o `session status` interno do gateway voltou para `connected=true` e `session_status=connected`
  - smoke publico: `/`, `/health` e `/api/auth/providers` responderam `200`

## Current Status
- O gateway de WhatsApp volta a reconectar automaticamente quando existe sessao salva.
- O status atual em producao voltou para `connected`.

## Next Recommended Step
- Confirmar com uma nova rodada de ociosidade real se a sessao permanece conectada sem intervencao manual.
- Se o `last_error` voltar a aparecer apos mensagens reais, revisar separadamente o callback inbound do gateway.

## 2026-03-24
- `sdr`: evolui o `langgraph_runtime` para usar estado conversacional semantico e deixar a SDR menos mecanica.
- O que mudou:
  - passei a persistir `langgraph_runtime_state` no `Lead.metadata_json` junto do `slot_projection`
  - o runtime agora carrega e atualiza `current_topic`, `conversation_mode`, `speech_act`, `last_agent_commitment` e `pending_user_request`
  - reduzi as confirmacoes excessivas de slot unico
  - tratei melhor entrega de simulacao e correcoes como `o q ja passei`, reaproveitando o telefone ja conhecido
  - mantive o encerramento curto quando o lead claramente quer parar
- Validacao:
  - `python3 -m py_compile backend/app/services/langgraph_runtime.py backend/app/services/runtime_router.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` ok (`21 passed`)

## Current Status
- O runtime novo ja nao depende so de slots; ele tambem persiste o estado da situacao conversacional.
- A SDR consegue manter melhor contexto de envio, correcao de contexto e encerramento.

## Next Recommended Step
- Rodar uma bateria de simulacoes baseada em conversas reais para endurecer transicoes comerciais mais sutis, como objecoes, impaciencia e retomada apos espera.
- Se o comportamento local ficar bom nesses cenarios, consolidar em commit e publicar novo deploy do backend.

## 2026-03-24
- `sdr`: rodei simulacoes encadeadas do `langgraph_runtime` com casos proximos das conversas reais para encontrar perda de contexto.
- Falhas encontradas e corrigidas:
  - `uso proprio`, `o q ja passei` e `me envie` podiam ser capturados como `lead_name`
  - `12 meses` e `4mil` ainda conseguiam sobrescrever `asset_value` em vez de preencher prazo/parcela
  - depois de `sim` para a simulacao, a SDR nao entrava de forma limpa na etapa de escolha de canal
  - depois do compromisso de envio, `nao` ainda podia reabrir o fluxo em vez de encerrar
- Correcao aplicada:
  - restringi captura de nome ao contexto certo
  - tornei `budget_monthly` parte da qualificacao comercial antes do cadastro
  - tratei `sim` apos `proposal_ready` como aceite operacional para perguntar canal de entrega
  - tratei `nao` apos compromisso de envio como fechamento
  - ampliei `_extract_target_use_case` para entender `uso proprio`/`uso pessoal` como `moradia`
- Validacao:
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py backend/tests/test_conversation_context.py` ok (`37 passed`)

## Current Status
- O runtime local ja reproduz de forma mais coerente a trilha: qualificacao -> parcela alvo -> cadastro -> aceite -> escolha de canal -> envio -> encerramento.
- As simulacoes encadeadas nao mostraram mais perda basica de contexto nesses cenarios.

## Next Recommended Step
- Repetir a bateria com objecoes, irritacao e retomada depois de horas/dias usando historico real anonimizado.
- Se o resultado continuar bom, consolidar commit e publicar novo deploy do backend.

## 2026-03-24
- `sdr`: analisei o workflow `Isis 5` do n8n para extrair os padroes que deixam a conversa mais humana e mais estavel.
- Conclusoes principais:
  - o ganho nao vem de mais regras de slot, e sim de memoria persistente por sessao, agregacao de mensagens, tools com pre-condicoes, handoff explicito, RAG sob demanda e pos-processamento por canal
  - o agente central da `Isis` parece melhor porque conversa em cima de politica + memoria + tools, e nao de uma arvore grande de respostas
- Resultado registrado em [`docs/n8n-isis-conversation-patterns.md`](/home/ilki/sdr/docs/n8n-isis-conversation-patterns.md)

## Current Status
- A direcao arquitetural mais promissora para o `sdr` agora esta mais clara: runtime mais fino, memoria melhor, tools melhores e menos micro-regras de conversa.

## Next Recommended Step
- Traduzir esse aprendizado em um plano concreto de refatoracao do `sdr`, reduzindo o peso do runtime atual e introduzindo debounce, memoria persistente semantica e tools com pre-condicoes.

## 2026-03-24
- `sdr`: formalizei o plano concreto de refatoracao da conversa em [`docs/sdr-conversation-refactor-plan.md`](/home/ilki/sdr/docs/sdr-conversation-refactor-plan.md).
- Direcao definida:
  - trocar a arquitetura de "runtime com muitas regras" por 5 camadas: ingestao, memoria, politica conversacional, tools e formatacao por canal
  - manter `langgraph` como orquestrador fino, e nao como lugar de toda a inteligencia procedural
  - reaproveitar Redis, `conversation_context`, `lead_capture`, `runtime_router` e persistencia atual
- Tambem atualizei [`docs/langgraph-runtime-plan.md`](/home/ilki/sdr/docs/langgraph-runtime-plan.md) para refletir essa mudanca de enfoque.

## Current Status
- O projeto agora tem uma direcao tecnica mais consistente para sair da espiral de regras no runtime.

## Next Recommended Step
- Comecar a Fase 1 do plano: criar `conversation_runtime_state` persistente e adaptar o `runtime_router` para salvar e carregar esse estado de forma centralizada.

## 2026-03-24
- `sdr`: iniciei a Fase 1 do plano de refatoracao da conversa.
- O que entrou:
  - `runtime_router` agora persiste o estado conversacional central em `Lead.metadata_json["conversation_runtime_state"]`
  - mantive compatibilidade com `langgraph_runtime_state` durante a transicao
  - o `langgraph_runtime` passou a preferir o estado central novo quando ele existir
- Validacao:
  - `python3 -m py_compile backend/app/services/runtime_router.py backend/app/services/langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_langgraph_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_messages_langgraph_runtime.py backend/tests/test_langgraph_runtime.py` ok (`24 passed`)

## Current Status
- O projeto agora ja tem um ponto unico e generico para o estado conversacional persistente, sem ficar preso ao nome do runtime atual.

## Next Recommended Step
- Continuar a Fase 1 extraindo esse estado para um modulo proprio e fazer o restante do backend consumir `conversation_runtime_state` como fonte primaria, reduzindo dependencia de `slot_projection`.

## 2026-03-24
- `sdr`: continuei a Fase 1 extraindo o estado conversacional para um modulo proprio.
- O que entrou:
  - novo modulo [`conversation_runtime_state.py`](/home/ilki/sdr/backend/app/services/conversation_runtime_state.py)
  - `runtime_router` agora usa esse helper para persistir e ler estado
  - `langgraph_runtime` passou a consumir o helper central, em vez de ler metadata diretamente
  - testes dedicados em [`test_conversation_runtime_state.py`](/home/ilki/sdr/backend/tests/test_conversation_runtime_state.py)
- Validacao:
  - `python3 -m py_compile backend/app/services/conversation_runtime_state.py backend/app/services/runtime_router.py backend/app/services/langgraph_runtime.py backend/tests/test_conversation_runtime_state.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_langgraph_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_conversation_runtime_state.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_langgraph_runtime.py` ok (`27 passed`)

## Current Status
- O estado conversacional persistente agora ja existe como contrato reutilizavel do backend.

## Next Recommended Step
- Fazer os pontos de entrada e de atualizacao de conversa consumirem esse contrato de forma mais explicita e, em seguida, iniciar a extracao da `conversation_policy` para tirar decisao de conversa de dentro do runtime.

## 2026-03-24
- `sdr`: iniciei a extracao da `conversation_policy`.
- O que entrou:
  - novo modulo [`conversation_policy.py`](/home/ilki/sdr/backend/app/services/conversation_policy.py)
  - helpers puros de politica movidos para fora do `langgraph_runtime`:
    - deteccao de handoff humano
    - deteccao de encerramento
    - mensagens de progresso de simulacao
    - mensagens de entrega da simulacao
    - pergunta de canal de envio
  - testes dedicados em [`test_conversation_policy.py`](/home/ilki/sdr/backend/tests/test_conversation_policy.py)
- Validacao:
  - `python3 -m py_compile backend/app/services/conversation_policy.py backend/app/services/langgraph_runtime.py backend/tests/test_conversation_policy.py backend/tests/test_langgraph_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_conversation_policy.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_conversation_runtime_state.py` ok (`32 passed`)

## Current Status
- O runtime continua funcionando, mas parte da decisao conversacional ja esta saindo para uma camada propria.

## Next Recommended Step
- Continuar a extracao da `conversation_policy`, movendo decisoes de `simulation_delivery`, `proposal_in_progress` e `closing/handoff` para funcoes mais declarativas, ate o `langgraph_runtime` ficar majoritariamente orquestrador.

## 2026-03-24
- `sdr`: avancei a extracao da `conversation_policy` ate o `langgraph_runtime` ficar majoritariamente coordenador nos ramos centrais.
- O que mudou:
  - criei `PolicyDecision` em [`conversation_policy.py`](/home/ilki/sdr/backend/app/services/conversation_policy.py)
  - movi para a policy os ramos de:
    - `closing`
    - `handoff`
    - `simulation_delivery`
    - `proposal_in_progress`
    - `objection_handling`
  - o `langgraph_runtime` agora principalmente:
    - monta contexto
    - calcula sinais e faltas
    - delega decisoes para a policy
    - monta `LangGraphTurnResponse`
- Medida local desta passada:
  - `_compose_langgraph_reply` ficou com `131` linhas, bem menor e mais orquestrador do que antes
- Validacao:
  - `python3 -m py_compile backend/app/services/conversation_policy.py backend/app/services/langgraph_runtime.py backend/tests/test_conversation_policy.py backend/tests/test_langgraph_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_conversation_policy.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_conversation_runtime_state.py` ok (`32 passed`)

## Current Status
- O `langgraph_runtime` ja nao concentra sozinho a maior parte das decisoes centrais de conversa.

## Next Recommended Step
- Completar a virada extraindo os ramos restantes de qualificacao, cadastro e `proposal_ready` para a policy, e depois introduzir o `channel_formatter` para tirar preocupacoes de canal do runtime.

## 2026-03-24
- `sdr`: concluida a extracao dos ramos restantes de conversa para a `conversation_policy`.
- O que saiu do `langgraph_runtime` nesta passada:
  - `qualification`
  - `registration`
  - `proposal_ready`
- O que entrou:
  - `qualification_decision`
  - `registration_decision`
  - `proposal_ready_decision`
  em [`conversation_policy.py`](/home/ilki/sdr/backend/app/services/conversation_policy.py)
- Medidas locais apos a passada:
  - `_compose_langgraph_reply` caiu para `126` linhas
  - [`langgraph_runtime.py`](/home/ilki/sdr/backend/app/services/langgraph_runtime.py) ficou com `851` linhas
  - [`conversation_policy.py`](/home/ilki/sdr/backend/app/services/conversation_policy.py) ficou com `262` linhas
- Validacao:
  - `python3 -m py_compile backend/app/services/conversation_policy.py backend/app/services/langgraph_runtime.py backend/tests/test_conversation_policy.py backend/tests/test_langgraph_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_conversation_policy.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_conversation_runtime_state.py` ok (`35 passed`)

## Current Status
- O `langgraph_runtime` agora esta majoritariamente como orquestrador.
- A decisao conversacional principal foi movida para `conversation_policy`.

## Next Recommended Step
- Introduzir `channel_formatter` para tirar do runtime as preocupacoes de formato de saida por WhatsApp.
- Depois disso, revisar o que ainda faz sentido manter em `langgraph_runtime` e o que pode virar tool ou helper de policy.

## 2026-03-24
- `sdr`: introduzi a camada de formatacao de canal.
- O que entrou:
  - novo modulo [`channel_formatter.py`](/home/ilki/sdr/backend/app/services/channel_formatter.py)
  - `runtime_router` agora formata a saida do runtime antes de entregar `draft_reply` e `reply_fragments`
  - para WhatsApp, respostas longas agora podem ser quebradas em fragmentos menores antes de sair do pipeline
- Cobertura:
  - testes dedicados em [`test_channel_formatter.py`](/home/ilki/sdr/backend/tests/test_channel_formatter.py)
  - teste de integracao do `runtime_router` validando fragmentacao de resposta longa no canal WhatsApp em [`test_messages_langgraph_runtime.py`](/home/ilki/sdr/backend/tests/test_messages_langgraph_runtime.py)
- Validacao:
  - `python3 -m py_compile backend/app/services/channel_formatter.py backend/app/services/runtime_router.py backend/tests/test_channel_formatter.py backend/tests/test_messages_langgraph_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_channel_formatter.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_conversation_policy.py backend/tests/test_langgraph_runtime.py backend/tests/test_conversation_runtime_state.py backend/tests/test_whatsapp_gateway.py` ok (`42 passed`)

## Current Status
- O runtime agora ja esta separado em:
  - estado conversacional persistente
  - policy
  - formatter de canal
- O `langgraph_runtime` esta mais proximo de um orquestrador de verdade.

## Next Recommended Step
- Revisar o que ainda resta no `langgraph_runtime` e extrair o que for claramente `tool/helper`, especialmente partes de extracao semantica e follow-up operacional.
- Depois disso, consolidar commit, push e deploy quando fizer sentido.

## 2026-03-24
- `sdr`: extraí a semantica conversacional restante para um helper proprio e reduzi mais a responsabilidade direta do `langgraph_runtime`.
- O que entrou:
  - novo modulo [`conversation_semantics.py`](/home/ilki/sdr/backend/app/services/conversation_semantics.py)
  - migracao de heuristicas de `speech_act`, deteccao de canal, ajuste de simulacao, deteccao de objecao, prompts/follow-ups e verificacoes de slots para essa camada
  - alinhamento do `langgraph_runtime` para consumir apenas os helpers extraidos
- Cobertura:
  - testes dedicados em [`test_conversation_semantics.py`](/home/ilki/sdr/backend/tests/test_conversation_semantics.py)
  - regressao completa mantida nas suites de runtime, policy, formatter, router e gateway
- Validacao:
  - `python3 -m py_compile backend/app/services/conversation_semantics.py backend/app/services/langgraph_runtime.py backend/tests/test_conversation_semantics.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_conversation_semantics.py backend/tests/test_channel_formatter.py backend/tests/test_conversation_policy.py backend/tests/test_conversation_runtime_state.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` ok (`49 passed`)

## Current Status
- O `langgraph_runtime` esta mais proximo de um orquestrador puro:
  - estado em `conversation_runtime_state`
  - decisao em `conversation_policy`
  - semantica em `conversation_semantics`
  - formatacao em `channel_formatter`
- A base esta pronta para a proxima etapa estrutural sem continuar inchando o runtime central.

## Next Recommended Step
- Revisar o que ainda resta no `langgraph_runtime` como composicao/bridge de contexto e, se o desenho estiver estavel, consolidar commit, push e deploy.
- Na sequencia, partir para testes de conversa reais e endurecer a `conversation_policy`, em vez de voltar a colocar regra espalhada no runtime.

## 2026-03-24
- `sdr`: extraí a inferencia de contexto operacional restante do `langgraph_runtime`.
- O que entrou:
  - novo modulo [`conversation_runtime_context.py`](/home/ilki/sdr/backend/app/services/conversation_runtime_context.py)
  - migracao de:
    - deteccao de `proposal_commitment_state`
    - inferencia de `last_agent_commitment`
    - inferencia de `current_topic`
    - inferencia de `conversation_mode`
- Efeito pratico:
  - [`langgraph_runtime.py`](/home/ilki/sdr/backend/app/services/langgraph_runtime.py) caiu para `574` linhas
  - `_build_runtime_context` caiu para `57` linhas
  - o runtime ficou mais concentrado em encadear:
    - montagem basica do request
    - aplicacao da mensagem aos slots
    - refresh semantico
    - dispatch para policy
- Cobertura:
  - testes dedicados em [`test_conversation_runtime_context.py`](/home/ilki/sdr/backend/tests/test_conversation_runtime_context.py)
  - regressao completa mantida no runtime, router, formatter, policy, semantics e gateway
- Validacao:
  - `python3 -m py_compile backend/app/services/conversation_runtime_context.py backend/app/services/langgraph_runtime.py backend/tests/test_conversation_runtime_context.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_conversation_runtime_context.py backend/tests/test_conversation_semantics.py backend/tests/test_channel_formatter.py backend/tests/test_conversation_policy.py backend/tests/test_conversation_runtime_state.py backend/tests/test_langgraph_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_whatsapp_gateway.py` ok (`57 passed`)

## Current Status
- O `langgraph_runtime` esta efetivamente majoritariamente como orquestrador.
- A estrutura atual ficou separada em:
  - estado persistente
  - inferencia de contexto
  - semantica conversacional
  - policy
  - formatter de canal

## Next Recommended Step
- Consolidar commit, push e deploy desta rodada estrutural.
- Depois disso, sair da fase de refatoracao interna e voltar para o que interessa comercialmente: bater conversas reais e ajustar `conversation_policy`/prompts com evidencias do comportamento publicado.

## 2026-03-24
- `sdr`: consolidada a rodada estrutural do runtime com publicacao e deploy.
- Commits publicados:
  - `6dce6dd` `refactor: split sdr conversation runtime layers`
  - `e46604e` `docs: record sdr runtime refactor`
- Publicacao:
  - `main` enviado ao GitHub com sucesso
  - remote local restaurado para `https://github.com/ilki70/sdr.git`
- Deploy:
  - build remoto do backend no Portainer com a tag `sdr-backend:prod-20260324-6dce6dd`
  - stack `sdr` reaplicada na stack `35` com `BACKEND_IMAGE=sdr-backend:prod-20260324-6dce6dd`
  - `LANGGRAPH_RUNTIME_ENABLED=true` preservado no ambiente da stack
- Validacao operacional:
  - `sdr_backend` convergiu para `sdr-backend:prod-20260324-6dce6dd`
  - `UpdateStatus` do backend concluido com `State=completed`
  - smoke `https://pulse.orfi.com.br/health` respondeu `ok`
  - worktree local limpo apos os commits

## Current Status
- A rodada de refatoracao estrutural esta publicada e ativa em producao.
- O runtime novo esta no ar com a separacao de estado, contexto, semantica, policy e formatter.

## Next Recommended Step
- Rodar uma bateria de conversas reais no ambiente publicado e ajustar a `conversation_policy` com base em desvios observados, em vez de voltar a crescer o `langgraph_runtime`.

## 2026-03-24
- `sdr`: concluida auditoria de alinhamento entre o frontend operacional e a nova estrutura do runtime.
- Registro:
  - [`docs/frontend-runtime-alignment-audit.md`](/home/ilki/sdr/docs/frontend-runtime-alignment-audit.md)
- Diagnostico consolidado:
  - alinhado:
    - `Agent Lab`
  - parcialmente alinhado:
    - `Conversations`
    - `Knowledge`
  - desalinhado:
    - `Agents`
    - `Personas`
    - `Training`
- Evidencia principal:
  - `Agent Lab` usa `messages/stream` e cai em `run_configured_sales_runtime`
  - `Training` ainda usa `run_sales_agent` em [`backend/app/services/training.py`](/home/ilki/sdr/backend/app/services/training.py)
  - `Conversations` ainda depende de `inferMockStatus` e `buildMockSummary` no frontend
  - `Agents`/`Personas` seguem administrando prompt/playbook/versionamento, mas o runtime novo nao consome esses campos no caminho principal

## Current Status
- A base nova do runtime esta publicada, mas nem todas as areas do frontend foram realinhadas para ela.
- O maior desalinhamento funcional hoje esta em `Training`.

## Next Recommended Step
- Migrar `Training` para usar o runtime novo antes de mexer nas demais telas.
- Em seguida, redefinir como `Agents` e `Personas` alimentam a `conversation_policy` e/ou a configuracao estruturada do runtime.

## 2026-03-25
- `sdr`: migrado o fluxo de `Training` para o runtime novo publicado.
- O que mudou:
  - [`backend/app/services/training.py`](/home/ilki/sdr/backend/app/services/training.py) deixou de chamar `run_sales_agent` diretamente
  - `Training` agora passa por `run_configured_sales_runtime`, aplicando `lead_capture` e `slot_projection` no mesmo caminho do `Agent Lab` e do WhatsApp
  - adicionada regressao dedicada em [`backend/tests/test_training_runtime.py`](/home/ilki/sdr/backend/tests/test_training_runtime.py)
  - corrigida compatibilidade Python 3.9 em [`backend/app/schemas/knowledge.py`](/home/ilki/sdr/backend/app/schemas/knowledge.py) com `from __future__ import annotations`
- Validacao:
  - `python3 -m py_compile backend/app/schemas/knowledge.py backend/app/services/training.py backend/tests/test_training_runtime.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_training_runtime.py backend/tests/test_messages_langgraph_runtime.py backend/tests/test_langgraph_runtime.py` ok (`26 passed`)

## Current Status
- `Training` deixou de treinar o motor legado e agora usa o mesmo runtime configurado do produto publicado.
- O desalinhamento mais critico entre frontend e backend caiu; os proximos pontos prioritarios continuam sendo `Agents`, `Personas` e a remocao dos fallbacks de estado em `Conversations`.

## Next Recommended Step
- Realinhar `Agents` e `Personas` para que a configuracao editada nessas telas alimente a `conversation_policy` e o `conversation_runtime_state` de forma explicita.
- Depois disso, remover `inferMockStatus` e `buildMockSummary` de `Conversations` e expor o estado real do runtime na API.

## 2026-03-25
- `sdr`: alinhado o caminho entre `Agents`/`Personas`, `conversation_policy` e a tela de `Conversations`.
- O que mudou:
  - criado [`backend/app/services/conversation_policy_config.py`](/home/ilki/sdr/backend/app/services/conversation_policy_config.py) para resolver contexto publicado de `AgentVersion` + `PersonaVersion`
  - [`backend/app/services/runtime_router.py`](/home/ilki/sdr/backend/app/services/runtime_router.py) agora injeta esse `policy_context` no `langgraph_runtime`
  - [`backend/app/services/conversation_semantics.py`](/home/ilki/sdr/backend/app/services/conversation_semantics.py) passou a usar tom/regras da persona e playbook de objeções para modular prompts e respostas
  - [`backend/app/services/conversation_policy.py`](/home/ilki/sdr/backend/app/services/conversation_policy.py) passou a usar regras configuradas de handoff/follow-up
  - [`backend/app/services/messages.py`](/home/ilki/sdr/backend/app/services/messages.py) e [`backend/app/schemas/messages.py`](/home/ilki/sdr/backend/app/schemas/messages.py) agora expõem `runtime_state` real nas conversas
  - [`frontend/app/(app)/conversations/page.tsx`](/home/ilki/sdr/frontend/app/(app)/conversations/page.tsx) deixou de usar `inferMockStatus` e `buildMockSummary`, passando a confiar em `pipeline_status`, `summary`, `next_step` e `runtime_state` vindos da API
  - corrigido bug real em `messages.py`: `update_conversation_pipeline_status` ainda chamava `_get_lead_for_conversation`, helper inexistente
- Validacao:
  - `python3 -m py_compile` nos arquivos alterados ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_messages_langgraph_runtime.py backend/tests/test_messages_pipeline.py backend/tests/test_langgraph_runtime.py backend/tests/test_conversation_policy.py` ok (`43 passed`)

## Current Status
- `Training` ja usa o runtime novo.
- `Agents` e `Personas` passaram a influenciar o comportamento real da policy no runtime publicado.
- `Conversations` deixou de inferir status/resumo localmente e agora mostra o estado real consolidado pela API.

## Next Recommended Step
- Expor e usar no frontend a configuracao estruturada completa do playbook do agente, para reduzir dependencia de heuristica textual em `prompt_system`.
- Rodar uma bateria de conversas reais no ambiente publicado para ajustar a policy agora em cima de configuracao viva, nao mais de fallbacks locais.

## 2026-03-25
- `sdr`: consolidado commit, push e deploy da rodada de alinhamento entre studio, policy e conversations.
- Publicacao:
  - commit local e remoto: `717a864` `feat: align runtime policy with studio`
  - `git push` concluido em `origin/main`
- Deploy:
  - stack `sdr` reaplicada no Portainer (`stack id 35`, `endpointId 1`)
  - `BACKEND_IMAGE` atualizado para `ghcr.io/ilki70/sdr/backend:717a864665d83eb291176119a106f0b98656005a`
  - `sdr_backend` convergiu para a imagem `ghcr.io/ilki70/sdr/backend:717a864665d83eb291176119a106f0b98656005a@sha256:0f6282d2d52d4e4a823c1b5cb3a8cc944b1250ff5fa5916ff6f8f00ffc146062`
  - `UpdateStatus` do service: `completed`
  - `LANGGRAPH_RUNTIME_ENABLED=true` preservado na stack
- Smoke:
  - `https://pulse.orfi.com.br/health` respondeu `ok`
  - worktree local limpo apos o commit

## Current Status
- A rodada de alinhamento entre `Agents`, `Personas`, `conversation_policy` e `Conversations` esta publicada em producao.
- O backend agora roda a imagem do commit `717a864`.

## Next Recommended Step
- Validar com conversas reais no ambiente publicado se o tom e as respostas de objeção refletiram bem a configuracao editada nas telas.
- Se a resposta ainda estiver mecânica, o proximo ajuste deve ir para a configuracao estruturada de playbook, nao para mais ramificacoes no runtime central.

## 2026-03-25
- `sdr`: implementado login com Google mantendo a sessao interna atual baseada em `iron-session`.
- O que mudou:
  - backend ganhou provisionamento/autenticacao Google em [`backend/app/services/auth.py`](/home/ilki/sdr/backend/app/services/auth.py) e rota [`backend/app/api/v1/auth/routes.py`](/home/ilki/sdr/backend/app/api/v1/auth/routes.py)
  - schema novo em [`backend/app/schemas/auth.py`](/home/ilki/sdr/backend/app/schemas/auth.py)
  - frontend ganhou inicio e callback OAuth em [`frontend/app/api/auth/google/start/route.ts`](/home/ilki/sdr/frontend/app/api/auth/google/start/route.ts) e [`frontend/app/api/auth/google/callback/route.ts`](/home/ilki/sdr/frontend/app/api/auth/google/callback/route.ts)
  - tela [`frontend/app/(auth)/login/page.tsx`](/home/ilki/sdr/frontend/app/(auth)/login/page.tsx) agora oferece `Entrar com Google`
  - sessao temporaria do OAuth foi adicionada em [`frontend/lib/session.ts`](/home/ilki/sdr/frontend/lib/session.ts)
  - envs documentadas em [`frontend/.env.example`](/home/ilki/sdr/frontend/.env.example)
- Validacao:
  - `python3 -m py_compile backend/app/schemas/auth.py backend/app/services/auth.py backend/app/api/v1/auth/routes.py backend/tests/test_auth_google.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_auth_google.py` ok (`2 passed`)
  - `npm run typecheck` ok com Node 20 local (`nvm use 20`)

## Current Status
- O projeto agora suporta login por email/senha e por Google, ambos convergindo para a mesma sessao interna do frontend.
- O login Google ja foi configurado no ambiente publicado da stack `sdr`.

## Next Recommended Step
- Validar o fluxo completo de login via navegador com uma conta Google autorizada no projeto OAuth.
- Se o deploy estiver estavel, rotacionar o `GOOGLE_CLIENT_SECRET`, porque ele foi compartilhado em texto aberto durante a sessao.

## 2026-03-25
- `sdr`: consolidado commit, push e deploy da rodada de login com Google.
- Commits publicados:
  - `2e76bcc` `feat: add google login to sdr auth`
  - `29b2169` `fix: wrap login search params in suspense`
- Publicacao:
  - `main` enviado ao GitHub com sucesso
  - workflow `Build atendente3 images` concluiu com sucesso para o commit `29b2169bb1fdb9752fb27d184f13deafe38d1877`
- Deploy:
  - stack `sdr` reaplicada via Portainer (`stack id 35`, `endpointId 1`) usando [`deploy/atendente3/stack.yml`](/home/ilki/sdr/deploy/atendente3/stack.yml)
  - `BACKEND_IMAGE=ghcr.io/ilki70/sdr/backend:29b2169bb1fdb9752fb27d184f13deafe38d1877`
  - `FRONTEND_IMAGE=ghcr.io/ilki70/sdr/frontend:29b2169bb1fdb9752fb27d184f13deafe38d1877`
  - `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` adicionados ao ambiente da stack
- Validacao:
  - `backend/tests/test_auth_google.py` -> `2 passed`
  - `npm run typecheck` ok com Node 20
  - `sdr_backend`, `sdr_worker` e `sdr_frontend` convergiram com `UpdateStatus=completed`
  - `GET https://pulse.orfi.com.br/api/auth/providers` agora retorna o provider `google`

## 2026-03-25
- `sdr`: corrigido drift de schema no dashboard publicado.
- Causa:
  - o codigo em producao ja dependia das colunas `conversations.pipeline_status`, `summary` e `next_step`, mas o Postgres da stack ainda nao tinha recebido a migration [`007_conversation_pipeline_fields.py`](/home/ilki/sdr/backend/alembic/versions/007_conversation_pipeline_fields.py)
- O que mudou:
  - [`deploy/atendente3/stack.yml`](/home/ilki/sdr/deploy/atendente3/stack.yml) e [`deploy/sdr/stack.yml`](/home/ilki/sdr/deploy/sdr/stack.yml) agora sobem o `backend` com `alembic upgrade head && uvicorn ...`
  - stack `sdr` reaplicada via Portainer mantendo as imagens atuais do commit `29b2169bb1fdb9752fb27d184f13deafe38d1877`
- Validacao:
  - `sdr_backend` convergiu com `UpdateStatus=completed`
  - o endpoint do dashboard deixou de retornar `500` publico; sem sessao agora responde `401`, que e o esperado

## Current Status
- A stack publicada agora executa migrations automaticamente no startup do `backend`.
- O erro `column conversations.pipeline_status does not exist` deve estar resolvido no ambiente publicado.

## Next Recommended Step
- Validar no navegador autenticado se o dashboard abriu normalmente apos o redeploy.
- Commitar e publicar a alteracao dos manifests de deploy para nao perder esse bootstrap de migration em futuras reaplicacoes.

## 2026-03-25
- `sdr`: corrigido o caminho de uploads para ingestao de documentos na base de conhecimento.
- Causa:
  - o upload era salvo em `uploads/...` dentro do container que recebia o POST
  - a ingestao rodava no `worker`, outro container, sem esse mesmo filesystem local
  - o job acabava falhando com `404: Arquivo local nao encontrado`
- O que mudou:
  - [`backend/app/services/uploads.py`](/home/ilki/sdr/backend/app/services/uploads.py) agora usa `UPLOAD_ROOT` compartilhado, preferindo `/data/uploads`
  - [`backend/app/services/knowledge.py`](/home/ilki/sdr/backend/app/services/knowledge.py) passou a resolver `uploads/...` tambem dentro do storage compartilhado
  - adicionada regressao em [`backend/tests/test_upload_paths.py`](/home/ilki/sdr/backend/tests/test_upload_paths.py)
- Validacao:
  - `python3 -m py_compile backend/app/services/uploads.py backend/app/services/knowledge.py backend/tests/test_upload_paths.py` ok
  - `PYTHONPATH=/home/ilki/sdr/backend pytest -q backend/tests/test_upload_paths.py backend/tests/test_knowledge_youtube.py` ok (`4 passed`)

## Current Status
- Novos uploads de documentos devem ficar acessiveis tanto para `backend` quanto para `worker` na stack publicada.
- Jobs antigos que ja falharam por caminho local perdido podem precisar ser reenviados.

## Next Recommended Step
- Publicar o backend/worker com essa correcao e testar um novo upload de documento no ambiente publicado.
