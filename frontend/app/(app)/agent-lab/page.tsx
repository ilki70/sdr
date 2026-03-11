"use client";

import { FormEvent, startTransition, useEffect, useState } from "react";
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

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sentAt?: string;
};

type AgentRuntimeState = {
  intent: string | null;
  replyFragments: string[];
  followUpSuggestion: string | null;
};

type AgentOption = {
  id: string;
  name: string;
  slug: string;
  active_version_no: number | null;
};

function createId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function mapMessages(messages: ConversationMessage[]): ChatMessage[] {
  return messages.map((message) => ({
    id: message.id,
    role: message.sender_type === "assistant" ? "assistant" : "user",
    content: message.content,
    sentAt: message.sent_at,
  }));
}

function extractRuntime(messages: ConversationMessage[]): AgentRuntimeState {
  const lastAssistant = [...messages].reverse().find((message) => message.sender_type === "assistant");
  return {
    intent: typeof lastAssistant?.metadata_json?.intent === "string" ? lastAssistant.metadata_json.intent : null,
    replyFragments: Array.isArray(lastAssistant?.metadata_json?.reply_fragments)
      ? (lastAssistant?.metadata_json?.reply_fragments as string[])
      : [],
    followUpSuggestion:
      typeof lastAssistant?.metadata_json?.follow_up_suggestion === "string"
        ? lastAssistant.metadata_json.follow_up_suggestion
        : null,
  };
}

