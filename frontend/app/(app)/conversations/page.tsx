"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import { EmptyState } from "@/components/shared/empty-state";

type LeadPipelineStatus = "new" | "qualifying" | "handoff" | "scheduled" | "disqualified";

type Conversation = {
  id: string;
  agent_id: string | null;
  title: string;
  channel: string;
  status: string;
  lead_name?: string | null;
  lead_phone?: string | null;
  lead_cpf?: string | null;
  lead_profile_missing_fields?: string[];
  agent_paused?: boolean;
  message_count: number;
  started_at?: string | null;
  updated_at: string;
  last_message_preview: string | null;
  summary?: string;
  pipeline_status?: LeadPipelineStatus;
};

type DecoratedConversation = Conversation & {
  summary: string;
  pipeline_status: LeadPipelineStatus;
  next_step: string;
};

type SortField = "started_at" | "updated_at" | "title" | "pipeline_status";

type AgentOption = {
  id: string;
  name: string;
  slug: string;
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
  conversation: Conversation;
  messages: ConversationMessage[];
};

function statusLabel(status: LeadPipelineStatus): string {
  switch (status) {
    case "new":
      return "Novo";
    case "qualifying":
      return "Qualificando";
    case "handoff":
      return "Aguardando humano";
    case "scheduled":
      return "Agendado";
    case "disqualified":
      return "Desqualificado";
    default:
      return status;
  }
}

function statusTone(status: LeadPipelineStatus): string {
  switch (status) {
    case "new":
      return "border-cyan-400/30 bg-cyan-500/10 text-cyan-200";
    case "qualifying":
      return "border-blue-400/30 bg-blue-500/10 text-blue-200";
    case "handoff":
      return "border-amber-400/30 bg-amber-500/10 text-amber-100";
    case "scheduled":
      return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
    case "disqualified":
      return "border-rose-400/30 bg-rose-500/10 text-rose-100";
    default:
      return "border-slate-700 bg-slate-800/80 text-slate-200";
  }
}

function inferMockStatus(conversation: Conversation): LeadPipelineStatus {
  const folded = `${conversation.status} ${conversation.title} ${conversation.last_message_preview || ""}`.toLowerCase();
  if (folded.includes("closed") || folded.includes("desqual")) {
    return "disqualified";
  }
  if (folded.includes("waiting_human") || folded.includes("handoff") || folded.includes("humano")) {
    return "handoff";
  }
  if (folded.includes("agend") || folded.includes("visita") || folded.includes("reuni")) {
    return "scheduled";
  }
  if (conversation.message_count <= 1) {
    return "new";
  }
  return "qualifying";
}

function leadFieldLabel(field: string): string {
  switch (field) {
    case "nome_completo":
      return "nome completo";
    case "cpf":
      return "CPF";
    case "telefone":
      return "telefone";
    default:
      return field;
  }
}

function buildMockSummary(conversation: Conversation): string {
  const preview = conversation.last_message_preview?.trim();
  if (preview) {
    return preview;
  }
  const foldedChannel = conversation.channel.toLowerCase();
  if (foldedChannel === "whatsapp") {
    return "Lead entrou pelo WhatsApp e ainda não há contexto suficiente registrado no resumo.";
  }
  if (foldedChannel === "lab") {
    return "Sessão de laboratório aberta para testar roteiro, objeções e próximos passos do agente.";
  }
  return "Conversa iniciada na operação comercial, aguardando mais contexto para qualificação.";
}

