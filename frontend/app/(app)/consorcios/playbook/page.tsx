"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import {
  type AgentOption,
  type ConsorcioStudio,
  formatObjections,
  joinLines,
  parseObjections,
  splitLines,
} from "../_shared";

export default function ConsorciosPlaybookPage() {
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [studio, setStudio] = useState<ConsorcioStudio | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    prompt_system: "",
    positioning: "",
    tone: "consultivo",
    qualification_intent: "qualificar lead de consorcio",
    qualification_questions: "",
    qualification_disqualifiers: "",
    qualification_required_fields: "",
    objections: "",
    compliance_rules: "",
    handoff_rules: "",
    follow_up_rules: "",
  });

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) || null,
    [agents, selectedAgentId],
  );

  async function loadStudio(agentId: string) {
    if (!agentId) {
      setStudio(null);
      return;
    }
    const payload = await fetchJson<ConsorcioStudio>(`/api/proxy/agents/${agentId}/consorcio-studio`);
    setStudio(payload);
    setForm({
      name: payload.agent.name,
      description: payload.agent.description || "",
      prompt_system:
        payload.active_version?.prompt_system ||
        "Voce e um agente comercial consultivo para operacao interna de consorcios. Atenda com clareza, sustente fatos oficiais e conduza para o proximo passo.",
      positioning: payload.playbook.positioning,
      tone: payload.playbook.tone,
      qualification_intent: payload.playbook.qualification.intent,
      qualification_questions: joinLines(payload.playbook.qualification.questions),
      qualification_disqualifiers: joinLines(payload.playbook.qualification.disqualifiers),
      qualification_required_fields: joinLines(payload.playbook.qualification.required_fields),
      objections: formatObjections(payload.playbook.objections),
      compliance_rules: joinLines(payload.playbook.compliance_rules),
      handoff_rules: joinLines(payload.playbook.handoff_rules),
      follow_up_rules: joinLines(payload.playbook.follow_up_rules),
    });
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsLoading(true);
      setError(null);
      try {
        const agentItems = await fetchJson<AgentOption[]>("/api/proxy/agents");
        if (cancelled) {
          return;
        }
        setAgents(agentItems);
        const agentId = agentItems[0]?.id || "";
        setSelectedAgentId(agentId);
        if (agentId) {
          await loadStudio(agentId);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao carregar playbook.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedAgentId) {
      return;
    }
    void loadStudio(selectedAgentId).catch((cause) =>
      setError(cause instanceof Error ? cause.message : "Falha ao carregar agente."),
    );
  }, [selectedAgentId]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAgentId) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      const currentToolConfig = studio?.active_version?.tool_config_json || { rag_enabled: true, web_allowlist_enabled: true };
      const currentChannelConfig = studio?.active_version?.channel_config_json || {
        default_channel: "whatsapp",
        allowed_channels: ["whatsapp", "lab"],
      };
      const currentKnowledge = studio?.active_version?.knowledge_config_json || {};
      await fetchJson<ConsorcioStudio>(`/api/proxy/agents/${selectedAgentId}/consorcio-studio`, {
        method: "PATCH",
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          prompt_system: form.prompt_system,
          playbook: {
            positioning: form.positioning,
            tone: form.tone,
            qualification: {
              intent: form.qualification_intent,
              questions: splitLines(form.qualification_questions),
              disqualifiers: splitLines(form.qualification_disqualifiers),
              required_fields: splitLines(form.qualification_required_fields),
            },
            objections: parseObjections(form.objections),
            compliance_rules: splitLines(form.compliance_rules),
            handoff_rules: splitLines(form.handoff_rules),
            follow_up_rules: splitLines(form.follow_up_rules),
          },
          knowledge: currentKnowledge,
          tool_config_json: currentToolConfig,
          channel_config_json: currentChannelConfig,
          publish: true,
        }),
      });
      await loadStudio(selectedAgentId);
      setNotice("Playbook publicado com sucesso.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao salvar playbook.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Consorcios / Playbook</p>
        <h1 className="mt-3 text-3xl font-semibold">Configuracao do agente</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Ajuste posicionamento, qualificacao, objeções, compliance, handoff e follow-up do agente de consorcios.
        </p>
        <Link href="/consorcios" className="mt-4 inline-flex rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
          Voltar ao hub
        </Link>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      {notice ? <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{notice}</p> : null}

      <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold">Playbook do agente</h2>
            <p className="mt-2 text-sm text-white/60">Os dados publicados entram na próxima conversa do agente.</p>
          </div>
          <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
            {isLoading ? "carregando" : selectedAgent?.slug || "sem agente"}
          </span>
        </div>

        <form onSubmit={handleSave} className="mt-6 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-white/70">
              <span>Agente</span>
              <select
                value={selectedAgentId}
                onChange={(event) => setSelectedAgentId(event.target.value)}
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              >
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Nome</span>
              <input
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              />
            </label>
          </div>

          <label className="space-y-2 text-sm text-white/70">
            <span>Descricao</span>
            <textarea
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
              rows={3}
              className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
            />
          </label>

          <label className="space-y-2 text-sm text-white/70">
            <span>Prompt base</span>
            <textarea
              value={form.prompt_system}
              onChange={(event) => setForm((current) => ({ ...current, prompt_system: event.target.value }))}
              rows={5}
              className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
            />
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-white/70 md:col-span-2">
              <span>Posicionamento</span>
              <textarea
                value={form.positioning}
                onChange={(event) => setForm((current) => ({ ...current, positioning: event.target.value }))}
                rows={4}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Tom</span>
              <input
                value={form.tone}
                onChange={(event) => setForm((current) => ({ ...current, tone: event.target.value }))}
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Intencao da qualificacao</span>
              <input
                value={form.qualification_intent}
                onChange={(event) => setForm((current) => ({ ...current, qualification_intent: event.target.value }))}
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70 md:col-span-2">
              <span>Perguntas de qualificacao, uma por linha</span>
              <textarea
                value={form.qualification_questions}
                onChange={(event) => setForm((current) => ({ ...current, qualification_questions: event.target.value }))}
                rows={4}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Desqualificadores, um por linha</span>
              <textarea
                value={form.qualification_disqualifiers}
                onChange={(event) => setForm((current) => ({ ...current, qualification_disqualifiers: event.target.value }))}
                rows={4}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Campos obrigatorios, um por linha</span>
              <textarea
                value={form.qualification_required_fields}
                onChange={(event) => setForm((current) => ({ ...current, qualification_required_fields: event.target.value }))}
                rows={4}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70 md:col-span-2">
              <span>Objeções no formato "objeção =&gt; resposta", uma por linha</span>
              <textarea
                value={form.objections}
                onChange={(event) => setForm((current) => ({ ...current, objections: event.target.value }))}
                rows={5}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-white/70">
              <span>Regras de compliance, uma por linha</span>
              <textarea
                value={form.compliance_rules}
                onChange={(event) => setForm((current) => ({ ...current, compliance_rules: event.target.value }))}
                rows={4}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Regras de handoff, uma por linha</span>
              <textarea
                value={form.handoff_rules}
                onChange={(event) => setForm((current) => ({ ...current, handoff_rules: event.target.value }))}
                rows={4}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>Regras de follow-up, uma por linha</span>
              <textarea
                value={form.follow_up_rules}
                onChange={(event) => setForm((current) => ({ ...current, follow_up_rules: event.target.value }))}
                rows={4}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-full bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? "Publicando..." : "Publicar playbook"}
            </button>
            <Link href="/consorcios" className="rounded-full border border-white/12 px-5 py-2 text-sm text-white/80">
              Voltar ao hub
            </Link>
          </div>
        </form>

        {studio?.active_version ? (
          <p className="mt-5 text-xs text-white/45">
            Versao ativa publicada em {formatDateTimeSP(studio.active_version.created_at)}
          </p>
        ) : null}
      </article>
    </main>
  );
}
