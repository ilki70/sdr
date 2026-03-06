# PRD Frontend - Agente Vendedor IA

## 1) Resumo do produto
- Plataforma web para operacao comercial com bot de IA especialista em vendas.
- Publico: empresas que querem terceirizar vendas.
- Entrega MVP: landing simples + app logado.
- Diferencial: bot com RAG, busca web restrita e operacao via Chatwoot.

## 2) Requisitos funcionais (frontend/UX)
- Login com sessao segura (iron-session).
- Gestao de clientes/produtos/conteudo de conhecimento.
- Upload com drag and drop para documentos e midias.
- Configuracao de persona e versoes de prompt.
- Integracao Chatwoot via setup de webhook.
- Tela de conversas com streaming SSE.
- Dashboard de metricas (sem reproduzir funil do Chatwoot).
- Painel de comissoes com simulacao e alteracao de regras.

## 3) Mapa de paginas (App Router)
- `app/(marketing)/page.tsx`: landing com proposta de valor e CTA.
- `app/(marketing)/demo/page.tsx`: simulacao rapida do bot.
- `app/(auth)/login/page.tsx`: autenticacao.
- `app/(app)/layout.tsx`: shell autenticado.
- `app/(app)/dashboard/page.tsx`: KPIs e filtros.
- `app/(app)/clients/page.tsx` e `app/(app)/clients/[id]/page.tsx`.
- `app/(app)/products/page.tsx` e `app/(app)/products/[id]/page.tsx`.
- `app/(app)/knowledge/page.tsx`: ingestao RAG.
- `app/(app)/personas/page.tsx`: edicao/publicacao.
- `app/(app)/integrations/page.tsx`: Chatwoot setup.
- `app/(app)/conversations/page.tsx` e `app/(app)/conversations/[id]/page.tsx`.
- `app/(app)/sales/page.tsx`.
- `app/(app)/commissions/page.tsx`.
- `app/(app)/settings/page.tsx`.

## 4) Arvore de componentes
- Layout:
- `components/layout/app-shell.tsx`
- `components/layout/command-bar.tsx`
- `components/layout/tenant-switcher.tsx`
- Metrics:
- `components/metrics/kpi-card.tsx`
- `components/metrics/metric-chart.tsx`
- `components/metrics/metric-filters.tsx`
- Knowledge:
- `components/knowledge/dropzone-upload.tsx`
- `components/knowledge/source-list.tsx`
- Chat:
- `components/chat/chat-thread.tsx`
- `components/chat/message-bubble.tsx`
- `components/chat/typing-stream.tsx`
- Persona:
- `components/persona/persona-form.tsx`
- `components/persona/version-timeline.tsx`
- Comissoes:
- `components/commissions/rule-table.tsx`
- `components/commissions/rule-form.tsx`
- `components/commissions/rule-simulator.tsx`
- Shared:
- `components/shared/loading-skeleton.tsx`
- `components/shared/error-state.tsx`
- `components/shared/empty-state.tsx`

## 5) Design system
- Direcao visual: "Sales Command Center" (autoral, sem layout padrao).
- Tipografia:
- Titulos: Space Grotesk.
- Texto/UI: IBM Plex Sans.
- Tokens de cor:
- `--bg-0: #0B1020`
- `--bg-1: #111831`
- `--surface: #18233F`
- `--accent: #19C37D`
- `--warning: #F59E0B`
- `--danger: #EF4444`
- `--info: #38BDF8`
- Motion:
- transicoes 120-180ms.
- entrada em stagger para cards.
- destaque visual em atualizacao de metricas.
- Base de componentes: shadcn/ui + componentes custom para chat/metricas.

## 6) Auth flow (iron-session no Next.js)
- Login envia credenciais para `/api/auth/login`.
- API route cria sessao httpOnly.
- Middleware protege rotas `/(app)`.
- Proxy interno injeta `X-User-Id` e `X-Tenant-Id` nas chamadas ao FastAPI.
- Logout invalida sessao e cookie.

## 7) API integration layer (proxy, hooks, SSE)
- `lib/api/fetcher.ts`: timeout, tratamento de erro padrao, request id.
- `lib/api/client.ts`: funcoes tipadas por dominio.
- Hooks:
- `use-session`
- `use-tenant`
- `use-metrics`
- `use-commission-rules`
- `use-sse-chat`
- Rotas proxy em `app/api/*` para evitar chamada direta ao backend.

## 8) Requisitos nao-funcionais (frontend)
- Responsividade:
- desktop + mobile web com foco operacional em desktop.
- UX states:
- loading, vazio e erro em todas as telas principais.
- Acessibilidade:
- labels/aria para formularios e navegacao por teclado.
- Performance:
- dashboard p95 <= 2s (janela ate 30 dias).

## 9) Security checklist (frontend)
- [ ] Sem tokens em localStorage/sessionStorage.
- [ ] Sem expor IDs internos sensiveis em logs/URL publica.
- [ ] Sem variaveis sensiveis com prefixo `NEXT_PUBLIC_`.
- [ ] Erros de UI sem stack trace interno.
- [ ] Upload validado antes do envio (tipo/tamanho).
- [ ] Todo request via proxy autenticado.

## 10) Stack e dependencias (package.json)
```json
{
  "name": "agente-vendedor-frontend",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.7.0",
    "tailwindcss": "^4.0.0",
    "@radix-ui/react-dialog": "latest",
    "@radix-ui/react-dropdown-menu": "latest",
    "class-variance-authority": "latest",
    "clsx": "latest",
    "lucide-react": "latest",
    "zod": "latest"
  }
}
```
