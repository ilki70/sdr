"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import { EmptyState } from "@/components/shared/empty-state";

type Persona = {
  id: string;
  name: string;
  description: string | null;
  active_version_no: number | null;
  is_active: boolean;
  updated_at?: string;
};

type PersonaVersion = {
  id: string;
  version_no: number;
  tone: string;
  prompt_system: string;
  approach_rules_json: { rules?: string[] };
  objection_playbook_json: Record<string, string>;
  is_published: boolean;
  created_at: string;
};

type PersonaDetail = {
  persona: Persona;
  versions: PersonaVersion[];
};

type PersonaEditorForm = {
  name: string;
  description: string;
  is_active: boolean;
};

type PersonaVersionForm = {
  tone: string;
  prompt_system: string;
  approach_rules: string;
  objection_playbook: string;
};

const createDefaults: PersonaVersionForm & { name: string; description: string } = {
  name: "",
  description: "",
  tone: "consultivo e objetivo",
  prompt_system:
    "Voce e uma persona comercial consultiva. Atue com clareza, qualificacao disciplinada e foco no proximo passo sem inventar fatos.",
  approach_rules: "Faça perguntas curtas.\nUse contexto oficial.\nSempre sugira próximo passo concreto.",
  objection_playbook:
    "preco: reposicione pelo valor e pela previsibilidade\nconfianca: cite fonte oficial e provas documentais",
};

function parseKeyValueBlock(input: string): Record<string, string> {
  return input
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce<Record<string, string>>((accumulator, line) => {
      const [key, ...rest] = line.split(":");
      if (key && rest.length > 0) {
        accumulator[key.trim()] = rest.join(":").trim();
      }
      return accumulator;
    }, {});
}

function formatKeyValueBlock(value: Record<string, string>) {
  return Object.entries(value)
    .map(([key, content]) => `${key}: ${content}`)
    .join("\n");
}

function buildVersionForm(version?: PersonaVersion | null): PersonaVersionForm {
  return {
    tone: version?.tone || createDefaults.tone,
    prompt_system: version?.prompt_system || createDefaults.prompt_system,
    approach_rules: (version?.approach_rules_json.rules || []).join("\n") || createDefaults.approach_rules,
    objection_playbook: formatKeyValueBlock(version?.objection_playbook_json || {}) || createDefaults.objection_playbook,
  };
}

