"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import { EmptyState } from "@/components/shared/empty-state";

type Client = {
  id: string;
  name: string;
  segment: string | null;
  website_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState({ name: "", segment: "consorcio_de_veiculos", website_url: "" });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setClients(await fetchJson<Client[]>("/api/proxy/clients"));
  }

  useEffect(() => {
    void load().catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar clientes."));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await fetchJson<Client>("/api/proxy/clients", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          segment: form.segment,
          website_url: form.website_url || undefined,
          status: "active",
        }),
      });
      setForm({ name: "", segment: "consorcio_de_veiculos", website_url: "" });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar cliente.");
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Operations</p>
        <h1 className="mt-3 text-3xl font-semibold">Clientes</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Cadastre empresas, normalize segmento e mantenha o contexto comercial que alimenta produtos, regras e agentes.
        </p>
      </section>

      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <form onSubmit={handleSubmit} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Novo cliente</p>
          <input className="mt-4 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none" placeholder="Nome do cliente" value={form.name} onChange={(event) => setForm((previous) => ({ ...previous, name: event.target.value }))} />
          <input className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none" placeholder="Segmento" value={form.segment} onChange={(event) => setForm((previous) => ({ ...previous, segment: event.target.value }))} />
          <input className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none" placeholder="https://site-do-cliente.com.br" value={form.website_url} onChange={(event) => setForm((previous) => ({ ...previous, website_url: event.target.value }))} />
          <button className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black" type="submit">Criar cliente</button>
          {error ? <p className="mt-3 text-sm text-red-100">{error}</p> : null}
        </form>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-semibold">Inventário</h2>
            <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">{clients.length} itens</span>
          </div>
          <div className="mt-5 space-y-3">
            {clients.map((client) => (
              <article key={client.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong>{client.name}</strong>
                  <span className="text-xs uppercase tracking-wide text-white/50">{client.status}</span>
                </div>
                <p className="mt-2 text-sm text-white/70">{client.segment || "Sem segmento"}</p>
                <p className="mt-2 text-xs text-white/50">{client.website_url || "Sem site cadastrado"}</p>
                <p className="mt-3 text-xs text-white/40">Atualizado em {formatDateTimeSP(client.updated_at)}</p>
              </article>
            ))}
            {clients.length === 0 ? (
              <EmptyState
                title="Nenhum cliente cadastrado."
                description="Crie o primeiro cliente para destravar produtos, regras de comissão e agentes por conta."
              />
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
