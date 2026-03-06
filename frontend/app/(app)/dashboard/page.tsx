"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type DashboardJob = {
  id: string;
  job_type: string;
  status: string;
  created_at: string;
  product_id: string;
};

type DashboardConversation = {
  id: string;
  status: string;
  updated_at: string;
  title: string;
  message_count: number;
  last_message_preview: string | null;
};

type EvaluationRun = {
  id: string;
  status: string;
  evaluation_type: string;
  summary_json: Record<string, unknown> | null;
  created_at: string;
};

type DashboardOverview = {
  client_count: number;
  product_count: number;
  conversation_count: number;
  active_rule_count: number;
  active_integration_count: number;
  sales_count: number;
  revenue_total: string;
  recent_jobs: DashboardJob[];
  recent_conversations: DashboardConversation[];
  latest_evaluation: EvaluationRun | null;
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const overview = await fetchJson<DashboardOverview>("/api/proxy/dashboard/overview");
        if (!cancelled) {
          setData(overview);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao carregar dashboard.");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const cards = [
    { label: "Clientes", value: data?.client_count ?? 0 },
    { label: "Produtos", value: data?.product_count ?? 0 },
    { label: "Conversas", value: data?.conversation_count ?? 0 },
    { label: "Regras de comissao", value: data?.active_rule_count ?? 0 },
    { label: "Integracoes", value: data?.active_integration_count ?? 0 },
    { label: "Vendas", value: data?.sales_count ?? 0 },
  ];

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Control Room</p>
        <h1 className="mt-3 text-3xl font-semibold">Dashboard operacional</h1>
        <p className="mt-2 text-sm text-white/70">
          Referencia horaria fixa em Sao Paulo. Use este painel para ver setup comercial, atividade recente e resultado das avaliacoes automaticas.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <article key={card.label} className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <p className="text-sm text-white/60">{card.label}</p>
            <p className="mt-3 text-3xl font-semibold">{card.value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Receita total registrada</p>
          <p className="mt-3 text-3xl font-semibold">R$ {data?.revenue_total ?? "0.00"}</p>
        </article>
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Ambiente</p>
          <p className="mt-3 text-lg font-semibold">America/Sao_Paulo</p>
          <p className="mt-2 text-xs text-white/50">Todas as datas exibidas neste dashboard usam esse fuso.</p>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-semibold">Atividade recente</h2>
          <div className="mt-5 space-y-3">
            {data?.recent_jobs.map((job) => (
              <article key={job.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">{job.job_type}</strong>
                  <span className="text-xs uppercase tracking-wide text-white/50">{job.status}</span>
                </div>
                <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(job.created_at)}</p>
                <p className="mt-2 text-xs text-white/35">Produto {job.product_id.slice(0, 8)}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="space-y-5">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold">Ultima avaliacao</h2>
            {data?.latest_evaluation ? (
              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-sm text-white/70">{data.latest_evaluation.evaluation_type}</p>
                <p className="mt-2 text-2xl font-semibold">{data.latest_evaluation.status}</p>
                <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(data.latest_evaluation.created_at)}</p>
                <p className="mt-3 text-sm text-white/70">
                  Media: {String(data.latest_evaluation.summary_json?.average_score ?? "-")} | Aprovados:{" "}
                  {String(data.latest_evaluation.summary_json?.passed_count ?? "-")}
                </p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-white/60">Nenhuma avaliacao automatica encontrada.</p>
            )}
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold">Conversas recentes</h2>
            <div className="mt-4 space-y-3">
              {data?.recent_conversations.map((conversation) => (
                <article key={conversation.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <strong className="text-sm">{conversation.title}</strong>
                  <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(conversation.updated_at)}</p>
                  <p className="mt-2 text-sm text-white/65">{conversation.last_message_preview || "Sem mensagens ainda."}</p>
                  <p className="mt-2 text-xs uppercase tracking-wide text-white/35">{conversation.message_count} mensagens</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
