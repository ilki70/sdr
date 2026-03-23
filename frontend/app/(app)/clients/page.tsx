"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import { EmptyState } from "@/components/shared/empty-state";

type Client = {
  id: string;
  tenant_id: string;
  name: string;
  segment: string | null;
  website_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

type ClientEditorForm = {
  name: string;
  segment: string;
  website_url: string;
  status: string;
};

const createTemplate: ClientEditorForm = {
  name: "",
  segment: "consorcio_de_veiculos",
  website_url: "",
  status: "active",
};

function buildEditorForm(client?: Client | null): ClientEditorForm {
  return {
    name: client?.name || "",
    segment: client?.segment || "",
    website_url: client?.website_url || "",
    status: client?.status || "active",
  };
}

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [createForm, setCreateForm] = useState(createTemplate);
  const [editorForm, setEditorForm] = useState<ClientEditorForm>(buildEditorForm());
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedClient = useMemo(
    () => clients.find((client) => client.id === selectedClientId) || null,
    [clients, selectedClientId],
  );

  async function loadClients(preferredClientId?: string) {
    setIsLoading(true);
    setError(null);
    try {
      const items = await fetchJson<Client[]>("/api/proxy/clients");
      setClients(items);
      const nextSelectedId = preferredClientId || selectedClientId || items[0]?.id || "";
      setSelectedClientId(nextSelectedId);
      setCreateForm((previous) => ({ ...previous, status: previous.status || "active" }));
      if (nextSelectedId) {
        const nextClient = items.find((client) => client.id === nextSelectedId) || null;
        setEditorForm(buildEditorForm(nextClient));
      } else {
        setEditorForm(buildEditorForm());
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar clientes.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadClients();
  }, []);

  useEffect(() => {
    if (selectedClient) {
      setEditorForm(buildEditorForm(selectedClient));
    }
  }, [selectedClient]);

  async function handleCreateClient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await fetchJson<Client>("/api/proxy/clients", {
        method: "POST",
        body: JSON.stringify({
          name: createForm.name,
          segment: createForm.segment || undefined,
          website_url: createForm.website_url || undefined,
          status: createForm.status,
        }),
      });
      setNotice(`Cliente ${created.name} criado com sucesso.`);
      setCreateForm(createTemplate);
      await loadClients(created.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar cliente.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSaveClient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedClient) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<Client>(`/api/proxy/clients/${selectedClient.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editorForm.name,
          segment: editorForm.segment || undefined,
          website_url: editorForm.website_url || undefined,
          status: editorForm.status,
        }),
      });
      setNotice(`Cliente ${editorForm.name} atualizado.`);
      await loadClients(selectedClient.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao atualizar cliente.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteClient() {
    if (!selectedClient) {
      return;
    }
    const confirmed = window.confirm(`Excluir o cliente "${selectedClient.name}"?`);
    if (!confirmed) {
      return;
    }
    setIsDeleting(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson(`/api/proxy/clients/${selectedClient.id}`, { method: "DELETE" });
      setNotice(`Cliente ${selectedClient.name} excluído.`);
      await loadClients();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao excluir cliente.");
    } finally {
      setIsDeleting(false);
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

      {(error || notice) && (
        <section className={`rounded-2xl border px-4 py-3 text-sm ${error ? "border-red-400/30 bg-red-500/10 text-red-100" : "border-emerald-400/30 bg-emerald-500/10 text-emerald-50"}`}>
          {error || notice}
        </section>
      )}

      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <form onSubmit={handleCreateClient} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Novo cliente</p>
          <label className="mt-4 block text-xs uppercase tracking-[0.18em] text-white/45">Nome</label>
          <input
            className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
            placeholder="Nome do cliente"
            value={createForm.name}
            onChange={(event) => setCreateForm((previous) => ({ ...previous, name: event.target.value }))}
          />
          <label className="mt-3 block text-xs uppercase tracking-[0.18em] text-white/45">Segmento</label>
          <input
            className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
            placeholder="consorcio_de_veiculos"
            value={createForm.segment}
            onChange={(event) => setCreateForm((previous) => ({ ...previous, segment: event.target.value }))}
          />
          <label className="mt-3 block text-xs uppercase tracking-[0.18em] text-white/45">Website</label>
          <input
            className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
            placeholder="https://site-do-cliente.com.br"
            value={createForm.website_url}
            onChange={(event) => setCreateForm((previous) => ({ ...previous, website_url: event.target.value }))}
          />
          <label className="mt-3 block text-xs uppercase tracking-[0.18em] text-white/45">Status</label>
          <select
            className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
            value={createForm.status}
            onChange={(event) => setCreateForm((previous) => ({ ...previous, status: event.target.value }))}
          >
            <option value="active">active</option>
            <option value="paused">paused</option>
            <option value="archived">archived</option>
          </select>
          <button
            className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isCreating}
          >
            {isCreating ? "Criando..." : "Criar cliente"}
          </button>
        </form>

        <section className="grid gap-5 lg:grid-cols-[280px_1fr]">
          <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-2xl font-semibold">Inventário</h2>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
                {clients.length} itens
              </span>
            </div>
            <div className="mt-5 space-y-3">
              {clients.map((client) => {
                const isSelected = client.id === selectedClientId;
                return (
                  <button
                    key={client.id}
                    type="button"
                    onClick={() => setSelectedClientId(client.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      isSelected ? "border-[var(--accent)] bg-[var(--accent)]/10" : "border-white/10 bg-black/20 hover:border-white/20"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <strong className="block text-sm">{client.name}</strong>
                        <p className="mt-1 text-xs text-white/45">{client.segment || "Sem segmento"}</p>
                      </div>
                      <span className="rounded-full bg-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-white/50">
                        {client.status}
                      </span>
                    </div>
                    <p className="mt-3 text-xs text-white/50">{client.website_url || "Sem site cadastrado"}</p>
                    <p className="mt-1 text-xs text-white/40">Atualizado em {formatDateTimeSP(client.updated_at)}</p>
                  </button>
                );
              })}
              {clients.length === 0 ? (
                <EmptyState
                  title="Nenhum cliente cadastrado."
                  description="Crie o primeiro cliente para destravar produtos, regras de comissão e agentes por conta."
                />
              ) : null}
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold">Editar cliente</h2>
                <p className="mt-1 text-sm text-white/55">
                  {selectedClient ? "Atualize os dados do cliente selecionado abaixo." : "Selecione um cliente na lista para editar."}
                </p>
              </div>
              {selectedClient ? (
                <button
                  type="button"
                  onClick={handleDeleteClient}
                  disabled={isDeleting}
                  className="rounded-full border border-red-400/30 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isDeleting ? "Excluindo..." : "Excluir cliente"}
                </button>
              ) : null}
            </div>

            {selectedClient ? (
              <form onSubmit={handleSaveClient} className="mt-5 grid gap-4 lg:grid-cols-[1fr_280px]">
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Nome</label>
                      <input
                        className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                        value={editorForm.name}
                        onChange={(event) => setEditorForm((previous) => ({ ...previous, name: event.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Segmento</label>
                      <input
                        className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                        value={editorForm.segment}
                        onChange={(event) => setEditorForm((previous) => ({ ...previous, segment: event.target.value }))}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Website</label>
                    <input
                      className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                      value={editorForm.website_url}
                      onChange={(event) => setEditorForm((previous) => ({ ...previous, website_url: event.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Status</label>
                    <select
                      className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                      value={editorForm.status}
                      onChange={(event) => setEditorForm((previous) => ({ ...previous, status: event.target.value }))}
                    >
                      <option value="active">active</option>
                      <option value="paused">paused</option>
                      <option value="archived">archived</option>
                    </select>
                  </div>
                </div>

                <div className="rounded-[24px] border border-white/10 bg-black/15 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-white/45">Detalhes</p>
                  <div className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/65">
                    <p>
                      <span className="text-white/40">Id:</span> {selectedClient.id}
                    </p>
                    <p>
                      <span className="text-white/40">Tenant:</span> {selectedClient.tenant_id}
                    </p>
                    <p>
                      <span className="text-white/40">Criado:</span> {formatDateTimeSP(selectedClient.created_at)}
                    </p>
                    <p>
                      <span className="text-white/40">Atualizado:</span> {formatDateTimeSP(selectedClient.updated_at)}
                    </p>
                  </div>
                  <button
                    className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                    type="submit"
                    disabled={isSaving}
                  >
                    {isSaving ? "Salvando..." : "Salvar alterações"}
                  </button>
                </div>
              </form>
            ) : (
              <div className="mt-5">
                <EmptyState
                  title="Selecione um cliente"
                  description="Use o painel à esquerda para carregar um cliente e liberar a edição ou exclusão."
                />
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
