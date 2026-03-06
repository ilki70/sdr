"use client";

import { useEffect, useState } from "react";

import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type DashboardJob = {
  id: string;
  job_type: string;
  status: string;
  created_at: string;
  product_id: string;
};

type DashboardConversation = {
  id: string;
  status: string;
  updated_at: string;
  title: string;
  message_count: number;
  last_message_preview: string | null;
};

type EvaluationRun = {
  id: string;
  status: string;
  evaluation_type: string;
  summary_json: Record<string, unknown> | null;
  created_at: string;
};

type StageMetric = {
  stage: string;
  count: number;
};

type HandoffQueueItem = {
  conversation_id: string;
  title: string;
  lead_id: string;
  channel: string;
  handoff_reason: string | null;
  updated_at: string;
  last_message_preview: string | null;
};

type DashboardOverview = {
  lead_count: number;
  engaged_lead_count: number;
  client_count: number;
  product_count: number;
  conversation_count: number;
  qualification_started_count: number;
  handoff_ready_count: number;
  avg_messages_per_conversation: number;
  active_rule_count: number;
  active_integration_count: number;
  sales_count: number;
  revenue_total: string;
  stage_metrics: StageMetric[];
  handoff_queue: HandoffQueueItem[];
  recent_jobs: DashboardJob[];
  recent_conversations: DashboardConversation[];
  latest_evaluation: EvaluationRun | null;
};

type WhatsAppGatewayStatus = {
  connected: boolean;
  session_status: string;
  paired_phone: string | null;
  qr_code_data_url: string | null;
  qr_code_text: string | null;
  last_event: string | null;
  last_error: string | null;
  last_inbound_at: string | null;
  last_inbound_chat: string | null;
  last_inbound_preview: string | null;
  last_callback_status: string | null;
  last_outbound_at: string | null;
  last_outbound_chat: string | null;
  last_outbound_preview: string | null;
  updated_at: string | null;
};

