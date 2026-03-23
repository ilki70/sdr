"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
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

type Persona = {
  id: string;
  name: string;
  active_version_no: number | null;
  is_active: boolean;
};

type AgentEditorForm = {
  name: string;
  slug: string;
  description: string;
  status: string;
};

type AgentVersionForm = {
  prompt_system: string;
  persona_id: string;
};

const createTemplate = {
  name: "",
  slug: "",
  description: "",
  prompt_system:
    "Voce e um agente comercial configuravel. Atue com clareza, consistencia, foco no contexto oficial e sempre conduza para o proximo passo.",
  persona_id: "",
};

function sanitizeSlug(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [createForm, setCreateForm] = useState(createTemplate);
  const [editorForm, setEditorForm] = useState<AgentEditorForm>({
    name: "",
    slug: "",
    description: "",
    status: "active",
  });
  const [versionForm, setVersionForm] = useState<AgentVersionForm>({
    prompt_system: createTemplate.prompt_system,
    persona_id: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingMeta, setIsSavingMeta] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadAgentDetail(agentId: string) {
    const payload = await fetchJson<AgentDetail>(`/api/proxy/agents/${agentId}`);
    setDetail(payload);
    const currentVersion = payload.versions[0];
    setEditorForm({
      name: payload.agent.name,
      slug: payload.agent.slug,
      description: payload.agent.description || "",
      status: payload.agent.status,
    });
    setVersionForm({
      prompt_system: currentVersion?.prompt_system || createTemplate.prompt_system,
      persona_id: currentVersion?.persona_id || "",
    });
  }

  async function loadReferenceData(preferredAgentId?: string) {
    setIsLoading(true);
    setError(null);
    try {
      const [agentItems, personaItems] = await Promise.all([
        fetchJson<Agent[]>("/api/proxy/agents"),
        fetchJson<Persona[]>("/api/proxy/personas"),
      ]);
      setAgents(agentItems);
      setPersonas(personaItems);
      const nextAgentId = preferredAgentId || selectedAgentId || agentItems[0]?.id || null;
      setSelectedAgentId(nextAgentId);
      if (nextAgentId) {
        await loadAgentDetail(nextAgentId);
      } else {
        setDetail(null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar agentes.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadReferenceData();
  }, []);

  const currentVersion = detail?.versions[0] || null;
  const activePersonas = personas.filter((persona) => persona.is_active);
  const linkedPersona = personas.find((persona) => persona.id === currentVersion?.persona_id) || null;

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await fetchJson<Agent>("/api/proxy/agents", {
        method: "POST",
        body: JSON.stringify({
          name: createForm.name,
          slug: sanitizeSlug(createForm.slug),
          description: createForm.description,
          persona_id: createForm.persona_id || null,
          prompt_system: createForm.prompt_system,
          policy_json: { rules: ["use contexto oficial", "nao invente fatos", "sempre proponha proximo passo"] },
          tool_config_json: { rag_enabled: true, web_allowlist_enabled: true },
          knowledge_config_json: { scope: "agent_only" },
          channel_config_json: { default_channel: "lab" },
          publish: true,
        }),
      });
      setCreateForm(createTemplate);
      setNotice(`Agente ${created.name} criado e publicado.`);
      await loadReferenceData(created.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar agente.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSaveAgentMeta(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) {
      return;
    }
    setIsSavingMeta(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<Agent>(`/api/proxy/agents/${detail.agent.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editorForm.name,
          slug: sanitizeSlug(editorForm.slug),
          description: editorForm.description,
          status: editorForm.status,
        }),
      });
      setNotice(`Dados do agente ${editorForm.name} atualizados.`);
      await loadReferenceData(detail.agent.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao atualizar agente.");
    } finally {
      setIsSavingMeta(false);
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
      await fetchJson<AgentVersion>(`/api/proxy/agents/${detail.agent.id}/versions`, {
        method: "POST",
        body: JSON.stringify({
          prompt_system: versionForm.prompt_system,
          persona_id: versionForm.persona_id || null,
          policy_json: currentVersion?.policy_json || {},
          tool_config_json: currentVersion?.tool_config_json || {},
          knowledge_config_json: currentVersion?.knowledge_config_json || {},
          channel_config_json: currentVersion?.channel_config_json || {},
          publish: true,
        }),
      });
      const linked = personas.find((persona) => persona.id === versionForm.persona_id);
      setNotice(
        linked
          ? `Nova versao publicada para ${detail.agent.name}, vinculada a ${linked.name}.`
          : `Nova versao publicada para ${detail.agent.name} sem persona vinculada.`,
      );
      await loadReferenceData(detail.agent.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao publicar nova versao.");
    } finally {
      setIsPublishing(false);
    }
  }

  async function handlePublishExistingVersion(versionNo: number) {
    if (!detail) {
      return;
    }
    setError(null);
    setNotice(null);
    try {
      await fetchJson<AgentVersion>(`/api/proxy/agents/${detail.agent.id}/versions/${versionNo}/publish`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice(`Versao v${versionNo} publicada para ${detail.agent.name}.`);
      await loadReferenceData(detail.agent.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao publicar versao.");
    }
  }

  async function handleDeleteAgent() {
    if (!detail) {
      return;
    }
    const confirmed = window.confirm(`Excluir o agente "${detail.agent.name}"?`);
    if (!confirmed) {
      return;
    }
    setIsDeleting(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<Agent>(`/api/proxy/agents/${detail.agent.id}`, { method: "DELETE" });
      setNotice(`Agente ${detail.agent.name} excluido.`);
      await loadReferenceData();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao excluir agente.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Agent Studio</p>
        <h1 className="mt-3 text-3xl font-semibold">Atendentes</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Cadastre agentes, edite o perfil operacional e publique versões com a persona certa vinculada ao comportamento.
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
                <p className="mt-1 text-sm text-white/60">Selecione um agente para editar dados e publicação.</p>
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
                onChange={(event) => {
                  const nextName = event.target.value;
                  setCreateForm((current) => ({
                    ...current,
                    name: nextName,
                    slug: current.slug ? current.slug : sanitizeSlug(nextName),
                  }));
                }}
                placeholder="Nome do agente"
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-white/30"
                required
              />
              <input
                value={createForm.slug}
                onChange={(event) => setCreateForm((current) => ({ ...current, slug: sanitizeSlug(event.target.value) }))}
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
              <select
                value={createForm.persona_id}
                onChange={(event) => setCreateForm((current) => ({ ...current, persona_id: event.target.value }))}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
              >
                <option value="">Sem persona vinculada</option>
                {activePersonas.map((persona) => (
                  <option key={persona.id} value={persona.id}>
                    {persona.name} {persona.active_version_no ? `(v${persona.active_version_no})` : ""}
                  </option>
                ))}
              </select>
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
          {detail ? (
            <>
              <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold">Dados do agente</h2>
                    <p className="mt-1 text-sm text-white/60">Edite identificação operacional sem publicar nova versão.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDeleteAgent()}
                    disabled={isDeleting}
                    className="rounded-full border border-red-400/35 px-4 py-2 text-sm text-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isDeleting ? "Excluindo..." : "Excluir"}
                  </button>
                </div>
                <form className="mt-5 space-y-3" onSubmit={handleSaveAgentMeta}>
                  <input
                    value={editorForm.name}
                    onChange={(event) => setEditorForm((current) => ({ ...current, name: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                    required
                  />
                  <input
                    value={editorForm.slug}
                    onChange={(event) => setEditorForm((current) => ({ ...current, slug: sanitizeSlug(event.target.value) }))}
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                    required
                  />
                  <textarea
                    value={editorForm.description}
                    onChange={(event) => setEditorForm((current) => ({ ...current, description: event.target.value }))}
                    rows={3}
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                  />
                  <select
                    value={editorForm.status}
                    onChange={(event) => setEditorForm((current) => ({ ...current, status: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                  >
                    <option value="active">Ativo</option>
                    <option value="paused">Pausado</option>
                  </select>
                  <button
                    type="submit"
                    disabled={isSavingMeta}
                    className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSavingMeta ? "Salvando..." : "Salvar dados"}
                  </button>
                </form>
              </article>

              <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                <h2 className="text-xl font-semibold">Vinculação e prompt</h2>
                <p className="mt-2 text-sm text-white/60">
                  Cada nova versão pode trocar a persona vinculada. Se nenhuma for escolhida, o agente opera só com o prompt publicado.
                </p>
                <div className="mt-4 rounded-[20px] border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-wide text-white/40">Vínculo ativo</p>
                  <p className="mt-2 text-sm text-white/80">
                    {linkedPersona
                      ? `${linkedPersona.name} • v${currentVersion?.persona_version_no ?? linkedPersona.active_version_no ?? "-"}`
                      : "Sem persona vinculada"}
                  </p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link
                    href={`/training?agentId=${detail.agent.id}`}
                    className="rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/10 px-4 py-2 text-sm text-emerald-100 transition hover:border-[var(--accent)]/50 hover:bg-[var(--accent)]/15"
                  >
                    Treinar persona vinculada
                  </Link>
                </div>
                <form className="mt-4 space-y-3" onSubmit={handlePublishVersion}>
                  <select
                    value={versionForm.persona_id}
                    onChange={(event) => setVersionForm((current) => ({ ...current, persona_id: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                  >
                    <option value="">Sem persona vinculada</option>
                    {currentVersion?.persona_id && linkedPersona && !linkedPersona.is_active ? (
                      <option value={linkedPersona.id}>
                        {linkedPersona.name} {currentVersion.persona_version_no ? `(v${currentVersion.persona_version_no})` : ""} (inativa)
                      </option>
                    ) : null}
                    {activePersonas.map((persona) => (
                      <option key={persona.id} value={persona.id}>
                        {persona.name} {persona.active_version_no ? `(v${persona.active_version_no})` : ""}
                      </option>
                    ))}
                  </select>
                  <textarea
                    value={versionForm.prompt_system}
                    onChange={(event) => setVersionForm((current) => ({ ...current, prompt_system: event.target.value }))}
                    rows={8}
                    placeholder="Prompt atualizado"
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-white/30"
                    required
                  />
                  <button
                    type="submit"
                    disabled={isPublishing}
                    className="rounded-full bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isPublishing ? "Publicando..." : "Publicar nova versão"}
                  </button>
                </form>
              </article>

              <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                <h2 className="text-xl font-semibold">Versão ativa e histórico</h2>
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
                    <p className="mt-3 text-xs text-white/45">
                      Persona ativa:{" "}
                      {linkedPersona
                        ? `${linkedPersona.name} • v${currentVersion?.persona_version_no ?? linkedPersona.active_version_no ?? "-"}`
                        : "sem vinculo"}
                    </p>
                  </div>

                  <div className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/40">Prompt ativo</p>
                    <pre className="mt-3 whitespace-pre-wrap text-sm text-white/80">{currentVersion?.prompt_system || "Sem versao."}</pre>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    {detail.versions.map((version) => {
                      const versionPersona = personas.find((persona) => persona.id === version.persona_id);
                      return (
                        <article key={version.id} className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <strong className="text-sm">Versao {version.version_no}</strong>
                            <button
                              type="button"
                              onClick={() => void handlePublishExistingVersion(version.version_no)}
                              className="text-xs text-[var(--accent)]"
                            >
                              {version.is_published ? "publicada" : "publicar"}
                            </button>
                          </div>
                          <p className="mt-2 text-xs text-white/40">{formatDateTimeSP(version.created_at)}</p>
                          <p className="mt-3 text-xs text-white/45">
                            Persona:{" "}
                            {versionPersona
                              ? `${versionPersona.name} • v${version.persona_version_no ?? versionPersona.active_version_no ?? "-"}`
                              : "sem vinculo"}
                          </p>
                          <p className="mt-3 line-clamp-4 text-sm text-white/65">{version.prompt_system}</p>
                        </article>
                      );
                    })}
                  </div>
                </div>
              </article>
            </>
          ) : (
            <section className="rounded-[24px] border border-white/10 bg-white/5 p-6">
              <EmptyState
                title="Nenhum agente selecionado."
                description="Escolha um agente existente ou crie um novo para começar."
              />
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
