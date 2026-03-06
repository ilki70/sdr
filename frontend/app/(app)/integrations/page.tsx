"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type Integration = {
  id: string;
  provider: string;
  inbox_ref: string;
  api_base_url: string;
  status: string;
  updated_at: string;
  config_json: Record<string, unknown> | null;
};

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [provider, setProvider] = useState("chatwoot");
  const [inboxRef, setInboxRef] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [status, setStatus] = useState("active");
  const [configJson, setConfigJson] = useState('{\n  "channel": "whatsapp"\n}');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedIntegration = useMemo(
    () => integrations.find((integration) => integration.id === selectedId) || null,
    [integrations, selectedId],
  );

  async function loadIntegrations(nextSelectedId?: string | null) {
    const items = await fetchJson<Integration[]>("/api/proxy/integrations");
    setIntegrations(items);
    const preferredId = nextSelectedId ?? selectedId;
    const selected = items.find((integration) => integration.id === preferredId) || items[0] || null;
    setSelectedId(selected?.id || null);
    return items;
  }

  useEffect(() => {
    void loadIntegrations().catch((cause) =>
      setError(cause instanceof Error ? cause.message : "Falha ao carregar integracoes."),
    );
  }, []);

  useEffect(() => {
    if (selectedIntegration) {
      setFormMode("edit");
      setProvider(selectedIntegration.provider);
      setInboxRef(selectedIntegration.inbox_ref);
      setApiBaseUrl(selectedIntegration.api_base_url);
      setWebhookSecret("");
      setStatus(selectedIntegration.status);
      setConfigJson(JSON.stringify(selectedIntegration.config_json || {}, null, 2));
      return;
    }

    setFormMode("create");
    setProvider("chatwoot");
    setInboxRef("");
    setApiBaseUrl("");
    setWebhookSecret("");
    setStatus("active");
    setConfigJson('{\n  "channel": "whatsapp"\n}');
  }, [selectedIntegration]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);

    try {
      const parsedConfig = configJson.trim() ? (JSON.parse(configJson) as Record<string, unknown>) : null;
      if (formMode === "create") {
        const created = await fetchJson<Integration>("/api/proxy/integrations", {
          method: "POST",
          body: JSON.stringify({
            provider,
            inbox_ref: inboxRef,
            api_base_url: apiBaseUrl,
            webhook_secret: webhookSecret,
            config_json: parsedConfig,
            status,
          }),
        });
        await loadIntegrations(created.id);
      } else if (selectedIntegration) {
        await fetchJson<Integration>(`/api/proxy/integrations/${selectedIntegration.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            inbox_ref: inboxRef,
            api_base_url: apiBaseUrl,
            webhook_secret: webhookSecret || undefined,
            config_json: parsedConfig,
            status,
          }),
        });
        await loadIntegrations(selectedIntegration.id);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao salvar integracao.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold">Integracoes</h1>
        <p className="mt-2 text-sm text-white/70">
          CRUD inicial para configurar Chatwoot e outros canais antes da integracao real por webhook.
        </p>
        {error ? <p className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={() => setSelectedId(null)}
            className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
              !selectedId ? "border-[var(--accent)]/60 bg-[var(--accent)]/12" : "border-white/10 bg-black/20"
            }`}
          >
            Nova integracao
          </button>

          {integrations.map((integration) => (
            <button
              key={integration.id}
              type="button"
              onClick={() => setSelectedId(integration.id)}
              className={`block w-full rounded-[24px] border px-5 py-5 text-left transition ${
                integration.id === selectedId
                  ? "border-[var(--accent)]/60 bg-[var(--accent)]/12"
                  : "border-white/10 bg-black/20 hover:border-white/20 hover:bg-white/5"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <strong>{integration.provider}</strong>
                <span className="text-xs uppercase tracking-wide text-white/50">{integration.status}</span>
              </div>
              <p className="mt-2 text-sm text-white/70">Inbox: {integration.inbox_ref}</p>
              <p className="mt-2 text-xs text-white/50">{integration.api_base_url}</p>
              <p className="mt-3 text-xs text-white/40">Atualizado em {formatDateTimeSP(integration.updated_at)}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Config editor</p>
            <h2 className="mt-2 text-xl font-semibold">{formMode === "create" ? "Criar integracao" : "Editar integracao"}</h2>
          </div>
          <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
            {formMode}
          </span>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-white/70">
              <span>Provider</span>
              <input
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
                disabled={formMode === "edit"}
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none disabled:opacity-60"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Status</span>
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              >
                <option value="active">active</option>
                <option value="test">test</option>
                <option value="paused">paused</option>
              </select>
            </label>
          </div>

          <label className="space-y-2 text-sm text-white/70">
            <span>Inbox ref</span>
            <input
              value={inboxRef}
              onChange={(event) => setInboxRef(event.target.value)}
              className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              placeholder="whatsapp-vinac"
            />
          </label>

          <label className="space-y-2 text-sm text-white/70">
            <span>API base URL</span>
            <input
              value={apiBaseUrl}
              onChange={(event) => setApiBaseUrl(event.target.value)}
              className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              placeholder="https://chatwoot.suaempresa.com"
            />
          </label>

          <label className="space-y-2 text-sm text-white/70">
            <span>{formMode === "create" ? "Webhook secret" : "Novo webhook secret opcional"}</span>
            <input
              value={webhookSecret}
              onChange={(event) => setWebhookSecret(event.target.value)}
              className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              placeholder="chatwoot-signing-secret"
            />
          </label>

          <label className="space-y-2 text-sm text-white/70">
            <span>config_json</span>
            <textarea
              value={configJson}
              onChange={(event) => setConfigJson(event.target.value)}
              className="min-h-[180px] w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 font-mono text-sm text-white outline-none"
            />
          </label>

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-white/50">No modo de edicao, deixe o secret em branco para manter o valor atual.</p>
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-full bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-black disabled:opacity-60"
            >
              {isSaving ? "Salvando..." : formMode === "create" ? "Criar integracao" : "Salvar ajustes"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