function decorateConversation(conversation: Conversation): DecoratedConversation {
  const pipelineStatus = conversation.pipeline_status || inferMockStatus(conversation);
  return {
    ...conversation,
    lead_profile_missing_fields: conversation.lead_profile_missing_fields || [],
    agent_paused: conversation.agent_paused || false,
    summary: conversation.summary || buildMockSummary(conversation),
    pipeline_status: pipelineStatus,
    next_step:
      pipelineStatus === "handoff"
        ? "Assumir atendimento humano e revisar contexto"
        : pipelineStatus === "scheduled"
          ? "Confirmar horario e preparar follow-up"
          : pipelineStatus === "disqualified"
            ? "Registrar motivo e encerrar no funil"
            : pipelineStatus === "new"
              ? "Fazer primeira qualificacao"
              : "Aprofundar necessidade e conduzir proximo passo",
  };
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("all");
  const [selectedPipelineStatus, setSelectedPipelineStatus] = useState<"all" | LeadPipelineStatus>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<SortField>("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isUpdatingPipelineStatus, setIsUpdatingPipelineStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailPipelineStatus, setDetailPipelineStatus] = useState<LeadPipelineStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      fetchJson<Conversation[]>("/api/proxy/messages/conversations"),
      fetchJson<AgentOption[]>("/api/proxy/agents"),
    ])
      .then(([conversationItems, agentItems]) => {
        if (cancelled) {
          return;
        }
        setConversations(conversationItems);
        setAgents(agentItems);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar conversas."));
    return () => {
      cancelled = true;
    };
  }, []);

  const visibleConversations = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const items =
      selectedAgentId === "all"
        ? conversations
        : conversations.filter((conversation) => conversation.agent_id === selectedAgentId);
    const filtered = items
      .map(decorateConversation)
      .filter((conversation) => {
        if (selectedPipelineStatus !== "all" && conversation.pipeline_status !== selectedPipelineStatus) {
          return false;
        }
        if (!normalizedSearch) {
          return true;
        }
        const haystack = `${conversation.title} ${conversation.summary} ${conversation.channel}`.toLowerCase();
        const leadFields = `${conversation.lead_name || ""} ${conversation.lead_phone || ""} ${conversation.lead_cpf || ""}`.toLowerCase();
        return `${haystack} ${leadFields}`.includes(normalizedSearch);
      });

    return [...filtered].sort((left, right) => {
      let comparison = 0;
      if (sortField === "title") {
        comparison = left.title.localeCompare(right.title, "pt-BR");
      } else if (sortField === "pipeline_status") {
        comparison = statusLabel(left.pipeline_status).localeCompare(statusLabel(right.pipeline_status), "pt-BR");
      } else {
        const leftValue = new Date((left[sortField] || left.updated_at) as string).getTime();
        const rightValue = new Date((right[sortField] || right.updated_at) as string).getTime();
        comparison = leftValue - rightValue;
      }
      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [conversations, searchTerm, selectedAgentId, selectedPipelineStatus, sortDirection, sortField]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedAgentId, selectedPipelineStatus, sortDirection, sortField]);

  const totalPages = Math.max(1, Math.ceil(visibleConversations.length / pageSize));
  const paginatedConversations = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return visibleConversations.slice(startIndex, startIndex + pageSize);
  }, [currentPage, pageSize, visibleConversations]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  function toggleSort(field: SortField) {
    if (field === sortField) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortField(field);
    setSortDirection(field === "title" || field === "pipeline_status" ? "asc" : "desc");
  }

  async function openConversation(conversationId: string) {
    setSelectedConversationId(conversationId);
    setIsLoadingDetail(true);
    setError(null);
    try {
      const payload = await fetchJson<ConversationDetail>(`/api/proxy/messages/conversations/${conversationId}`);
      setDetail(payload);
      setDetailPipelineStatus(decorateConversation(payload.conversation).pipeline_status);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar detalhe da conversa.");
    } finally {
      setIsLoadingDetail(false);
    }
  }

  function closeConversation() {
    setSelectedConversationId(null);
    setDetail(null);
    setDetailPipelineStatus(null);
  }

  async function applyQuickStatus(nextStatus: LeadPipelineStatus) {
    if (!selectedConversationId) {
      return;
    }
    setIsUpdatingPipelineStatus(true);
    setError(null);
    try {
      const payload = await fetchJson<ConversationDetail>(
        `/api/proxy/messages/conversations/${selectedConversationId}/pipeline-status`,
        {
          method: "PATCH",
          body: JSON.stringify({ pipeline_status: nextStatus }),
        },
      );
      setDetail(payload);
      setDetailPipelineStatus(nextStatus);
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === payload.conversation.id
            ? {
                ...conversation,
                ...payload.conversation,
              }
            : conversation,
        ),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao atualizar status da conversa.");
    } finally {
      setIsUpdatingPipelineStatus(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-slate-800 bg-slate-900 p-6 shadow-[0_24px_80px_rgba(2,6,23,0.35)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-50">Conversas</h1>
            <p className="mt-2 text-sm text-slate-400">
              Acompanhamento do funil do SDR com foco em entrada, qualificação, handoff e avanço operacional dos leads.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Buscar por nome, contato ou resumo"
              className="min-w-[260px] rounded-full border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500"
            />
            <select
              value={selectedAgentId}
              onChange={(event) => setSelectedAgentId(event.target.value)}
              className="rounded-full border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-slate-100 outline-none"
            >
              <option value="all">Todos os agentes</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
            <select
              value={selectedPipelineStatus}
              onChange={(event) => setSelectedPipelineStatus(event.target.value as "all" | LeadPipelineStatus)}
              className="rounded-full border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-slate-100 outline-none"
            >
              <option value="all">Todos os status</option>
              <option value="new">Novo</option>
              <option value="qualifying">Qualificando</option>
              <option value="handoff">Aguardando humano</option>
              <option value="scheduled">Agendado</option>
              <option value="disqualified">Desqualificado</option>
            </select>
            <Link href="/agent-lab" className="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black">
              Abrir Agent Lab
            </Link>
          </div>
        </div>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}

      <section className="overflow-hidden rounded-[28px] border border-slate-800 bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Acompanhamento de leads</h2>
            <p className="mt-1 text-sm text-slate-500">
              {visibleConversations.length} leads no filtro atual. Pagina {currentPage} de {totalPages}.
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <span>Linhas por pagina</span>
            <select
              value={pageSize}
              onChange={(event) => setPageSize(Number(event.target.value))}
              className="rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={30}>30</option>
            </select>
          </label>
        </div>

        {visibleConversations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm text-slate-200">
              <thead className="bg-slate-950/80 text-xs uppercase tracking-[0.18em] text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">
                    <button type="button" onClick={() => toggleSort("started_at")} className="transition hover:text-slate-200">
                      Data de Entrada {sortField === "started_at" ? (sortDirection === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </th>
                  <th className="px-4 py-3 font-medium">
                    <button type="button" onClick={() => toggleSort("updated_at")} className="transition hover:text-slate-200">
                      Ultima Interacao {sortField === "updated_at" ? (sortDirection === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </th>
                  <th className="px-4 py-3 font-medium">
                    <button type="button" onClick={() => toggleSort("title")} className="transition hover:text-slate-200">
                      Nome / Contato {sortField === "title" ? (sortDirection === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </th>
                  <th className="px-4 py-3 font-medium">
                    <button type="button" onClick={() => toggleSort("pipeline_status")} className="transition hover:text-slate-200">
                      Status {sortField === "pipeline_status" ? (sortDirection === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </th>
                  <th className="px-4 py-3 font-medium">Agente responsavel</th>
                  <th className="px-4 py-3 font-medium">Proximo passo</th>
                  <th className="px-4 py-3 font-medium">Resumo da Conversa</th>
                  <th className="px-4 py-3 text-right font-medium">Acao</th>
                </tr>
              </thead>
              <tbody>
                {paginatedConversations.map((conversation) => (
                  <tr
                    key={conversation.id}
                    className={`border-t border-slate-800 transition hover:bg-slate-800 ${
                      conversation.pipeline_status === "handoff" ? "bg-amber-500/5" : ""
                    }`}
                  >
                    <td className="px-4 py-3 text-slate-300">
                      {formatDateTimeSP(conversation.started_at || conversation.updated_at)}
                    </td>
                    <td className="px-4 py-3 text-slate-300">{formatDateTimeSP(conversation.updated_at)}</td>
                    <td className="px-4 py-3">
                      {(() => {
                        const missingFields = conversation.lead_profile_missing_fields || [];
                        return (
                      <div className="min-w-[220px]">
                        <p className="font-medium text-slate-100">{conversation.lead_name || conversation.title}</p>
                        <p className="mt-1 text-xs text-slate-400">{conversation.lead_phone || "Telefone nao capturado"}</p>
                        <p className="mt-1 text-xs text-slate-500">{conversation.lead_cpf || "CPF nao capturado"}</p>
                        <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{conversation.channel}</p>
                        {missingFields.length > 0 ? (
                          <p className="mt-2 text-[11px] uppercase tracking-wide text-amber-300">
                            Faltando: {missingFields.map(leadFieldLabel).join(", ")}
                          </p>
                        ) : null}
                      </div>
                        );
                      })()}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${statusTone(conversation.pipeline_status)}`}
                      >
                        {statusLabel(conversation.pipeline_status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      <div>
                        <p>{agents.find((agent) => agent.id === conversation.agent_id)?.name || "Nao atribuido"}</p>
                        {conversation.agent_paused ? (
                          <p className="mt-1 text-[11px] uppercase tracking-wide text-amber-300">Agente pausado</p>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      <p className="max-w-[16rem] truncate" title={conversation.next_step}>
                        {conversation.next_step}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      <p className="max-w-[32rem] truncate" title={conversation.summary}>
                        {conversation.summary}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => void openConversation(conversation.id)}
                        className="rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:border-slate-500 hover:bg-slate-800"
                      >
                        Ver conversa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          !error && (
            <div className="p-6">
              <EmptyState
                title="Nenhuma conversa encontrada para o filtro atual."
                description="Abra o Agent Lab ou ajuste o filtro de agente para ver conversas existentes."
                actionLabel="Abrir Agent Lab"
                actionHref="/agent-lab"
              />
            </div>
          )
        )}

        {visibleConversations.length > 0 ? (
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-4">
            <p className="text-sm text-slate-500">
              Mostrando {(currentPage - 1) * pageSize + 1} a {Math.min(currentPage * pageSize, visibleConversations.length)} de{" "}
              {visibleConversations.length} leads
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={currentPage === 1}
                className="rounded-full border border-slate-700 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                disabled={currentPage === totalPages}
                className="rounded-full border border-slate-700 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Proxima
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {selectedConversationId ? (
        <>
          <button type="button" aria-label="Fechar painel" className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm" onClick={closeConversation} />
          <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l border-slate-800 bg-slate-900 shadow-[-24px_0_80px_rgba(2,6,23,0.55)]">
            <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-6 py-5">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Painel da conversa</p>
                <h2 className="mt-2 text-xl font-semibold text-slate-50">
                  {detail?.conversation.title || "Carregando conversa"}
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                  Canal {detail?.conversation.channel || "-"} •{" "}
                  {detail?.conversation.updated_at ? formatDateTimeSP(detail.conversation.updated_at) : "-"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={closeConversation}
                  className="rounded-full border border-slate-700 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:bg-slate-800"
                >
                  Fechar
                </button>
              </div>
            </div>

            <div className="grid gap-4 border-b border-slate-800 px-6 py-4 text-sm text-slate-400 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Data de entrada</p>
                <p className="mt-2 text-slate-200">
                  {detail?.conversation.started_at
                    ? formatDateTimeSP(detail.conversation.started_at)
                    : detail?.conversation.updated_at
                      ? formatDateTimeSP(detail.conversation.updated_at)
                      : "-"}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Status atual</p>
                <div className="mt-2">
                  <span
                    className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${
                      detailPipelineStatus ? statusTone(detailPipelineStatus) : "border-slate-700 text-slate-300"
                    }`}
                  >
                    {detailPipelineStatus ? statusLabel(detailPipelineStatus) : "-"}
                  </span>
                </div>
              </div>
            </div>

            <div className="border-b border-slate-800 px-6 py-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Acoes rapidas</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void applyQuickStatus("handoff")}
                  disabled={isUpdatingPipelineStatus}
                  className="rounded-full border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-100 transition hover:bg-amber-500/20"
                >
                  Marcar handoff
                </button>
                <button
                  type="button"
                  onClick={() => void applyQuickStatus("scheduled")}
                  disabled={isUpdatingPipelineStatus}
                  className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-emerald-200 transition hover:bg-emerald-500/20"
                >
                  Marcar agendado
                </button>
                <button
                  type="button"
                  onClick={() => void applyQuickStatus("disqualified")}
                  disabled={isUpdatingPipelineStatus}
                  className="rounded-full border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-rose-100 transition hover:bg-rose-500/20"
                >
                  Desqualificar
                </button>
                <button
                  type="button"
                  onClick={() => void applyQuickStatus("qualifying")}
                  disabled={isUpdatingPipelineStatus}
                  className="rounded-full border border-blue-400/30 bg-blue-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-blue-100 transition hover:bg-blue-500/20"
                >
                  Voltar para qualificacao
                </button>
              </div>
              {isUpdatingPipelineStatus ? <p className="mt-3 text-xs text-slate-500">Atualizando status da conversa...</p> : null}
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              {isLoadingDetail ? (
                <p className="text-sm text-slate-400">Carregando mensagens...</p>
              ) : detail ? (
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-slate-800 bg-slate-950 px-4 py-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Resumo do lead</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{decorateConversation(detail.conversation).summary}</p>
                  </div>
                  <div className="rounded-[24px] border border-slate-800 bg-slate-950 px-4 py-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Cadastro obrigatorio</p>
                    <div className="mt-2 space-y-2 text-sm text-slate-300">
                      <p>Nome: {detail.conversation.lead_name || "Nao capturado"}</p>
                      <p>Telefone: {detail.conversation.lead_phone || "Nao capturado"}</p>
                      <p>CPF: {detail.conversation.lead_cpf || "Nao capturado"}</p>
                      <p>
                        Pendencias:{" "}
                        {detail.conversation.lead_profile_missing_fields?.length
                          ? detail.conversation.lead_profile_missing_fields.map(leadFieldLabel).join(", ")
                          : "cadastro completo"}
                      </p>
                    </div>
                  </div>
                  <div className="rounded-[24px] border border-slate-800 bg-slate-950 px-4 py-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Responsavel atual</p>
                    <p className="mt-2 text-sm text-slate-300">
                      {agents.find((agent) => agent.id === detail.conversation.agent_id)?.name || "Nao atribuido"}
                    </p>
                    {detail.conversation.agent_paused ? (
                      <p className="mt-2 text-xs uppercase tracking-wide text-amber-300">
                        Agente pausado por handoff humano
                      </p>
                    ) : null}
                  </div>
                  {detail.messages.length > 0 ? (
                    detail.messages.map((message) => {
                      const isAssistant = message.sender_type === "assistant";
                      return (
                        <article
                          key={message.id}
                          className={`max-w-[85%] rounded-2xl border px-4 py-3 ${
                            isAssistant
                              ? "ml-auto border-[var(--accent)]/25 bg-[var(--accent)]/12 text-slate-50"
                              : "border-slate-800 bg-slate-950 text-slate-200"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <strong className="text-xs uppercase tracking-wide text-slate-400">
                              {isAssistant ? "Agente" : "Lead"}
                            </strong>
                            <span className="text-xs text-slate-500">{formatDateTimeSP(message.sent_at)}</span>
                          </div>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{message.content}</p>
                        </article>
                      );
                    })
                  ) : (
                  <p className="text-sm text-slate-400">Nenhuma mensagem registrada nesta conversa.</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-400">Nao foi possivel carregar o detalhe da conversa.</p>
              )}
            </div>
          </aside>
        </>
      ) : null}
    </main>
  );
}
