# Logica de Uso do Projeto

## 1. Visao geral
O projeto foi desenhado para operar um agente de vendas em tres camadas:

1. Atracao
- landing publica
- demo publica
- captura inicial de leads

2. Preparacao comercial
- cadastro de clientes e produtos
- ingestao de conhecimento
- configuracao de persona/playbook

3. Operacao e controle
- conversas persistidas
- metricas de qualificacao e handoff
- simulacao de cenarios antes de ligar canal real

O erro comum aqui seria tratar isso como um chatbot solto. Nao e esse o modelo. O sistema foi montado como esteira comercial com memoria, contexto e governanca.

## 2. Logica de uso por papel

### Quem opera o sistema
No MVP, o operador tipico e a sua equipe interna.

Essa equipe usa o sistema para:
- cadastrar um cliente que terceiriza vendas com voce
- modelar produtos e regras comerciais
- ensinar o agente usando RAG e playbook
- testar conversa
- acompanhar qualidade e preparar integracao com canais reais

### Quem conversa com a agente
Tem dois tipos de pessoa:
- visitante da landing/demo publica
- lead real atendido dentro da operacao do tenant

## 3. Fluxo correto de onboarding de um novo cliente

### Passo 1: criar o contexto base
1. Criar `client`
2. Criar `product`
3. Definir website, segmento e observacoes relevantes

Sem isso, o restante fica frouxo demais e o agente vira um respondedor generico.

### Passo 2: montar a base de conhecimento
Use a tela `Knowledge` para:
- subir PDFs
- subir textos
- ingerir URLs
- reindexar quando a fonte mudar

Objetivo:
- fazer o agente buscar fatos em fontes oficiais
- reduzir resposta inventada
- deixar a conversa ancorada em produto real

### Passo 3: publicar a persona comercial
Use a tela `Personas` para definir:
- tom de voz
- regras de abordagem
- limites comerciais
- roteiro de objecoes
- sinais de fechamento e follow-up

Logica:
- o RAG diz "o que e verdadeiro"
- a persona diz "como vender isso"

### Passo 4: testar no Agent Lab
Antes de colocar qualquer canal real, rode cenarios no `Agent Lab`:
- lead com pouco orcamento
- lead comparando com financiamento
- lead com urgencia
- lead com objecao de credibilidade
- lead que precisa de follow-up

Esse passo existe para evitar integrar um agente mal calibrado no WhatsApp.

## 4. Logica da landing publica

### O que a landing precisa fazer
A landing nao existe para explicar tudo. Ela precisa:
- posicionar a oferta
- mostrar a agente em acao
- abrir uma conversa comercial
- captar um caso real

### Demo publica
A demo publica:
- usa o backend real
- cria ou reaproveita `conversation_id`
- persiste mensagens
- transmite a resposta via SSE

Isso permite testar memoria real, e nao apenas um mock visual.

### Captura de lead
Quando um visitante preenche o formulario:
1. o frontend chama `/api/marketing/leads`
2. o backend cria `lead`
3. o backend cria `conversation`
4. o backend grava a mensagem inicial

Resultado:
- o comercial pode retomar exatamente de onde a landing parou

## 5. Logica do app logado

### Dashboard
O dashboard serve para responder:
- quantos leads existem
- quantos estao engajados
- quantas conversas ja iniciaram qualificacao
- quantas estao prontas para handoff
- qual a profundidade media das conversas

Importante:
- a regra de agregacao fica no backend
- o frontend so consome a visao consolidada

### Knowledge
Essa tela existe para governar conhecimento.

Use quando:
- o cliente mandar um PDF novo
- uma pagina do site mudar
- precisar reindexar o produto
- quiser testar se a recuperacao semantica achou o trecho certo

### Personas
Essa tela existe para governar comportamento comercial.

Use quando:
- o agente estiver educado demais e fechando pouco
- o agente estiver agressivo demais
- o cliente exigir limite formal de discurso
- quiser testar outra estrategia de objecao

### Integrations
Essa tela prepara a ponte com canais reais.

No estado atual, ela organiza o setup e o controle das integracoes. O dashboard ja passou a controlar o pareamento do WhatsApp via QR code usando um gateway Go com `whatsmeow`.

## 6. Logica do Agent Lab
O `Agent Lab` e o ambiente de homologacao do agente.

Ele serve para:
- abrir multiplas sessoes
- comparar conversas diferentes
- validar memoria por sessao
- validar follow-up
- validar se o agente usa o conhecimento certo

Forma correta de usar:
1. abrir uma sessao
2. rodar um cenario com 3 a 5 mensagens
3. observar se houve qualificacao
4. ajustar persona ou conhecimento
5. repetir

## 7. Logica de dados

### Tenant
Tudo acontece dentro de um `tenant`.

Consequencia pratica:
- clientes, produtos, leads, conversas, mensagens e metricas sao isolados por tenant

### Lead
Representa a oportunidade comercial.

Pode nascer de:
- landing
- demo
- agent lab
- integracao externa

### Conversation
Representa a unidade de memoria operacional.

Se o lead volta, o ideal e continuar uma conversa coerente, nao recomecar do zero sem contexto.

### Message
Representa cada troca persistida.

No caso do agente, a mensagem do assistente salva:
- intent
- confidence
- fragments
- follow_up_suggestion

Isso e o que permite gerar metricas operacionais depois.

## 8. Como testar o sistema do jeito certo

### Teste rapido
1. abrir a landing
2. abrir a demo
3. enviar uma pergunta
4. enviar uma segunda pergunta na mesma sessao
5. conferir se o `conversation_id` foi reaproveitado

### Teste operacional
1. login no app
2. abrir `Knowledge`
3. ingerir fontes
4. abrir `Personas`
5. publicar playbook
6. abrir `Agent Lab`
7. simular conversa
8. abrir `Dashboard`
9. criar o canal WhatsApp e gerar o QR code
10. conferir sinais de lead/conversa/handoff

### Teste de grounding
Use casos com resposta objetiva, como VINAC:
- seminovo
- adesao online
- regras do produto

Se o agente errar fato objetivo:
- primeiro corrija conhecimento
- depois persona
- so depois mexa no prompt do agente

## 9. O que ainda nao esta fechado
- webhook Chatwoot real
- score de lead e handoff mais ricos
- regressao automatica bloqueando respostas fora do playbook
- automacao total do funil publico ate canal real
- multiplas sessoes WhatsApp por gateway

## 10. Resumo pratico
Se for usar o sistema hoje, a sequencia correta e:

1. subir o ambiente
2. fazer login
3. cadastrar cliente e produto
4. ingerir conhecimento
5. publicar persona
6. testar no Agent Lab
7. testar landing/demo publica
8. acompanhar dashboard
9. so depois ligar canal real

