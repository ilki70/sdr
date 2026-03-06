"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP, formatMoneyBRL } from "@/lib/datetime";

type Client = { id: string; name: string };
type Product = {
  id: string;
  client_id: string;
  name: string;
  description: string | null;
  base_price: string | null;
  currency: string;
  updated_at: string;
};

export default function ProductsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState({ client_id: "", name: "", description: "", base_price: "1000" });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [clientItems, productItems] = await Promise.all([
      fetchJson<Client[]>("/api/proxy/clients"),
      fetchJson<Product[]>("/api/proxy/products"),
    ]);
    setClients(clientItems);
    setProducts(productItems);
    if (!form.client_id && clientItems[0]) {
      setForm((previous) => ({ ...previous, client_id: clientItems[0].id }));
    }
  }

  useEffect(() => {
    void load().catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar produtos."));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await fetchJson<Product>("/api/proxy/products", {
        method: "POST",
        body: JSON.stringify({
          client_id: form.client_id,
          name: form.name,
          description: form.description || undefined,
          base_price: Number(form.base_price),
          currency: "BRL",
          sales_terms_json: null,
          is_active: true,
        }),
      });
      setForm((previous) => ({ ...previous, name: "", description: "", base_price: "1000" }));
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar produto.");
    }
  }

  return (
    <main className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <form onSubmit={handleSubmit} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Novo produto</p>
        <select className="mt-4 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={form.client_id} onChange={(event) => setForm((previous) => ({ ...previous, client_id: event.target.value }))}>
          {clients.map((client) => (
            <option key={client.id} value={client.id}>{client.name}</option>
          ))}
        </select>
        <input className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" placeholder="Nome do produto" value={form.name} onChange={(event) => setForm((previous) => ({ ...previous, name: event.target.value }))} />
        <textarea className="mt-3 min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" placeholder="Descrição comercial" value={form.description} onChange={(event) => setForm((previous) => ({ ...previous, description: event.target.value }))} />
        <input className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" placeholder="Preço base" value={form.base_price} onChange={(event) => setForm((previous) => ({ ...previous, base_price: event.target.value }))} />
        <button className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black" type="submit">Criar produto</button>
        {error ? <p className="mt-3 text-sm text-red-100">{error}</p> : null}
      </form>

      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold">Produtos</h1>
        <div className="mt-5 space-y-3">
          {products.map((product) => (
            <article key={product.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <strong>{product.name}</strong>
                <span className="text-sm text-[var(--accent)]">{formatMoneyBRL(product.base_price)}</span>
              </div>
              <p className="mt-2 text-sm text-white/70">{product.description || "Sem descrição"}</p>
              <p className="mt-3 text-xs text-white/40">Atualizado em {formatDateTimeSP(product.updated_at)}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
