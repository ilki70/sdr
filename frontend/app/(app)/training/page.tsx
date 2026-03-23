"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { EmptyState } from "@/components/shared/empty-state";
import { formatDateTimeSP } from "@/lib/datetime";

type Agent = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  active_version_no: number | null;
  status: string;
  updated_at: string;
};

type AgentVersion = {
  id: string;
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
  created_at: string;
};

type Persona = {
  id: string;
  name: string;
  active_version_no: number | null;
  is_active: boolean;
};

type AgentDetail = {
  agent: Agent;
  versions: AgentVersion[];
};

type TrainingCycle = {
  cycle_no: number;
  average_score: number;
  total_turns: number;
  findings: string[];
  recommendations: string[];
  conversation_ids: string[];
  applied_persona_version_no: number | null;
  applied_agent_version_no: number | null;
};

type EvaluationRun = {
  id: string;
  status: string;
  summary_json: Record<string, unknown> | null;
  report_markdown: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

type TrainingResponse = {
  evaluation_run: EvaluationRun;
  agent: Agent;
  persona: Persona | null;
  cycles: TrainingCycle[];
  summary_json: Record<string, unknown>;
  report_markdown: string;
};

const focusOptions = [
  { value: "first_attendance", label: "Primeiro atendimento" },
  { value: "qualification", label: "Qualificacao" },
  { value: "objection_handling", label: "Objeções" },
  { value: "closing", label: "Fechamento" },
  { value: "follow_up", label: "Follow-up" },
] as const;

export default function TrainingPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return new URLSearchParams(window.location.search).get("agentId");
  });
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [cycles, setCycles] = useState(1);
  const [interactionsPerCycle, setInteractionsPerCycle] = useState(4);
  const [focus, setFocus] = useState<(typeof focusOptions)[number]["value"]>("first_attendance");
  const [autoApply, setAutoApply] = useState(true);
  const [result, setResult] = useState<TrainingResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTraining, setIsTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const currentVersion = detail?.versions[0] || null;
  const linkedPersona = personas.find((persona) => persona.id === currentVersion?.persona_id) || null;
  async function loadAgentDetail(agentId: string) {
    const payload = await fetchJson<AgentDetail>(`/api/proxy/agents/${agentId}`);
    setDetail(payload);
  }

  async function loadData(preferredAgentId?: string) {
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
      setError(cause instanceof Error ? cause.message : "Falha ao carregar treinamento.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function handleRunTraining(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) {
      return;
    }
    setIsTraining(true);
    setError(null);
    setNotice(null);
    setResult(null);
    try {
      const payload = await fetchJson<TrainingResponse>(`/api/proxy/agents/${detail.agent.id}/training`, {
        method: "POST",
        body: JSON.stringify({
          cycles,
          interactions_per_cycle: interactionsPerCycle,
          focus,
          auto_apply: autoApply,
        }),
      });
      setResult(payload);
      setNotice(
        autoApply
          ? `Treino concluido e melhorias publicadas para ${payload.agent.name}.`
          : `Treino concluido para ${payload.agent.name}.`,
      );
      await loadData(payload.agent.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao executar treino.");
    } finally {
      setIsTraining(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Training Lab</p>
        <h1 className="mt-3 text-3xl font-semibold">Treino da Márcia</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Simule ciclos de atendimento, detecte pontos fracos e publique automaticamente uma nova versão da persona e do
          agente vinculado quando fizer sentido.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      {notice ? <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{notice}</p> : null}

      <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-5">
          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Agente alvo</h2>
                <p className="mt-1 text-sm text-white/60">Escolha a Márcia ou qualquer outro agente para treinar a persona vinculada.</p>
              </div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/55">{agents.length} agentes</span>
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
                <EmptyState title="Nenhum agente encontrado." description="Crie um agente antes de treinar a persona vinculada." />
              ) : null}
            </div>
          </article>

          <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-xl font-semibold">Configuração</h2>
            <form className="mt-4 space-y-3" onSubmit={handleRunTraining}>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm text-white/70">
                  <span>Ciclos</span>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={cycles}
                    onChange={(event) => setCycles(Number(event.target.value) || 1)}
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                  />
                </label>
                <label className="space-y-2 text-sm text-white/70">
                  <span>Interações por ciclo</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={interactionsPerCycle}
                    onChange={(event) => setInteractionsPerCycle(Number(event.target.value) || 1)}
                    className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                  />
                </label>
              </div>
              <label className="space-y-2 text-sm text-white/70">
                <span>Foco do treino</span>
                <select
                  value={focus}
                  onChange={(event) => setFocus(event.target.value as (typeof focusOptions)[number]["value"])}
                  className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                >
                  {focusOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/75">
                <input
                  type="checkbox"
                  checked={autoApply}
                  onChange={(event) => setAutoApply(event.target.checked)}
                  className="h-4 w-4 rounded border-white/30 bg-transparent"
                />
                Aplicar as melhorias automaticamente no final de cada ciclo
              </label>
              <button
                type="submit"
                disabled={isTraining || !detail}
                className="rounded-full bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isTraining ? "Treinando..." : "Executar treino"}
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
                    <h2 className="text-xl font-semibold">Contexto atual</h2>
                    <p className="mt-1 text-sm text-white/60">A persona ativa da Márcia é o alvo do treinador.</p>
                  </div>
                  <Link
                    href={`/agents?agentId=${detail.agent.id}`}
                    className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/80 transition hover:bg-white/10"
                  >
                    Abrir agente
                  </Link>
                </div>
                <div className="mt-4 rounded-[20px] border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-wide text-white/40">Agente</p>
                  <p className="mt-2 text-sm text-white/80">{detail.agent.name}</p>
                  <p className="mt-4 text-xs uppercase tracking-wide text-white/40">Persona vinculada</p>
                  <p className="mt-2 text-sm text-white/80">
                    {linkedPersona
                      ? `${linkedPersona.name} • v${currentVersion?.persona_version_no ?? linkedPersona.active_version_no ?? "-"}`
                      : "Sem persona vinculada"}
                  </p>
                  <p className="mt-4 text-xs uppercase tracking-wide text-white/40">Prompt ativo</p>
                  <p className="mt-2 line-clamp-4 text-sm text-white/65">{currentVersion?.prompt_system || "Sem versao publicada."}</p>
                </div>
              </article>

              {result ? (
                <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-semibold">Resultado</h2>
                      <p className="mt-1 text-sm text-white/60">Última execução de treino concluída.</p>
                    </div>
                    <span className="rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/10 px-3 py-1 text-xs text-emerald-100">
                      {result.evaluation_run.status}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {result.cycles.map((cycle) => (
                      <div key={cycle.cycle_no} className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <strong className="text-sm">Ciclo {cycle.cycle_no}</strong>
                          <span className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-white/55">
                            {cycle.average_score.toFixed(2)}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-white/40">{cycle.total_turns} interacoes simuladas</p>
                        <ul className="mt-3 space-y-1 text-sm text-white/70">
                          {cycle.recommendations.slice(0, 4).map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 rounded-[20px] border border-white/10 bg-black/20 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/40">Resumo do treino</p>
                    <pre className="mt-3 whitespace-pre-wrap text-sm text-white/75">{result.report_markdown}</pre>
                  </div>

                  <div className="mt-4 rounded-[20px] border border-white/10 bg-black/20 p-4 text-sm text-white/70">
                    <p>
                      Persona publicada: {typeof result.summary_json.applied_persona_version_no === "number" ? `v${result.summary_json.applied_persona_version_no}` : "não publicada"}
                    </p>
                    <p className="mt-1">
                      Agente publicado: {typeof result.summary_json.applied_agent_version_no === "number" ? `v${result.summary_json.applied_agent_version_no}` : "não publicado"}
                    </p>
                  </div>
                </article>
              ) : (
                <section className="rounded-[24px] border border-white/10 bg-white/5 p-6">
                  <EmptyState
                    title="Nenhum treino executado ainda."
                    description="Rode um ciclo para gerar recomendações e, se habilitado, publicar novas versões da persona e do agente."
                  />
                </section>
              )}
            </>
          ) : (
            <section className="rounded-[24px] border border-white/10 bg-white/5 p-6">
              <EmptyState title="Nenhum agente selecionado." description="Escolha a Márcia ou outro agente para iniciar o treino." />
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
