"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type QualityReview = {
  conversation_id: string;
  title: string;
  agent_id: string | null;
  agent_name: string | null;
  status: string;
  score: number;
  findings: string[];
  reviewed_at: string;
};

function statusTone(status: string): string {
  if (status === "pass") {
    return "border-emerald-400/30 bg-emerald-500/10 text-emerald-100";
  }
  if (status === "watch") {
    return "border-amber-400/30 bg-amber-500/10 text-amber-100";
  }
  return "border-red-400/30 bg-red-500/10 text-red-100";
}

export default function QualityPage() {
  const [reviews, setReviews] = useState<QualityReview[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchJson<QualityReview[]>("/api/proxy/quality/reviews")
      .then(setReviews)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar monitoria."));
  }, []);

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Quality Monitor</p>
        <h1 className="mt-3 text-3xl font-semibold">Monitoria basica</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Avaliacao heuristica das conversas mais recentes, com score, status e achados para revisao rapida do time.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}

      <section className="grid gap-4 lg:grid-cols-2">
        {reviews.map((review) => (
          <article key={review.conversation_id} className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <strong>{review.title}</strong>
                <p className="mt-1 text-xs text-white/45">{review.agent_name || "Agente nao identificado"}</p>
              </div>
              <div className={`rounded-full border px-3 py-1 text-xs uppercase tracking-wide ${statusTone(review.status)}`}>
                {review.status} • {review.score}
              </div>
            </div>
            <p className="mt-3 text-xs text-white/45">Revisado em {formatDateTimeSP(review.reviewed_at)}</p>
            <ul className="mt-4 space-y-2 text-sm text-white/70">
              {review.findings.length > 0 ? (
                review.findings.map((finding) => <li key={finding}>{finding}</li>)
              ) : (
                <li>Nenhum achado relevante na heuristica atual.</li>
              )}
            </ul>
          </article>
        ))}
        {!error && reviews.length === 0 ? (
          <article className="rounded-[24px] border border-dashed border-white/15 bg-black/20 p-5 text-sm text-white/60">
            Ainda nao ha conversas suficientes para monitoria.
          </article>
        ) : null}
      </section>
    </main>
  );
}
