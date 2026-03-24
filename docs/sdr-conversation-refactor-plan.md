# SDR Conversation Refactor Plan

## Objective

Reduzir a complexidade do comportamento conversacional do `sdr` e aproximar a arquitetura do padrao que funcionou no workflow `Isis 5`: memoria persistente, tools, debounce, handoff explicito e pos-processamento por canal.

## Problem Statement

O `langgraph_runtime` atual melhorou alguns casos, mas esta assumindo responsabilidades demais:

- interpretar a mensagem
- inferir contexto
- extrair slots
- decidir o proximo passo
- controlar tom da conversa
- compensar falhas de canal

Isso leva a uma espiral de regras. Cada nova falha vira mais codigo no runtime, e o resultado tende a continuar fragil.

## Architectural Direction

Trocar o modelo atual de "runtime cheio de regras" por um modelo em 5 camadas:

1. `ingestion`
2. `memory`
3. `conversation policy`
4. `tools`
5. `channel formatter`

O runtime deixa de ser o lugar onde tudo acontece.

## Target Shape

### 1. Ingestion Layer

Responsabilidade:
- receber mensagens
- agregar fragmentos curtos
- normalizar entrada multimodal

Onde encaixa:
- [`whatsapp.py`](/home/ilki/sdr/backend/app/services/whatsapp.py)
- [`whatsapp_gateway.py`](/home/ilki/sdr/backend/app/services/whatsapp_gateway.py)

O que aproveitar:
- `resolve_fragmented_inbound_text`
- cache curto em Redis
- `summarize_media_attachments`

O que mudar:
- transformar a fragmentacao atual em um debounce explicito por `conversation_id`
- considerar rajadas de mensagens como um turno logico unico antes do agente responder

### 2. Memory Layer

Responsabilidade:
- manter memoria util da conversa fora do prompt bruto
- registrar fatos confirmados e loops abertos

Estado recomendado:
- `confirmed_facts`
- `open_loops`
- `last_agent_commitment`
- `last_user_request`
- `conversation_mode`
- `handoff_state`
- `preferred_channel`
- `pending_actions`
- `follow_up_status`

Formato sugerido:
- `lead.metadata_json["conversation_runtime_state"]`
- complemento resumido em Redis para acesso rapido

O que aproveitar:
- [`conversation_context.py`](/home/ilki/sdr/backend/app/services/conversation_context.py)
- `Lead.metadata_json`
- `Conversation.summary`
- `Conversation.next_step`

O que mudar:
- parar de usar `slot_projection` como memoria principal
- promover estado semantico a primeiro nivel

### 3. Conversation Policy Layer

Responsabilidade:
- decidir como conversar
- decidir quando perguntar, confirmar, resumir, encerrar ou acionar tool

Regra central:
- o agente nao deve tentar preencher todos os slots na mao por codigo
- ele deve conversar usando:
  - estado persistido
  - historico resumido
  - regras simples de politica
  - ferramentas disponiveis

Politica minima sugerida:
- uma informacao por vez quando estiver coletando dado critico
- confirmar apenas antes de acao irreversivel ou relevante
- priorizar pedido explicito do lead antes de abrir nova pergunta
- nao reabrir topico encerrado sem sinal claro
- encerrar quando houver sinal forte de conclusao

Onde encaixa:
- novo modulo, por exemplo:
  - `backend/app/services/conversation_policy.py`

### 4. Tools Layer

Responsabilidade:
- executar operacoes de negocio com pre-condicoes claras

Tools sugeridas para o `sdr`:
- `knowledge_lookup`
- `lead_upsert`
- `proposal_request`
- `human_handoff`
- `schedule_follow_up`

Cada tool deve declarar:
- quando pode ser acionada
- quais dados minimos precisa
- que estado atualiza ao terminar

O que isso substitui:
- parte das regras procedurais hoje enterradas em [`langgraph_runtime.py`](/home/ilki/sdr/backend/app/services/langgraph_runtime.py)

### 5. Channel Formatter Layer

Responsabilidade:
- adaptar a resposta para o canal real

Para WhatsApp:
- quebrar mensagem longa
- evitar blocos densos
- preservar links
- separar payloads tecnicos
- respeitar estilo conversacional curto

Onde encaixa:
- novo modulo, por exemplo:
  - `backend/app/services/channel_formatter.py`

## What To Keep

Nao faz sentido jogar fora:

- [`conversation_context.py`](/home/ilki/sdr/backend/app/services/conversation_context.py)
- [`lead_capture.py`](/home/ilki/sdr/backend/app/services/lead_capture.py)
- [`runtime_router.py`](/home/ilki/sdr/backend/app/services/runtime_router.py)
- persistencia em `Lead`, `Conversation`, `Message`
- handoff e pipeline ja existentes
- cache em Redis

Essas pecas continuam, mas deixam de carregar o peso inteiro da conversa.

## What To Shrink

O modulo que precisa emagrecer e mudar de papel eh:

- [`langgraph_runtime.py`](/home/ilki/sdr/backend/app/services/langgraph_runtime.py)

Papel novo dele:
- coordenar estado
- chamar policy
- acionar tools
- devolver resposta estruturada

Papel que ele deve perder:
- dezenas de micro-regras de wording
- parser de toda nuance conversacional
- tentativa de cobrir todas as possibilidades no codigo

## Proposed Rollout

### Phase 1. Stabilize The Core Runtime Shape

Entregas:
- criar `conversation_runtime_state`
- mover estado semantico para esse objeto
- manter `slot_projection` apenas como apoio

Saida esperada:
- estado mais estavel entre turnos

### Phase 2. Add Debounce Before Response

Entregas:
- consolidar fragmentos curtos por janela pequena
- responder ao lote, nao a cada micropedaço

Saida esperada:
- menos respostas precipitadas

### Phase 3. Introduce Policy Layer

Entregas:
- criar `conversation_policy.py`
- mover decisao de tom, confirmacao e encerramento para esse modulo

Saida esperada:
- menos codigo procedural dentro do runtime

### Phase 4. Introduce Tools

Entregas:
- modelar tools internas do `sdr`
- proposal, handoff, knowledge, follow-up

Saida esperada:
- conversa mais orientada a tarefa e menos improvisada

### Phase 5. Add Channel Formatter

Entregas:
- formatador para WhatsApp
- fragmentacao natural de saida

Saida esperada:
- resposta mais humana no canal real

### Phase 6. Add Async Follow-Up

Entregas:
- job separado para classificar conversas paradas
- follow-up curto baseado em historico resumido

Saida esperada:
- menos dependencia do turno sincrono

## First Practical Cut

Se fosse para comecar agora sem refatorar tudo de uma vez, a ordem mais eficiente seria:

1. criar `conversation_runtime_state`
2. adaptar `runtime_router` para persisti-lo
3. extrair `conversation_policy.py`
4. simplificar `langgraph_runtime.py` para usar a policy
5. adicionar `channel_formatter.py`

## Success Criteria

Considerar a refatoracao bem-sucedida quando:

- o runtime encolher em complexidade
- a conversa deixar de depender de dezenas de excecoes codificadas
- o agente conseguir manter compromisso e assunto entre turnos
- WhatsApp parar de parecer "chat web copiado"
- handoff e follow-up funcionarem sem disputar contexto com o bot

## Conclusion

O proximo salto de qualidade do `sdr` nao depende de adicionar mais regra local ao runtime atual.

Depende de mudar a arquitetura para:

- memoria persistente semantica
- debounce
- policy
- tools
- formatter por canal

Esse plano permite fazer isso sem reescrever o produto inteiro.
