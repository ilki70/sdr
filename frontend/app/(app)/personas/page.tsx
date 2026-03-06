"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type Persona = {
  id: string;
  name: string;
  description: string | null;
  active_version_no: number | null;
  is_active: boolean;
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

export default function PersonasPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>("");
  const [detail, setDetail] = useState<PersonaDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    name: "Closer Consultivo",
    description: "Persona comercial focada em qualificação e fechamento.",
    tone: "consultivo e objetivo",
    prompt_system: "Você é um vendedor consultivo, focado em clareza, qualificação e fechamento sem prometer o que não está na base oficial.",
    approach_rules: "Faça perguntas curtas.\nUse contexto oficial.\nSempre sugira próximo passo concreto.",
    objection_playbook: "preco: reposicione pelo valor e pela previsibilidade\nconfianca: cite fonte oficial e provas documentais",
  });
  const [versionForm, setVersionForm] = useState({
    tone: "consultivo e firme",
    prompt_system: "Você conduz o lead de forma objetiva, sustentada pela base oficial e orientada a próximo passo.",
    approach_rules: "Valide a dor.\nQualifique renda e objetivo.\nLeve para simulação ou adesão.",
    objection_playbook: "juros: explique que consórcio não trabalha com juros, conforme contexto oficial\norcamento: mostre faixa mínima e pergunte sobre margem",
  });

  async function loadPersonas() {
    const items = await fetchJson<Persona[]>("/api/proxy/personas");
    setPersonas(items);
    const nextPersonaId = selectedPersonaId || items[0]?.id || "";
    setSelectedPersonaId(nextPersonaId);
    if (nextPersonaId) {
      const payload = await fetchJson<PersonaDetail>(`/api/proxy/personas/${nextPersonaId}`);
      setDetail(payload);
    } else {
      setDetail(null);
    }
  }

  useEffect(() => {
    void loadPersonas().catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar personas."));
  }, []);

  useEffect(() => {
    if (!selectedPersonaId) {
      return;
    }
    void fetchJson<PersonaDetail>(`/api/proxy/personas/${selectedPersonaId}`)
      .then(setDetail)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar detalhe da persona."));
  }, [selectedPersonaId]);

  async function handleCreatePersona(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await fetchJson<Persona>("/api/proxy/personas", {
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
      await loadPersonas();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar persona.");
    }
  }

  async function handleCreateVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPersonaId) {
      return;
    }
    setError(null);
    try {
      await fetchJson<PersonaVersion>(`/api/proxy/personas/${selectedPersonaId}/versions`, {
        method: "POST",
        body: JSON.stringify({
          tone: versionForm.tone,
          prompt_system: versionForm.prompt_system,
          approach_rules: versionForm.approach_rules.split("\n").map((item) => item.trim()).filter(Boolean),
          objection_playbook: parseKeyValueBlock(versionForm.objection_playbook),
          publish: false,
        }),
      });
      const payload = await fetchJson<PersonaDetail>(`/api/proxy/personas/${selectedPersonaId}`);
      setDetail(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar versão.");
    }
  }

  async function handlePublish(versionNo: number) {
    if (!selectedPersonaId) {
      return;
    }
    await fetchJson<PersonaVersion>(`/api/proxy/personas/${selectedPersonaId}/versions/${versionNo}/publish`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    const payload = await fetchJson<PersonaDetail>(`/api/proxy/personas/${selectedPersonaId}`);
    setDetail(payload);
    await loadPersonas();
  }

  return (
    <main className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <div className="space-y-5">
        <form onSubmit={handleCreatePersona} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Nova persona</p>
          <input className="mt-4 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={createForm.name} onChange={(event) => setCreateForm((previous) => ({ ...previous, name: event.target.value }))} />
          <textarea className="mt-3 min-h-[90px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={createForm.description} onChange={(event) => setCreateForm((previous) => ({ ...previous, description: event.target.value }))} />
          <input className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={createForm.tone} onChange={(event) => setCreateForm((previous) => ({ ...previous, tone: event.target.value }))} />
          <textarea className="mt-3 min-h-[140px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={createForm.prompt_system} onChange={(event) => setCreateForm((previous) => ({ ...previous, prompt_system: event.target.value }))} />
          <textarea className="mt-3 min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={createForm.approach_rules} onChange={(event) => setCreateForm((previous) => ({ ...previous, approach_rules: event.target.value }))} />
          <textarea className="mt-3 min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={createForm.objection_playbook} onChange={(event) => setCreateForm((previous) => ({ ...previous, objection_playbook: event.target.value }))} />
          <button className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black" type="submit">Criar persona publicada</button>
        </form>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Personas</p>
          <div className="mt-4 space-y-2">
            {personas.map((persona) => (
              <button key={persona.id} type="button" onClick={() => setSelectedPersonaId(persona.id)} className="block w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-left">
                <strong className="text-sm">{persona.name}</strong>
                <p className="mt-1 text-xs text-white/50">Versão ativa: {persona.active_version_no || "-"}</p>
              </button>
            ))}
          </div>
        </section>
      </div>

      <section className="space-y-5">
        {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
        <form onSubmit={handleCreateVersion} className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h1 className="text-2xl font-semibold">Painel de persona/playbook</h1>
          <p className="mt-2 text-sm text-white/70">Edite tom, prompt-base, regras comerciais e objeções sem tocar no código do agente.</p>
          <input className="mt-4 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={versionForm.tone} onChange={(event) => setVersionForm((previous) => ({ ...previous, tone: event.target.value }))} />
          <textarea className="mt-3 min-h-[140px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={versionForm.prompt_system} onChange={(event) => setVersionForm((previous) => ({ ...previous, prompt_system: event.target.value }))} />
          <textarea className="mt-3 min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={versionForm.approach_rules} onChange={(event) => setVersionForm((previous) => ({ ...previous, approach_rules: event.target.value }))} />
          <textarea className="mt-3 min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm" value={versionForm.objection_playbook} onChange={(event) => setVersionForm((previous) => ({ ...previous, objection_playbook: event.target.value }))} />
          <button className="mt-4 rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-black" type="submit">Criar nova versão</button>
        </form>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-semibold">Versões</h2>
          <div className="mt-5 space-y-3">
            {detail?.versions.map((version) => (
              <article key={version.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong>v{version.version_no} • {version.tone}</strong>
                  <button type="button" onClick={() => void handlePublish(version.version_no)} className="rounded-full border border-[var(--accent)]/35 px-4 py-2 text-sm text-[var(--accent)]">
                    {version.is_published ? "Publicada" : "Publicar"}
                  </button>
                </div>
                <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(version.created_at)}</p>
                <p className="mt-3 text-sm text-white/70">{version.prompt_system}</p>
                <p className="mt-3 text-xs text-white/55">Regras: {(version.approach_rules_json.rules || []).join(" | ") || "sem regras"}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