export default function AgentLabPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [agentRuntime, setAgentRuntime] = useState<AgentRuntimeState>({
    intent: null,
    replyFragments: [],
    followUpSuggestion: null,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsBootstrapping(true);
      setError(null);
      try {
        const [items, agentItems] = await Promise.all([
          fetchJson<ConversationSummary[]>("/api/proxy/messages/conversations"),
          fetchJson<AgentOption[]>("/api/proxy/agents"),
        ]);
        if (cancelled) {
          return;
        }
        setConversations(items);
        setAgents(agentItems);
        setSelectedAgentId((current) => current || agentItems[0]?.id || null);
        if (items.length > 0) {
          await openConversation(items[0].id, { silent: true });
          return;
        }
        const created = await createConversation({ silent: true });
        if (!cancelled && created) {
          await openConversation(created.id, { silent: true });
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao iniciar Agent Lab.");
        }
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshConversations() {
    const items = await fetchJson<ConversationSummary[]>("/api/proxy/messages/conversations");
    startTransition(() => {
      setConversations(items);
    });
    return items;
  }

  async function createConversation(options?: { silent?: boolean }) {
    setError(null);
    if (!options?.silent) {
      setIsCreatingConversation(true);
    }
    try {
      const created = await fetchJson<ConversationSummary>("/api/proxy/messages/conversations", {
        method: "POST",
        body: JSON.stringify({ channel: "lab", agent_id: selectedAgentId }),
      });
      const items = await refreshConversations();
      const selected = items.find((item) => item.id === created.id) || created;
      setActiveConversationId(selected.id);
      setSelectedAgentId(selected.agent_id || selectedAgentId);
      setMessages([]);
      setAgentRuntime({ intent: null, replyFragments: [], followUpSuggestion: null });
      return selected;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar nova sessao.");
      return null;
    } finally {
      if (!options?.silent) {
        setIsCreatingConversation(false);
      }
    }
  }

  async function openConversation(conversationId: string, options?: { silent?: boolean }) {
    setError(null);
    if (!options?.silent) {
      setIsLoadingConversation(true);
    }
    try {
      const detail = await fetchJson<ConversationDetail>(`/api/proxy/messages/conversations/${conversationId}`);
      startTransition(() => {
        setActiveConversationId(detail.conversation.id);
        setSelectedAgentId(detail.conversation.agent_id || selectedAgentId);
        setMessages(mapMessages(detail.messages));
        setAgentRuntime(extractRuntime(detail.messages));
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao abrir conversa.");
    } finally {
      if (!options?.silent) {
        setIsLoadingConversation(false);
      }
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isSending) {
      return;
    }

    let conversationId = activeConversationId;
    if (!conversationId) {
      const created = await createConversation();
      if (!created) {
        return;
      }
      conversationId = created.id;
    }

    setInput("");
    setIsSending(true);
    setError(null);
    setAgentRuntime({ intent: null, replyFragments: [], followUpSuggestion: null });

    const userMessage: ChatMessage = { id: createId(), role: "user", content: text };
    const assistantId = createId();
    setMessages((previous) => [...previous, userMessage, { id: assistantId, role: "assistant", content: "" }]);

    try {
      const response = await fetch("/api/proxy/messages/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ message_text: text, channel: "lab", conversation_id: conversationId, agent_id: selectedAgentId }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Falha na stream: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let nextConversationId = conversationId;

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventChunk of events) {
          const line = eventChunk
            .split("\n")
            .find((item) => item.startsWith("data: "))
            ?.slice(6);

          if (!line) {
            continue;
          }

          try {
            const payload = JSON.parse(line) as {
              token?: string;
              done?: boolean;
              intent?: string;
              conversation_id?: string;
              reply_fragments?: string[];
              follow_up_suggestion?: string | null;
            };
            const token = payload.token;
            if (token) {
              setMessages((previous) =>
                previous.map((message) =>
                  message.id === assistantId
                    ? { ...message, content: message.content ? `${message.content} ${token}` : token }
                    : message,
                ),
              );
            }
            if (payload.conversation_id) {
              nextConversationId = payload.conversation_id;
            }
            if (payload.done && payload.intent) {
              setAgentRuntime({
                intent: payload.intent,
                replyFragments: payload.reply_fragments || [],
                followUpSuggestion: payload.follow_up_suggestion || null,
              });
              setMessages((previous) =>
                previous.map((message) =>
                  message.id === assistantId
                    ? { ...message, content: `${message.content}\n\n[intent detectado: ${payload.intent}]` }
                    : message,
                ),
              );
            }
          } catch {
            setMessages((previous) =>
              previous.map((message) =>
                message.id === assistantId ? { ...message, content: `${message.content}\n[erro ao parsear evento]` } : message,
              ),
            );
          }
        }
      }

      const items = await refreshConversations();
      const selected = items.find((item) => item.id === nextConversationId);
      if (selected) {
        setActiveConversationId(selected.id);
      }
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "erro desconhecido";
      setMessages((previous) =>
        previous.map((message) =>
          message.id === assistantId ? { ...message, content: `Falha ao consultar agente: ${detail}` } : message,
        ),
      );
      setError(detail);
    } finally {
      setIsSending(false);
    }
  }

  const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId) || null;
  const activeAgent = agents.find((agent) => agent.id === selectedAgentId) || null;

  return (
    <main className="grid gap-5 xl:grid-cols-[320px_1fr]">
      <aside className="overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))]">
        <div className="border-b border-white/10 px-5 py-5">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Agent Lab</p>
          <div className="mt-3 flex items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold">Memoria de Conversas</h1>
              <p className="text-sm text-white/65">Retome sessoes anteriores e compare a evolucao do agente.</p>
            </div>
            <button
              type="button"
              onClick={() => void createConversation()}
              disabled={isCreatingConversation}
              className="rounded-full border border-[var(--accent)]/40 bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
            >
              {isCreatingConversation ? "Criando..." : "Nova sessao"}
            </button>
          </div>
        </div>

        <div className="max-h-[70vh] space-y-3 overflow-y-auto px-3 py-4">
          {conversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId;
            return (
              <button
                key={conversation.id}
                type="button"
                onClick={() => void openConversation(conversation.id)}
                className={`block w-full rounded-2xl border px-4 py-4 text-left transition ${
                  isActive
                    ? "border-[var(--accent)]/60 bg-[var(--accent)]/12"
                    : "border-white/10 bg-black/20 hover:border-white/20 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <strong className="line-clamp-1 text-sm">{conversation.title}</strong>
                  <span className="rounded-full border border-white/10 px-2 py-1 text-[10px] uppercase tracking-wide text-white/60">
                    {conversation.message_count} msgs
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-white/65">
                  {conversation.last_message_preview || "Sessao criada. Envie a primeira mensagem."}
                </p>
                <p className="mt-3 text-[11px] uppercase tracking-wide text-white/40">
                  Atualizado em {formatDateTimeSP(conversation.updated_at)}
                </p>
              </button>
            );
          })}

          {!isBootstrapping && conversations.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/15 px-4 py-6 text-sm text-white/60">
              Nenhuma sessao encontrada.
            </div>
          ) : null}
        </div>
      </aside>

      <section className="overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(244,211,94,0.12),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))]">
        <header className="border-b border-white/10 px-6 py-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Sessao ativa</p>
              <h2 className="mt-2 text-2xl font-semibold">
                {activeConversation ? activeConversation.title : "Preparando ambiente"}
              </h2>
              <p className="mt-1 text-sm text-white/65">
                {activeConversation
                  ? `${activeConversation.message_count} mensagens registradas`
                  : "Criando ou carregando uma conversa para teste"}
              </p>
            </div>
            <div className="rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs uppercase tracking-wide text-white/55">
              {activeConversation ? `Canal ${activeConversation.channel}` : "Aguardando"}
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
            <label className="block">
              <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-white/45">Agente em teste</span>
              <select
                value={selectedAgentId || ""}
                onChange={(event) => setSelectedAgentId(event.target.value || null)}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
              >
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name} {agent.active_version_no ? `(v${agent.active_version_no})` : ""}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Rota atual</p>
              <p className="mt-2 text-sm text-white/75">{activeAgent ? `${activeAgent.name} • ${activeAgent.slug}` : "Nenhum agente selecionado"}</p>
            </div>
          </div>
          {error ? <p className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
        </header>

        <div className="grid gap-0 lg:grid-cols-[1fr_280px]">
          <div className="border-b border-white/10 px-6 py-5 lg:border-b-0 lg:border-r">
            <div className="mb-4 max-h-[58vh] min-h-[420px] space-y-4 overflow-y-auto pr-2">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={`max-w-[85%] rounded-3xl border px-4 py-3 text-sm whitespace-pre-wrap ${
                    message.role === "user"
                      ? "ml-auto border-[var(--accent)]/30 bg-[var(--accent)]/14"
                      : "border-white/10 bg-black/25"
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between gap-4 text-[11px] uppercase tracking-wide text-white/45">
                    <span>{message.role === "user" ? "Lead" : "Agente"}</span>
                    {message.sentAt ? <span>{formatDateTimeSP(message.sentAt)}</span> : null}
                  </div>
                  <p>{message.content || "..."}</p>
                </article>
              ))}

              {!isBootstrapping && !isLoadingConversation && messages.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-white/15 bg-black/20 px-5 py-8 text-sm text-white/55">
                  Sessao pronta. Envie a primeira mensagem para comecar a validar memoria e continuidade.
                </div>
              ) : null}

              {isLoadingConversation ? (
                <div className="rounded-3xl border border-white/10 bg-black/20 px-5 py-6 text-sm text-white/60">
                  Carregando historico...
                </div>
              ) : null}
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <textarea
                className="min-h-[110px] w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-sm outline-none focus:border-[var(--accent)]"
                placeholder="Ex.: Tenho interesse em consorcio, mas preciso de uma parcela que caiba na minha renda."
                value={input}
                onChange={(event) => setInput(event.target.value)}
              />
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs text-white/50">
                  Cada envio grava a mensagem no MySQL e reutiliza o historico recente no prompt do agente.
                </p>
                <button
                  type="submit"
                  disabled={isSending || input.trim().length === 0 || isLoadingConversation || !selectedAgentId}
                  className="rounded-full bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSending ? "Enviando..." : activeAgent ? `Enviar para ${activeAgent.name}` : "Enviar"}
                </button>
              </div>
            </form>
          </div>

          <aside className="space-y-4 px-6 py-5 text-sm">
            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Teste realista</p>
              <ul className="mt-3 space-y-2 text-white/75">
                <li>Historico persistido por tenant e sessao.</li>
                <li>Reabertura de conversa com contexto recuperado.</li>
                <li>Multiplas sessoes de teste no mesmo ambiente.</li>
                <li>Streaming SSE sobre resposta ja gravada no backend.</li>
                <li>Fragmentacao e follow-up sugeridos pela persona ativa.</li>
              </ul>
            </div>

            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Sessao</p>
              <dl className="mt-3 space-y-3 text-white/70">
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-white/40">Conversation ID</dt>
                  <dd className="mt-1 break-all text-xs">{activeConversationId || "-"}</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-white/40">Ultima atualizacao</dt>
                  <dd className="mt-1 text-xs">{activeConversation ? formatDateTimeSP(activeConversation.updated_at) : "-"}</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-white/40">Agente vinculado</dt>
                  <dd className="mt-1 text-xs">
                    {agents.find((agent) => agent.id === activeConversation?.agent_id)?.name || activeAgent?.name || "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-white/40">Intent mais recente</dt>
                  <dd className="mt-1 text-xs">{agentRuntime.intent || "-"}</dd>
                </div>
              </dl>
            </div>

            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Entrega da persona</p>
              <div className="mt-3 space-y-3">
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-white/40">Mensagens fragmentadas</p>
                  <ul className="mt-2 space-y-2 text-xs text-white/70">
                    {agentRuntime.replyFragments.length > 0 ? (
                      agentRuntime.replyFragments.map((fragment, index) => <li key={`${index}-${fragment}`}>{fragment}</li>)
                    ) : (
                      <li>Nenhuma fragmentacao registrada ainda.</li>
                    )}
                  </ul>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-white/40">Follow-up sugerido</p>
                  <p className="mt-2 text-xs text-white/70">{agentRuntime.followUpSuggestion || "-"}</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