type WhatsAppSessionStatus = {
  integration_exists: boolean;
  integration_id: string | null;
  provider: string;
  integration_status: string;
  inbox_ref: string | null;
  api_base_url: string | null;
  config_json: Record<string, unknown> | null;
  gateway: WhatsAppGatewayStatus;
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [whatsApp, setWhatsApp] = useState<WhatsAppSessionStatus | null>(null);
  const [whatsAppError, setWhatsAppError] = useState<string | null>(null);
  const [isWhatsAppSaving, setIsWhatsAppSaving] = useState(false);

  async function loadDashboard() {
    const overview = await fetchJson<DashboardOverview>("/api/proxy/dashboard/overview");
    setData(overview);
  }

  async function loadWhatsAppStatus() {
    try {
      const status = await fetchJson<WhatsAppSessionStatus>("/api/proxy/whatsapp/session");
      setWhatsApp(status);
      setWhatsAppError(null);
    } catch (cause) {
      setWhatsAppError(cause instanceof Error ? cause.message : "Falha ao carregar status do WhatsApp.");
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [overview] = await Promise.all([fetchJson<DashboardOverview>("/api/proxy/dashboard/overview")]);
        if (!cancelled) {
          setData(overview);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao carregar dashboard.");
        }
      }
    }
    void load();
    void loadWhatsAppStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!whatsApp) {
      return;
    }
    if (!["pairing", "connecting"].includes(whatsApp.gateway.session_status)) {
      return;
    }
    const handle = window.setInterval(() => {
      void loadWhatsAppStatus();
    }, 5000);
    return () => window.clearInterval(handle);
  }, [whatsApp]);

  async function runWhatsAppAction(path: string) {
    setIsWhatsAppSaving(true);
    setWhatsAppError(null);
    try {
      const status = await fetchJson<WhatsAppSessionStatus>(path, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setWhatsApp(status);
      await loadDashboard();
    } catch (cause) {
      setWhatsAppError(cause instanceof Error ? cause.message : "Falha na operacao do WhatsApp.");
    } finally {
      setIsWhatsAppSaving(false);
    }
  }

  const coreCards = [
    { label: "Leads", value: data?.lead_count ?? 0 },
    { label: "Leads engajados", value: data?.engaged_lead_count ?? 0 },
    { label: "Clientes", value: data?.client_count ?? 0 },
    { label: "Produtos", value: data?.product_count ?? 0 },
    { label: "Conversas", value: data?.conversation_count ?? 0 },
    { label: "Vendas", value: data?.sales_count ?? 0 },
  ];

  const funnelCards = [
    { label: "Qualificacao iniciada", value: data?.qualification_started_count ?? 0 },
    { label: "Prontas para handoff", value: data?.handoff_ready_count ?? 0 },
    { label: "Media de mensagens", value: data?.avg_messages_per_conversation ?? 0 },
    { label: "Integracoes ativas", value: data?.active_integration_count ?? 0 },
    { label: "Regras de comissao", value: data?.active_rule_count ?? 0 },
  ];
  const stageMetrics = data?.stage_metrics ?? [];

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Control Room</p>
        <h1 className="mt-3 text-3xl font-semibold">Dashboard operacional</h1>
        <p className="mt-2 text-sm text-white/70">
          Referencia horaria fixa em Sao Paulo. Este painel agrega metricas operacionais e agora tambem controla o pareamento do WhatsApp por QR code.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}

      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(37,211,102,0.12),rgba(37,211,102,0.04))] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.24em] text-[#7dffb4]">WhatsApp Gateway</p>
            <h2 className="mt-2 text-2xl font-semibold">Pareamento por QR code no dashboard</h2>
            <p className="mt-2 max-w-2xl text-sm text-white/70">
              O gateway em Go usa `whatsmeow`, persiste a sessao do dispositivo e encaminha mensagens recebidas para o backend responder automaticamente com o agente.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void runWhatsAppAction("/api/proxy/whatsapp/bootstrap")}
              disabled={isWhatsAppSaving}
              className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/85 disabled:opacity-60"
            >
              {whatsApp?.integration_exists ? "Reconfigurar gateway" : "Criar canal WhatsApp"}
            </button>
            <button
              type="button"
              onClick={() => void runWhatsAppAction("/api/proxy/whatsapp/session/connect")}
              disabled={isWhatsAppSaving}
              className="rounded-full bg-[#25D366] px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
            >
              {isWhatsAppSaving ? "Processando..." : "Gerar QR code"}
            </button>
            <button
              type="button"
              onClick={() => void runWhatsAppAction("/api/proxy/whatsapp/session/disconnect")}
              disabled={isWhatsAppSaving || !whatsApp?.integration_exists}
              className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/85 disabled:opacity-60"
            >
              Desconectar
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-[24px] border border-white/10 bg-black/20 p-5">
            <p className="text-[11px] uppercase tracking-wide text-white/40">Status da sessao</p>
            <p className="mt-3 text-2xl font-semibold text-white">{whatsApp?.gateway.session_status || "indisponivel"}</p>
            <div className="mt-4 space-y-2 text-sm text-white/70">
              <p>Integracao: {whatsApp?.integration_exists ? whatsApp.inbox_ref || "whatsapp-primary" : "nao criada"}</p>
              <p>Conectado: {whatsApp?.gateway.connected ? "sim" : "nao"}</p>
              <p>Numero pareado: {whatsApp?.gateway.paired_phone || "aguardando"}</p>
              <p>Ultimo evento: {whatsApp?.gateway.last_event || "-"}</p>
              <p>Ultimo callback: {whatsApp?.gateway.last_callback_status || "-"}</p>
              <p>Ultimo inbound: {whatsApp?.gateway.last_inbound_at ? formatDateTimeSP(whatsApp.gateway.last_inbound_at) : "-"}</p>
              <p>Preview inbound: {whatsApp?.gateway.last_inbound_preview || "-"}</p>
              <p>Ultimo outbound: {whatsApp?.gateway.last_outbound_at ? formatDateTimeSP(whatsApp.gateway.last_outbound_at) : "-"}</p>
              <p>Preview outbound: {whatsApp?.gateway.last_outbound_preview || "-"}</p>
              <p>Atualizado: {whatsApp?.gateway.updated_at ? formatDateTimeSP(whatsApp.gateway.updated_at) : "-"}</p>
            </div>
            {whatsAppError ? <p className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{whatsAppError}</p> : null}
            {whatsApp?.gateway.last_error ? <p className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">{whatsApp.gateway.last_error}</p> : null}
          </div>

          <div className="rounded-[24px] border border-white/10 bg-black/20 p-5">
            <p className="text-[11px] uppercase tracking-wide text-white/40">QR code</p>
            <div className="mt-4 flex min-h-[320px] items-center justify-center rounded-[24px] border border-dashed border-white/15 bg-white/5 p-4">
              {whatsApp?.gateway.qr_code_data_url ? (
                <img src={whatsApp.gateway.qr_code_data_url} alt="QR code para conectar o WhatsApp" className="h-[280px] w-[280px] rounded-2xl bg-white p-3" />
              ) : (
                <div className="max-w-md text-center text-sm leading-7 text-white/60">
                  <p>1. Crie ou reconfigure o canal WhatsApp.</p>
                  <p>2. Clique em `Gerar QR code`.</p>
                  <p>3. Escaneie pelo WhatsApp no celular.</p>
                  <p>4. Depois disso, as mensagens recebidas passam a cair no agente automaticamente.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {coreCards.map((card) => (
          <article key={card.label} className="rounded-[24px] border border-white/10 bg-white/5 p-5">
            <p className="text-sm text-white/60">{card.label}</p>
            <p className="mt-3 text-3xl font-semibold">{card.value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-5">
        {funnelCards.map((card) => (
          <article key={card.label} className="rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(122,210,255,0.12),rgba(122,210,255,0.04))] p-5">
            <p className="text-sm text-white/60">{card.label}</p>
            <p className="mt-3 text-3xl font-semibold">{card.value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stageMetrics.map((metric) => (
          <article key={metric.stage} className="rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,193,122,0.12),rgba(255,193,122,0.04))] p-5">
            <p className="text-sm capitalize text-white/60">{metric.stage}</p>
            <p className="mt-3 text-3xl font-semibold">{metric.count}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Receita total registrada</p>
          <p className="mt-3 text-3xl font-semibold">R$ {data?.revenue_total ?? "0.00"}</p>
        </article>
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Ambiente</p>
          <p className="mt-3 text-lg font-semibold">America/Sao_Paulo</p>
          <p className="mt-2 text-xs text-white/50">Todas as datas exibidas neste dashboard usam esse fuso.</p>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-semibold">Atividade recente</h2>
          <div className="mt-5 space-y-3">
            {data?.recent_jobs.map((job) => (
              <article key={job.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">{job.job_type}</strong>
                  <span className="text-xs uppercase tracking-wide text-white/50">{job.status}</span>
                </div>
                <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(job.created_at)}</p>
                <p className="mt-2 text-xs text-white/35">Produto {job.product_id.slice(0, 8)}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="space-y-5">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold">Ultima avaliacao</h2>
            {data?.latest_evaluation ? (
              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-sm text-white/70">{data.latest_evaluation.evaluation_type}</p>
                <p className="mt-2 text-2xl font-semibold">{data.latest_evaluation.status}</p>
                <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(data.latest_evaluation.created_at)}</p>
                <p className="mt-3 text-sm text-white/70">
                  Media: {String(data.latest_evaluation.summary_json?.average_score ?? "-")} | Aprovados:{" "}
                  {String(data.latest_evaluation.summary_json?.passed_count ?? "-")}
                </p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-white/60">Nenhuma avaliacao automatica encontrada.</p>
            )}
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold">Conversas recentes</h2>
            <div className="mt-4 space-y-3">
              {data?.recent_conversations.map((conversation) => (
                <article key={conversation.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <strong className="text-sm">{conversation.title}</strong>
                  <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(conversation.updated_at)}</p>
                  <p className="mt-2 text-sm text-white/65">{conversation.last_message_preview || "Sem mensagens ainda."}</p>
                  <p className="mt-2 text-xs uppercase tracking-wide text-white/35">{conversation.message_count} mensagens</p>
                </article>
              ))}
            </div>
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold">Fila de handoff</h2>
            <div className="mt-4 space-y-3">
              {data?.handoff_queue.length ? (
                data.handoff_queue.map((item) => (
                  <article key={item.conversation_id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <strong className="text-sm">{item.title}</strong>
                    <p className="mt-2 text-xs uppercase tracking-wide text-white/35">{item.channel}</p>
                    <p className="mt-2 text-sm text-white/65">{item.handoff_reason || "handoff solicitado"}</p>
                    <p className="mt-2 text-xs text-white/50">{formatDateTimeSP(item.updated_at)}</p>
                  </article>
                ))
              ) : (
                <p className="text-sm text-white/60">Nenhuma conversa aguardando humano.</p>
              )}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
