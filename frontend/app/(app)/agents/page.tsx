"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import { EmptyState } from "@/components/shared/empty-state";

type Agent = {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  description: string | null;
  active_version_no: number | null;
  status: string;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
};

type AgentVersion = {
  id: string;
  tenant_id: string;
  agent_id: string;
  version_no: number;
  persona_id: string | null;
  persona_version_no: number | null;
  prompt_system: string;
  policy_json: Record<string, unknown>;
  tool_config_json: Record<string, unknown>;
  knowledge_config_json: Record<string, unknown>;
  channel_config_json: Record<string, unknown>;
  is_published: boolean;
  created_by_user_id: string;
  created_at: string;
};

type AgentDetail = {
  agent: Agent;
  versions: AgentVersion[];
};

const createTemplate = {
  name: "",
  slug: "",
  description: "",
  prompt_system:
    "Voce e um agente comercial configuravel. Atue com clareza, consistencia, foco no contexto oficial e sempre conduza para o proximo passo.",
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [createForm, setCreateForm] = useState(createTemplate);
  const [versionPrompt, setVersionPrompt] = useState(createTemplate.prompt_system);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void loadAgents();
  }, []);

  async function loadAgents(preferredAgentId?: string) {
    setIsLoading(true);
    setError(null);
    try {
      const items = await fetchJson<Agent[]>("/api/proxy/agents");
      setAgents(items);
      const agentId = preferredAgentId || selectedAgentId || items[0]?.id || null;
      setSelectedAgentId(agentId);
      if (agentId) {
        await loadAgentDetail(agentId);
      } else {
        setDetail(null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar agentes.");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadAgentDetail(agentId: string) {
    const payload = await fetchJson<AgentDetail>(`/api/proxy/agents/${agentId}`);
    setDetail(payload);
    setVersionPrompt(payload.versions[0]?.prompt_system || createTemplate.prompt_system);
  }

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await fetchJson<Agent>("/api/proxy/agents", {
        method: "POST",
        body: JSON.stringify({
          ...createForm,
          policy_json: { rules: ["use contexto oficial", "nao invente fatos", "sempre proponha proximo passo"] },
          tool_config_json: { rag_enabled: true, web_allowlist_enabled: true },
          knowledge_config_json: { scope: "agent_only" },
          channel_config_json: { default_channel: "lab" },
          publish: true,
        }),
      });
      setCreateForm(createTemplate);
      setNotice(`Agente ${created.name} criado e publicado.`);
      await loadAgents(created.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar agente.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handlePublishVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) {
      return;
    }
    setIsPublishing(true);
    setError(null);
    setNotice(null);
    try {
      const currentVersion = detail.versions[0];
      await fetchJson<AgentVersion>(`/api/proxy/agents/${detail.agent.id}/versions`, {
        method: "POST",
        body: JSON.stringify({
          prompt_system: versionPrompt,
          persona_id: currentVersion?.persona_id || null,
          persona_version_no: currentVersion?.persona_version_no || null,
          policy_json: currentVersion?.policy_json || {},
          tool_config_json: currentVersion?.tool_config_json || {},
          knowledge_config_json: currentVersion?.knowledge_config_json || {},
          channel_config_json: currentVersion?.channel_config_json || {},
          publish: true,
        }),
      });
      setNotice(`Nova versao publicada para ${detail.agent.name}.`);
      await loadAgents(detail.agent.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao publicar nova versao.");
    } finally {
      setIsPublishing(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Agent Studio</p>
        <h1 className="mt-3 text-3xl font-semibold">Atendentes</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Cadastre atendentes, publique novas versões e mantenha cada agente alinhado ao contexto comercial do tenant.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      {notice ? <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{notice}</p> : null}

      <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-5">
          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Catálogo</h2>
                <p className="mt-1 text-sm text-white/60">Selecione um agente para revisar a versão ativa e o histórico.</p>
              </div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/55">{agents.length} ativos</span>
            </div>
            <div className="mt-4 space-y-3">
              {isLoading ? <p className="text-sm text-white/60">Carregando agentes...</p> : null}
              {agents.map((agent) => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => {
                    setSelectedAgentId(agent.id);
                    void loadAgentDetail(agent.id);
                  }}
                  className={`w-full rounded-[20px] border p-4 text-left transition ${
                    selectedAgentId === agent.id
                      ? "border-[var(--accent)] bg-emerald-500/10"
                      : "border-white/10 bg-black/20 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <strong className="text-sm">{agent.name}</strong>
                      <p className="mt-1 text-[11px] uppercase tracking-wide text-white/40">{agent.slug}</p>
                    </div>
                    <span className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-white/55">
                      v{agent.active_version_no ?? "-"}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-white/65">{agent.description || "Sem descricao operacional."}</p>
                  <p className="mt-3 text-xs text-white/35">Atualizado em {formatDateTimeSP(agent.updated_at)}</p>
                </button>
              ))}
              {!isLoading && agents.length === 0 ? (
                <EmptyState
                  title="Nenhum agente encontrado."
                  description="Crie o primeiro atendente para destravar versões, laboratório e bindings por canal."
                />
              ) : null}
            </div>
          </article>

          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-xl font-semibold">Criar atendente</h2>
            <form className="mt-4 space-y-3" onSubmit={handleCreateAgent}>
              <input
                value={createForm.name}
                onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Nome do agente"
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-white/30"
                required
              />
              <input
                value={createForm.slug}
                onChange={(event) => setCreateForm((current) => ({ ...current, slug: event.target.value }))}
                placeholder="slug-do-agente"
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-white/30"
                required
              />
              <textarea
                value={createForm.description}
                onChange={(event) => setCreateForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Descricao operacional"
                rows={3}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-white/30"
              />
              <textarea
                value={createForm.prompt_system}
                onChange={(event) => setCreateForm((current) => ({ ...current, prompt_system: event.target.value }))}
                placeholder="Prompt base publicado"
                rows={6}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-white/30"
                required
              />
              <button
                type="submit"
                disabled={isCreating}
                className="rounded-full bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreating ? "Criando..." : "Criar e publicar"}
              </button>
            </form>
          </article>
        </div>

        <div className="space-y-5">
          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-xl font-semibold">Versão ativa e histórico</h2>
            {detail ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <strong>{detail.agent.name}</strong>
                      <p className="mt-1 text-xs uppercase tracking-wide text-white/40">{detail.agent.slug}</p>
                    </div>
                    <span className="rounded-full border border-[var(--accent)] px-3 py-1 text-xs text-emerald-200">
                      publicada v{detail.agent.active_version_no ?? "-"}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-white/65">{detail.agent.description || "Sem descricao operacional."}</p>
                </div>

                <div className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-wide text-white/40">Prompt ativo</p>
                  <pre className="mt-3 whitespace-pre-wrap text-sm text-white/80">{detail.versions[0]?.prompt_system || "Sem versao."}</pre>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {detail.versions.map((version) => (
                    <article key={version.id} className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <strong className="text-sm">Versao {version.version_no}</strong>
                        <span className="text-xs text-white/45">{version.is_published ? "publicada" : "rascunho"}</span>
                      </div>
                      <p className="mt-2 text-xs text-white/40">{formatDateTimeSP(version.created_at)}</p>
                      <p className="mt-3 line-clamp-4 text-sm text-white/65">{version.prompt_system}</p>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-white/60">Selecione um agente para abrir os detalhes.</p>
            )}
          </article>

          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-xl font-semibold">Publicar nova versão</h2>
            <p className="mt-2 text-sm text-white/60">Use o prompt como unidade de iteração rápida do agente.</p>
            <form className="mt-4 space-y-3" onSubmit={handlePublishVersion}>
              <textarea
                value={versionPrompt}
                onChange={(event) => setVersionPrompt(event.target.value)}
                rows={8}
                placeholder="Prompt atualizado"
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-white/30"
                required
              />
              <button
                type="submit"
                disabled={!detail || isPublishing}
                className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isPublishing ? "Publicando..." : "Criar versão publicada"}
              </button>
            </form>
          </article>
        </div>
      </section>
    </main>
  );
}
