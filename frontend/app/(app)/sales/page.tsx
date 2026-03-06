"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP, formatMoneyBRL } from "@/lib/datetime";

type Sale = {
  id: string;
  product_id: string;
  status: string;
  amount: string;
  currency: string;
  closed_at: string | null;
  source_channel: string | null;
  notes: string | null;
  updated_at: string;
};

export default function SalesPage() {
  const [sales, setSales] = useState<Sale[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchJson<Sale[]>("/api/proxy/sales")
      .then(setSales)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar vendas."));
  }, []);

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold">Vendas</h1>
        <p className="mt-2 text-sm text-white/70">Lista inicial das vendas registradas no tenant. Conforme o fluxo comercial evoluir, essa área passa a consolidar fechamento e comissão aplicada.</p>
      </section>
      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      <div className="space-y-3">
        {sales.length === 0 ? (
          <div className="rounded-[24px] border border-dashed border-white/15 bg-black/20 px-5 py-8 text-sm text-white/60">Nenhuma venda registrada ainda.</div>
        ) : null}
        {sales.map((sale) => (
          <article key={sale.id} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
            <div className="flex items-center justify-between gap-3">
              <strong>Venda {sale.id.slice(0, 8)}</strong>
              <span className="text-sm text-[var(--accent)]">{formatMoneyBRL(sale.amount)}</span>
            </div>
            <p className="mt-2 text-sm text-white/70">{sale.status} • {sale.source_channel || "canal não informado"}</p>
            <p className="mt-3 text-xs text-white/40">Atualizado em {formatDateTimeSP(sale.updated_at)}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
