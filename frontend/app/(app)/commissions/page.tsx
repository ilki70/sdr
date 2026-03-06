"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type Client = { id: string; name: string };
type Product = { id: string; name: string };
type Rule = {
  id: string;
  name: string;
  rule_scope: string;
  fixed_percent: string | null;
  client_id: string | null;
  product_id: string | null;
  condition_type: string;
  updated_at: string;
};

export default function CommissionsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [form, setForm] = useState({
    name: "Regra padrão",
    rule_scope: "product",
    client_id: "",
    product_id: "",
    fixed_percent: "2.50",
  });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [clientItems, productItems, ruleItems] = await Promise.all([
      fetchJson<Client[]>("/api/proxy/clients"),
      fetchJson<Product[]>("/api/proxy/products"),
      fetchJson<Rule[]>("/api/proxy/commissions/rules"),
    ]);
    setClients(clientItems);
    setProducts(productItems);
    setRules(ruleItems);
    setForm((previous) => ({
      ...previous,
      client_id: previous.client_id || clientItems[0]?.id || "",
      product_id: previous.product_id || productItems[0]?.id || "",
    }));
  }

  useEffect(() => {
    void load().catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar regras."));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await fetchJson<Rule>("/api/proxy/commissions/rules", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          priority: 100,
          rule_scope: form.rule_scope,
          client_id: form.client_id || null,
          product_id: form.product_id || null,
          fixed_percent: Number(form.fixed_percent),
          condition_type: "panel_default",
          conditions_json: { source: "ui" },
          active_from: new Date().toISOString(),
          active_to: null,
          is_active: true,
        }),
      });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar regra.");
    }
  }

  return (
    <main className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <form onSubmit={handleSubmit} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Nova regra</p>
        <input className="mt-4 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={form.name} onChange={(event) => setForm((previous) => ({ ...previous, name: event.target.value }))} />
        <select className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={form.rule_scope} onChange={(event) => setForm((previous) => ({ ...previous, rule_scope: event.target.value }))}>
          <option value="product">Por produto</option>
          <option value="client">Por cliente</option>
        </select>
        <select className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={form.client_id} onChange={(event) => setForm((previous) => ({ ...previous, client_id: event.target.value }))}>
          {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
        </select>
        <select className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={form.product_id} onChange={(event) => setForm((previous) => ({ ...previous, product_id: event.target.value }))}>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
        </select>
        <input className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={form.fixed_percent} onChange={(event) => setForm((previous) => ({ ...previous, fixed_percent: event.target.value }))} />
        <button className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black" type="submit">Criar regra</button>
        {error ? <p className="mt-3 text-sm text-red-100">{error}</p> : null}
      </form>

      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold">Comissões</h1>
        <div className="mt-5 space-y-3">
          {rules.map((rule) => (
            <article key={rule.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <strong>{rule.name}</strong>
                <span className="text-sm text-[var(--accent)]">{rule.fixed_percent || "-"}%</span>
              </div>
              <p className="mt-2 text-sm text-white/70">{rule.rule_scope} • {rule.condition_type}</p>
              <p className="mt-3 text-xs text-white/40">Atualizado em {formatDateTimeSP(rule.updated_at)}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
