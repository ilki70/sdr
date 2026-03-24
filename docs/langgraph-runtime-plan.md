# LangGraph Runtime Plan

## Objective

Substituir o motor atual de conversa do `sdr` por um runtime stateful dentro do proprio backend, usando a biblioteca `langgraph` como base e sem depender de plataforma externa ou licenca comercial.

## Status

Este plano continua valido como base tecnica do runtime, mas ja nao deve ser interpretado como "crescer a inteligencia dentro de um unico arquivo de runtime".

Depois da analise do workflow `Isis 5`, a direcao recomendada passou a ser:

- runtime mais fino
- memoria semantica persistente
- tools com pre-condicoes
- debounce de mensagens
- formatter por canal

Referencia complementar:
- [`docs/n8n-isis-conversation-patterns.md`](/home/ilki/sdr/docs/n8n-isis-conversation-patterns.md)
- [`docs/sdr-conversation-refactor-plan.md`](/home/ilki/sdr/docs/sdr-conversation-refactor-plan.md)

## Why This Direction

- evita o bloqueio de licenca visto no `Rasa CALM`
- evita depender de plataforma SaaS para o core do atendimento
- preserva o banco, CRM, inbox e canais ja existentes
- permite controlar slots, handoff e proximo passo no mesmo backend FastAPI

## Runtime Shape

- `backend/app/services/langgraph_runtime.py`
- entrada: mensagem atual, historico recente, perfil do lead e metadata persistida
- saida: `reply_text`, `reply_fragments`, `follow_up_suggestion`, `handoff_requested` e `slot_projection`

## Initial Flow

1. detectar handoff humano
2. consolidar slots ja persistidos
3. extrair slots novos da mensagem atual
4. decidir o proximo slot faltante
5. responder com a proxima pergunta ou liberar simulacao

## Slot Order

- `lead_name`
- `asset_type`
- `goal`
- `asset_value`
- `timeline`
- `cpf`
- `phone`

`lance` fica como complementar, nao como bloqueio do fluxo principal.

## Rollout

1. `agent-lab` por feature flag `LANGGRAPH_RUNTIME_ENABLED`
2. validacao local dos principais cenarios de SDR
3. migracao do WhatsApp para o mesmo runtime
4. desativacao do runtime legado