export default function PersonasPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>("");
  const [detail, setDetail] = useState<PersonaDetail | null>(null);
  const [createForm, setCreateForm] = useState(createDefaults);
  const [editorForm, setEditorForm] = useState<PersonaEditorForm>({ name: "", description: "", is_active: true });
  const [versionForm, setVersionForm] = useState<PersonaVersionForm>(buildVersionForm());
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingMeta, setIsSavingMeta] = useState(false);
  const [isSavingVersion, setIsSavingVersion] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadPersonaDetail(personaId: string) {
    const payload = await fetchJson<PersonaDetail>(`/api/proxy/personas/${personaId}`);
    setDetail(payload);
    setEditorForm({
      name: payload.persona.name,
      description: payload.persona.description || "",
      is_active: payload.persona.is_active,
    });
    setVersionForm(buildVersionForm(payload.versions[0]));
  }

  async function loadPersonas(preferredPersonaId?: string) {
    setIsLoading(true);
    setError(null);
    try {
      const items = await fetchJson<Persona[]>("/api/proxy/personas");
      setPersonas(items);
      const nextPersonaId = preferredPersonaId || selectedPersonaId || items[0]?.id || "";
      setSelectedPersonaId(nextPersonaId);
      if (nextPersonaId) {
        await loadPersonaDetail(nextPersonaId);
      } else {
        setDetail(null);
        setEditorForm({ name: "", description: "", is_active: true });
        setVersionForm(buildVersionForm());
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar personas.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadPersonas();
  }, []);

  async function handleCreatePersona(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await fetchJson<Persona>("/api/proxy/personas", {
        method: "POST",
        body: JSON.stringify({
          name: createForm.name,
          description: createForm.description,
          tone: createForm.tone,
          prompt_system: createForm.prompt_system,
          approach_rules: createForm.approach_rules.split("\n").map((item) => item.trim()).filter(Boolean),
          objection_playbook: parseKeyValueBlock(createForm.objection_playbook),
          publish: true,
        }),
      });
      setCreateForm(createDefaults);
      setNotice(`Persona ${created.name} criada e publicada.`);
      await loadPersonas(created.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar persona.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSavePersonaMeta(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) {
      return;
    }
    setIsSavingMeta(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<Persona>(`/api/proxy/personas/${detail.persona.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editorForm.name,
          description: editorForm.description,
          is_active: editorForm.is_active,
        }),
      });
      setNotice(`Dados da persona ${editorForm.name} atualizados.`);
      await loadPersonas(detail.persona.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao atualizar persona.");
    } finally {
      setIsSavingMeta(false);
    }
  }

  async function handleCreateVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) {
      return;
    }
    setIsSavingVersion(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<PersonaVersion>(`/api/proxy/personas/${detail.persona.id}/versions`, {
        method: "POST",
        body: JSON.stringify({
          tone: versionForm.tone,
          prompt_system: versionForm.prompt_system,
          approach_rules: versionForm.approach_rules.split("\n").map((item) => item.trim()).filter(Boolean),
          objection_playbook: parseKeyValueBlock(versionForm.objection_playbook),
          publish: true,
        }),
      });
      setNotice(`Nova versao publicada para ${detail.persona.name}.`);
      await loadPersonas(detail.persona.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao publicar versao.");
    } finally {
      setIsSavingVersion(false);
    }
  }

  async function handlePublish(versionNo: number) {
    if (!detail) {
      return;
    }
    setError(null);
    setNotice(null);
    try {
      await fetchJson<PersonaVersion>(`/api/proxy/personas/${detail.persona.id}/versions/${versionNo}/publish`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice(`Versao v${versionNo} publicada para ${detail.persona.name}.`);
      await loadPersonas(detail.persona.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao publicar versao.");
    }
  }

  async function handleDeletePersona() {
    if (!detail) {
      return;
    }
    const confirmed = window.confirm(`Excluir a persona "${detail.persona.name}"?`);
    if (!confirmed) {
      return;
    }
    setIsDeleting(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<Persona>(`/api/proxy/personas/${detail.persona.id}`, { method: "DELETE" });
      setNotice(`Persona ${detail.persona.name} excluida.`);
      await loadPersonas();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao excluir persona.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Persona Studio</p>
        <h1 className="mt-3 text-3xl font-semibold">Personas</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Crie, ajuste e publique o tom operacional que depois pode ser vinculado aos agentes para alinhar comportamento.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      {notice ? <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{notice}</p> : null}

      <section className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <div className="space-y-5">
          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Catálogo</h2>
                <p className="mt-1 text-sm text-white/60">Escolha uma persona para editar nome, status e versões.</p>
              </div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
                {personas.length} itens
              </span>
            </div>
            <div className="mt-4 space-y-3">
              {isLoading ? <p className="text-sm text-white/60">Carregando personas...</p> : null}
              {personas.map((persona) => (
                <button
                  key={persona.id}
                  type="button"
                  onClick={() => {
                    setSelectedPersonaId(persona.id);
                    void loadPersonaDetail(persona.id);
                  }}
                  className={`block w-full rounded-[20px] border px-4 py-3 text-left transition ${
                    selectedPersonaId === persona.id
                      ? "border-[var(--accent)] bg-emerald-500/10"
                      : "border-white/10 bg-black/20 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <strong className="text-sm">{persona.name}</strong>
                    <span className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-white/55">
                      v{persona.active_version_no || "-"}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-white/50">{persona.description || "Sem descricao resumida."}</p>
                  <p className="mt-3 text-[11px] uppercase tracking-wide text-white/35">
                    {persona.is_active ? "ativa" : "inativa"}
                  </p>
                </button>
              ))}
              {!isLoading && personas.length === 0 ? (
                <EmptyState
                  title="Nenhuma persona cadastrada."
                  description="Crie a primeira persona para registrar tom, objeções e estilo comercial do tenant."
                />
              ) : null}
            </div>
          </article>

          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-xl font-semibold">Criar persona</h2>
            <form onSubmit={handleCreatePersona} className="mt-4 space-y-3">
              <input
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                value={createForm.name}
                placeholder="Nome da persona"
                onChange={(event) => setCreateForm((previous) => ({ ...previous, name: event.target.value }))}
                required
              />
              <textarea
                className="min-h-[90px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                value={createForm.description}
                placeholder="Descricao da persona"
                onChange={(event) => setCreateForm((previous) => ({ ...previous, description: event.target.value }))}
              />
              <input
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                value={createForm.tone}
                placeholder="Tom base"
                onChange={(event) => setCreateForm((previous) => ({ ...previous, tone: event.target.value }))}
                required
              />
              <textarea
                className="min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                value={createForm.prompt_system}
                placeholder="Prompt base"
                onChange={(event) => setCreateForm((previous) => ({ ...previous, prompt_system: event.target.value }))}
                required
              />
              <button
                className="w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                type="submit"
                disabled={isCreating}
              >
                {isCreating ? "Criando..." : "Criar e publicar"}
              </button>
            </form>
          </article>
        </div>

        <div className="space-y-5">
          {detail ? (
            <>
              <article className="rounded-[24px] border border-white/10 bg-white/5 p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold">Dados da persona</h2>
                    <p className="mt-1 text-sm text-white/60">Ajuste nome, resumo e disponibilidade da persona.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDeletePersona()}
                    disabled={isDeleting}
                    className="rounded-full border border-red-400/35 px-4 py-2 text-sm text-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isDeleting ? "Excluindo..." : "Excluir"}
                  </button>
                </div>
                <form onSubmit={handleSavePersonaMeta} className="mt-5 space-y-3">
                  <input
                    className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                    value={editorForm.name}
                    onChange={(event) => setEditorForm((previous) => ({ ...previous, name: event.target.value }))}
                    required
                  />
                  <textarea
                    className="min-h-[90px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                    value={editorForm.description}
                    onChange={(event) => setEditorForm((previous) => ({ ...previous, description: event.target.value }))}
                  />
                  <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/75">
                    <input
                      type="checkbox"
                      checked={editorForm.is_active}
                      onChange={(event) => setEditorForm((previous) => ({ ...previous, is_active: event.target.checked }))}
                    />
                    Persona disponivel para uso e vinculacao em agentes
                  </label>
                  <button
                    type="submit"
                    disabled={isSavingMeta}
                    className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSavingMeta ? "Salvando..." : "Salvar dados"}
                  </button>
                </form>
              </article>

              <article className="rounded-[24px] border border-white/10 bg-white/5 p-6">
                <h2 className="text-xl font-semibold">Prompt e playbook</h2>
                <p className="mt-1 text-sm text-white/60">Publique uma nova versão para atualizar o comportamento da persona.</p>
                <form onSubmit={handleCreateVersion} className="mt-5 space-y-3">
                  <input
                    className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                    value={versionForm.tone}
                    onChange={(event) => setVersionForm((previous) => ({ ...previous, tone: event.target.value }))}
                    placeholder="Tom da persona"
                    required
                  />
                  <textarea
                    className="min-h-[140px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                    value={versionForm.prompt_system}
                    onChange={(event) => setVersionForm((previous) => ({ ...previous, prompt_system: event.target.value }))}
                    placeholder="Prompt-base"
                    required
                  />
                  <textarea
                    className="min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                    value={versionForm.approach_rules}
                    onChange={(event) => setVersionForm((previous) => ({ ...previous, approach_rules: event.target.value }))}
                    placeholder="Uma regra por linha"
                  />
                  <textarea
                    className="min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                    value={versionForm.objection_playbook}
                    onChange={(event) => setVersionForm((previous) => ({ ...previous, objection_playbook: event.target.value }))}
                    placeholder="objecao: resposta"
                  />
                  <button
                    className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                    type="submit"
                    disabled={isSavingVersion}
                  >
                    {isSavingVersion ? "Publicando..." : "Publicar nova versão"}
                  </button>
                </form>
              </article>

              <section className="rounded-[24px] border border-white/10 bg-white/5 p-6">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold">Histórico de versões</h2>
                  <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
                    {detail.versions.length} itens
                  </span>
                </div>
                <div className="mt-5 space-y-3">
                  {detail.versions.map((version) => (
                    <article key={version.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <strong>
                            v{version.version_no} • {version.tone}
                          </strong>
                          <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(version.created_at)}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => void handlePublish(version.version_no)}
                          className="rounded-full border border-[var(--accent)]/35 px-4 py-2 text-sm text-[var(--accent)]"
                        >
                          {version.is_published ? "Publicada" : "Publicar"}
                        </button>
                      </div>
                      <p className="mt-3 text-sm text-white/70">{version.prompt_system}</p>
                      <p className="mt-3 text-xs text-white/55">
                        Regras: {(version.approach_rules_json.rules || []).join(" | ") || "sem regras"}
                      </p>
                    </article>
                  ))}
                  {detail.versions.length === 0 ? (
                    <EmptyState
                      title="Nenhuma versão registrada."
                      description="Publique a primeira versão para deixar essa persona pronta para vinculação."
                    />
                  ) : null}
                </div>
              </section>
            </>
          ) : (
            <section className="rounded-[24px] border border-white/10 bg-white/5 p-6">
              <EmptyState
                title="Nenhuma persona selecionada."
                description="Escolha uma persona existente ou crie uma nova para começar."
              />
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
