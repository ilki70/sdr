"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import type { AgentOption, ConversationSummary, KnowledgeSource, ProductOption } from "./_shared";

export default function ConsorciosPage() {
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsLoading(true);
      setError(null);
      try {
        const [agentItems, productItems, conversationItems] = await Promise.all([
          fetchJson<AgentOption[]>("/api/proxy/agents"),
          fetchJson<ProductOption[]>("/api/proxy/products"),
          fetchJson<ConversationSummary[]>("/api/proxy/messages/conversations"),
        ]);
        if (cancelled) {
          return;
        }
        setAgents(agentItems);
        setProducts(productItems);
        setConversations(conversationItems);
        if (productItems[0]?.id) {
          const knowledge = await fetchJson<KnowledgeSource[]>(
            `/api/proxy/knowledge/sources?product_id=${encodeURIComponent(productItems[0].id)}`,
          );
          if (!cancelled) {
            setSources(knowledge);
          }
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao carregar o hub de consorcios.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const cards = [
    { href: "/consorcios/playbook", label: "Playbook", description: "Configuracao do agente, qualificacao, objeções e compliance." },
    { href: "/consorcios/knowledge", label: "Knowledge", description: "Docs, URLs, YouTube e diffs da base de conhecimento." },
    { href: "/consorcios/inbox", label: "Inbox", description: "Conversations, handoff humano e visao operacional." },
  ];

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(37,211,102,0.10),rgba(255,255,255,0.04))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Consorcios Studio</p>
        <h1 className="mt-3 text-3xl font-semibold">Central operacional de consórcios</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Acesso rápido aos blocos do estúdio: playbook do agente, base de conhecimento e inbox do time.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}

      <section className="grid gap-4 md:grid-cols-3">
        {cards.map((card) => (
          <article key={card.href} className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">{card.label}</p>
            <p className="mt-2 text-sm text-white/72">{card.description}</p>
            <Link href={card.href} className="mt-4 inline-flex rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
              Abrir {card.label.toLowerCase()}
            </Link>
          </article>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Agentes</p>
          <p className="mt-3 text-3xl font-semibold">{agents.length}</p>
          <p className="mt-2 text-xs text-white/45">{isLoading ? "Atualizando..." : "Disponiveis no tenant"}</p>
        </article>
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Produtos</p>
          <p className="mt-3 text-3xl font-semibold">{products.length}</p>
          <p className="mt-2 text-xs text-white/45">Produtos conectados ao conhecimento</p>
        </article>
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Conversas recentes</p>
          <p className="mt-3 text-3xl font-semibold">{conversations.length}</p>
          <p className="mt-2 text-xs text-white/45">Handoff e acompanhamento do time</p>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Fontes mais recentes</h2>
              <p className="mt-1 text-sm text-white/60">Inventario do produto carregado no hub.</p>
            </div>
            <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/55">{sources.length} itens</span>
          </div>
          <div className="mt-4 space-y-3">
            {sources.slice(0, 5).map((source) => (
              <article key={source.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">{source.source_type}</strong>
                  <span className="text-xs uppercase tracking-wide text-white/45">{source.status}</span>
                </div>
                <p className="mt-2 break-all text-xs text-white/60">{source.source_ref}</p>
                <p className="mt-2 text-[11px] text-white/40">Atualizado em {formatDateTimeSP(source.updated_at)}</p>
              </article>
            ))}
            {sources.length === 0 ? <p className="text-sm text-white/50">Nenhuma fonte ativa.</p> : null}
          </div>
        </article>

        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-semibold">Fluxo recomendado</h2>
          <ol className="mt-4 space-y-3 text-sm text-white/70">
            <li>1. Configurar o playbook do agente em {`/consorcios/playbook`}.</li>
            <li>2. Ingerir docs, URLs e videos em {`/consorcios/knowledge`}.</li>
            <li>3. Monitorar a fila operacional em {`/consorcios/inbox`}.</li>
            <li>4. Handoff para a Turn2C apenas no momento de fechamento.</li>
          </ol>
          <div className="mt-5 rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm text-white/65">
            A Central foi separada em subareas explicitas para o time operar sem misturar configuracao, conhecimento e acompanhamento.
          </div>
        </article>
      </section>
    </main>
  );
}
