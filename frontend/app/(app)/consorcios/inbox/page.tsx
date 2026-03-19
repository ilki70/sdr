"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type ConversationSummary = {
  id: string;
  agent_id: string | null;
  title: string;
  channel: string;
  status: string;
  lead_id: string;
  started_at: string;
  updated_at: string;
  last_message_preview: string | null;
  message_count: number;
};

type ConversationMessage = {
  id: string;
  conversation_id: string;
  sender_type: string;
  direction: string;
  content: string;
  model_name: string | null;
  metadata_json: Record<string, unknown> | null;
  sent_at: string;
};

type ConversationDetail = {
  conversation: ConversationSummary;
  messages: ConversationMessage[];
};

type AgentOption = {
  id: string;
  name: string;
  slug: string;
};

function statusTone(status: string): string {
  if (status === "completed" || status === "ready") {
    return "border-emerald-400/25 text-emerald-200";
  }
  if (status === "failed") {
    return "border-red-400/30 text-red-100";
  }
  if (status === "running" || status === "processing" || status === "in_progress") {
    return "border-amber-400/25 text-amber-100";
  }
  return "border-white/10 text-white/60";
}

export default function ConsorciosInboxPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedChannel, setSelectedChannel] = useState("all");
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      fetchJson<ConversationSummary[]>("/api/proxy/messages/conversations"),
      fetchJson<AgentOption[]>("/api/proxy/agents"),
    ])
      .then(([conversationItems, agentItems]) => {
        if (cancelled) {
          return;
        }
        setConversations(conversationItems);
        setAgents(agentItems);
        setSelectedConversationId((current) => current || conversationItems[0]?.id || null);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar inbox."));
    return () => {
      cancelled = true;
    };
  }, []);

  const visibleConversations = useMemo(() => {
    return conversations.filter((conversation) => {
      if (selectedAgentId !== "all" && conversation.agent_id !== selectedAgentId) {
        return false;
      }
      if (selectedStatus !== "all" && conversation.status !== selectedStatus) {
        return false;
      }
      if (selectedChannel !== "all" && conversation.channel !== selectedChannel) {
        return false;
      }
      return true;
    });
  }, [conversations, selectedAgentId, selectedStatus, selectedChannel]);

  const selectedConversation = useMemo(
    () => visibleConversations.find((conversation) => conversation.id === selectedConversationId) || null,
    [visibleConversations, selectedConversationId],
  );

  useEffect(() => {
    if (visibleConversations.length === 0) {
      setSelectedConversationId(null);
      setDetail(null);
      return;
    }
    if (!visibleConversations.some((conversation) => conversation.id === selectedConversationId)) {
      setSelectedConversationId(visibleConversations[0].id);
    }
  }, [visibleConversations, selectedConversationId]);

  useEffect(() => {
    if (!selectedConversationId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setIsLoadingDetail(true);
    setError(null);
    void fetchJson<ConversationDetail>(`/api/proxy/messages/conversations/${selectedConversationId}`)
      .then((payload) => {
        if (!cancelled) {
          setDetail(payload);
        }
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar conversa."))
      .finally(() => {
        if (!cancelled) {
          setIsLoadingDetail(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedConversationId]);

  const totals = useMemo(() => {
    const open = conversations.filter((conversation) => conversation.status !== "closed").length;
    const closed = conversations.filter((conversation) => conversation.status === "closed").length;
    const handoff = conversations.filter((conversation) => conversation.status === "handoff" || conversation.status === "waiting_human").length;
    return { open, closed, handoff };
  }, [conversations]);

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(59,130,246,0.10),rgba(255,255,255,0.04))] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Consorcios / Inbox</p>
            <h1 className="mt-3 text-3xl font-semibold">Central de conversas e handoff</h1>
            <p className="mt-2 max-w-3xl text-sm text-white/70">
              Tela de operação para acompanhar atendimentos, filtrar por agente e escalar o que precisa de humano.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/consorcios" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
              Hub
            </Link>
            <Link href="/consorcios/playbook" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
              Playbook
            </Link>
            <Link href="/consorcios/knowledge" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
              Knowledge
            </Link>
          </div>
        </div>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}

      <section className="grid gap-5 xl:grid-cols-3">
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Abertas</p>
          <p className="mt-3 text-3xl font-semibold">{totals.open}</p>
        </article>
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Em handoff</p>
          <p className="mt-3 text-3xl font-semibold">{totals.handoff}</p>
        </article>
        <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-white/60">Fechadas</p>
          <p className="mt-3 text-3xl font-semibold">{totals.closed}</p>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[380px_1fr]">
        <aside className="space-y-4">
          <article className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">Filtros</h2>
            <div className="mt-4 space-y-3">
              <label className="space-y-2 text-sm text-white/70">
                <span>Agente</span>
                <select
                  value={selectedAgentId}
                  onChange={(event) => setSelectedAgentId(event.target.value)}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 outline-none"
                >
                  <option value="all">Todos</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Status</span>
                <select
                  value={selectedStatus}
                  onChange={(event) => setSelectedStatus(event.target.value)}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 outline-none"
                >
                  <option value="all">Todos</option>
                  <option value="open">open</option>
                  <option value="waiting_human">waiting_human</option>
                  <option value="handoff">handoff</option>
                  <option value="closed">closed</option>
                </select>
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Canal</span>
                <select
                  value={selectedChannel}
                  onChange={(event) => setSelectedChannel(event.target.value)}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 outline-none"
                >
                  <option value="all">Todos</option>
                  <option value="whatsapp">whatsapp</option>
                  <option value="lab">lab</option>
                  <option value="web">web</option>
                </select>
              </label>
            </div>
          </article>

          <article className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">Conversa selecionada</h2>
            {selectedConversation ? (
              <div className="mt-4 space-y-2 text-sm text-white/70">
                <p>Lead: {selectedConversation.lead_id}</p>
                <p>Canal: {selectedConversation.channel}</p>
                <p>Status: {selectedConversation.status}</p>
                <p>Mensagens: {selectedConversation.message_count}</p>
                <p>Atualizada em {formatDateTimeSP(selectedConversation.updated_at)}</p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-white/50">Nenhuma conversa selecionada.</p>
            )}
            <div className="mt-4 rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm text-white/65">
              Handoff humano deve acontecer quando houver necessidade de proposta, excecao comercial ou validacao contratual.
            </div>
          </article>

          <article className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">Acoes</h2>
            <div className="mt-4 space-y-3 text-sm text-white/75">
              <p>• Revisar leads parados com mais de uma troca sem avancar.</p>
              <p>• Levar para a Turn2C apenas o que estiver pronto para simulacao.</p>
              <p>• Manter o follow-up externo ao sistema quando o atendente ja estiver em handshake humano.</p>
            </div>
            <Link href="/agent-lab" className="mt-4 inline-flex rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black">
              Abrir Agent Lab
            </Link>
          </article>
        </aside>

        <section className="space-y-4">
          <article className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Fila ativa</h2>
                <p className="mt-1 text-sm text-white/60">Lista filtrada da inbox operacional.</p>
              </div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/55">{visibleConversations.length} itens</span>
            </div>
            <div className="mt-4 space-y-3">
              {visibleConversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => setSelectedConversationId(conversation.id)}
                  className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                    selectedConversationId === conversation.id ? "border-[var(--accent)]/60 bg-black/30" : "border-white/10 bg-black/20"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <strong className="text-sm">{conversation.title}</strong>
                    <span className="text-[11px] uppercase tracking-wide text-white/45">{conversation.channel}</span>
                  </div>
                  <p className="mt-2 text-sm text-white/70">{conversation.last_message_preview || "Sem mensagens."}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-white/45">
                    <span className={`rounded-full border px-2 py-1 ${statusTone(conversation.status)}`}>{conversation.status}</span>
                    <span>{agents.find((agent) => agent.id === conversation.agent_id)?.name || "nao atribuido"}</span>
                    <span>{conversation.message_count} mensagens</span>
                    <span>{formatDateTimeSP(conversation.updated_at)}</span>
                  </div>
                </button>
              ))}
              {!error && visibleConversations.length === 0 ? (
                <article className="rounded-[24px] border border-dashed border-white/15 bg-black/20 p-5 text-sm text-white/60">
                  Nenhuma conversa encontrada para o filtro atual.
                </article>
              ) : null}
            </div>
          </article>

          <article className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Detalhe da conversa</h2>
                <p className="mt-1 text-sm text-white/60">Mensagens e contexto do atendimento selecionado.</p>
              </div>
              {isLoadingDetail ? <span className="text-xs text-white/45">Carregando...</span> : null}
            </div>
            <div className="mt-4 space-y-3">
              {(detail?.messages || []).map((message) => (
                <article
                  key={message.id}
                  className={`rounded-2xl border p-4 ${message.sender_type === "assistant" ? "border-emerald-400/20 bg-emerald-500/10" : "border-white/10 bg-black/20"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <strong className="text-sm capitalize">{message.sender_type}</strong>
                    <span className="text-[11px] uppercase tracking-wide text-white/45">{message.direction}</span>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-white/75">{message.content}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-white/45">
                    <span>{formatDateTimeSP(message.sent_at)}</span>
                    {message.model_name ? <span>{message.model_name}</span> : null}
                  </div>
                </article>
              ))}
              {detail && detail.messages.length === 0 ? (
                <p className="text-sm text-white/50">Conversa sem mensagens ainda.</p>
              ) : null}
            </div>
          </article>
        </section>
      </section>
    </main>
  );
}
