"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import { EmptyState } from "@/components/shared/empty-state";

type Conversation = {
  id: string;
  agent_id: string | null;
  title: string;
  channel: string;
  status: string;
  message_count: number;
  updated_at: string;
  last_message_preview: string | null;
};

type AgentOption = {
  id: string;
  name: string;
  slug: string;
};

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      fetchJson<Conversation[]>("/api/proxy/messages/conversations"),
      fetchJson<AgentOption[]>("/api/proxy/agents"),
    ])
      .then(([conversationItems, agentItems]) => {
        setConversations(conversationItems);
        setAgents(agentItems);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar conversas."));
  }, []);

  const visibleConversations =
    selectedAgentId === "all"
      ? conversations
      : conversations.filter((conversation) => conversation.agent_id === selectedAgentId);

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Conversas</h1>
            <p className="mt-2 text-sm text-white/70">Inbox minima por agente, usando bindings de integracao e sessoes de laboratorio.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedAgentId}
              onChange={(event) => setSelectedAgentId(event.target.value)}
              className="rounded-full border border-white/15 bg-black/20 px-4 py-2 text-sm outline-none"
            >
              <option value="all">Todos os agentes</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
            <Link href="/agent-lab" className="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black">
              Abrir Agent Lab
            </Link>
          </div>
        </div>
      </section>
      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      <div className="space-y-3">
        {visibleConversations.map((conversation) => (
          <article key={conversation.id} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
            <div className="flex items-center justify-between gap-3">
              <strong>{conversation.title}</strong>
              <span className="text-xs uppercase tracking-wide text-white/50">{conversation.channel}</span>
            </div>
            <p className="mt-2 text-sm text-white/70">{conversation.last_message_preview || "Sem mensagens."}</p>
            <p className="mt-3 text-xs text-white/45">
              Agente: {agents.find((agent) => agent.id === conversation.agent_id)?.name || "nao atribuido"}
            </p>
            <p className="mt-3 text-xs text-white/40">{conversation.message_count} mensagens • {formatDateTimeSP(conversation.updated_at)}</p>
          </article>
        ))}
        {!error && visibleConversations.length === 0 ? (
          <EmptyState
            title="Nenhuma conversa encontrada para o filtro atual."
            description="Abra o Agent Lab ou ajuste o filtro de agente para ver conversas existentes."
            actionLabel="Abrir Agent Lab"
            actionHref="/agent-lab"
          />
        ) : null}
      </div>
    </main>
  );
}
