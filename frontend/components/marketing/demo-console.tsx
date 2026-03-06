"use client";

import { FormEvent, useMemo, useState } from "react";

type DemoMessage = {
  id: string;
  role: "lead" | "agent";
  content: string;
};

type DonePayload = {
  done?: boolean;
  conversation_id?: string;
  reply_fragments?: string[];
  follow_up_suggestion?: string | null;
  qualification_signals?: string[];
};

function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const starterPrompts = [
  "Tenho pouco orcamento. Como voce me ajudaria a vender sem forcar um plano ruim?",
  "Como a agente rebate a comparacao entre consorcio e financiamento?",
  "Se o lead perguntar de seminovo, como a conversa evolui?",
];

export function DemoConsole() {
  const [messages, setMessages] = useState<DemoMessage[]>([
    {
      id: createId(),
      role: "agent",
      content:
        "Eu sou a demo publica conectada ao backend real do produto. Me provoque com objecoes, qualificacao e cenarios de venda para eu mostrar memoria, proximo passo e handoff.",
    },
  ]);
  const [input, setInput] = useState(starterPrompts[0]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [followUpSuggestion, setFollowUpSuggestion] = useState<string | null>(null);
  const [qualificationSignals, setQualificationSignals] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const canSend = useMemo(() => input.trim().length > 0 && !isStreaming, [input, isStreaming]);

  async function sendMessage(messageText: string) {
    const text = messageText.trim();
    if (!text || isStreaming) {
      return;
    }

    setError(null);
    setIsStreaming(true);
    setInput("");
    setFollowUpSuggestion(null);
    setQualificationSignals([]);

    const userMessage: DemoMessage = { id: createId(), role: "lead", content: text };
    const assistantId = createId();
    setMessages((previous) => [...previous, userMessage, { id: assistantId, role: "agent", content: "" }]);

    try {
      const response = await fetch("/api/demo/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          message_text: text,
          conversation_id: conversationId,
          channel: "marketing-demo",
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Falha na demo: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

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

          const payload = JSON.parse(line) as { token?: string } & DonePayload;

          if (typeof payload.token === "string") {
            const token = payload.token;
            setMessages((previous) =>
              previous.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content ? `${message.content} ${token}` : token }
                  : message,
              ),
            );
          }

          if (payload.done) {
            setConversationId(payload.conversation_id || null);
            setFollowUpSuggestion(payload.follow_up_suggestion || null);
            setQualificationSignals(payload.qualification_signals || []);
          }
        }
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao executar demo.");
      setMessages((previous) =>
        previous.map((message) =>
          message.id === assistantId ? { ...message, content: "Falha ao executar a demonstracao publica." } : message,
        ),
      );
    } finally {
      setIsStreaming(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendMessage(input);
  }

  function resetConversation() {
    setConversationId(null);
    setFollowUpSuggestion(null);
    setQualificationSignals([]);
    setMessages([
      {
        id: createId(),
        role: "agent",
        content:
          "Conversa reiniciada. Traga um novo cenario comercial e eu abro outra sessao publica no backend para testar memoria e condução.",
      },
    ]);
    setInput(starterPrompts[0]);
    setError(null);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <section className="rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(8,14,27,0.92),rgba(12,18,32,0.94))] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] md:p-6">
        <div className="flex items-center justify-between gap-3 rounded-[20px] border border-white/10 bg-black/20 px-4 py-3 text-xs text-white/55">
          <span>Demo publica / backend real</span>
          <span>{isStreaming ? "ao vivo" : conversationId ? `sessao ${conversationId.slice(0, 8)}` : "pronta"}</span>
        </div>

        <div className="mt-4 min-h-[360px] space-y-4 rounded-[26px] border border-white/8 bg-[rgba(255,255,255,0.03)] p-4">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`max-w-[92%] rounded-[22px] border px-4 py-3 text-sm leading-7 ${
                message.role === "agent"
                  ? "border-[#7ad2ff]/18 bg-[linear-gradient(180deg,rgba(122,210,255,0.14),rgba(122,210,255,0.05))] text-white"
                  : "ml-auto border-white/10 bg-white/5 text-white/78"
              }`}
            >
              <p className="mb-2 text-[11px] uppercase tracking-[0.22em] text-white/38">
                {message.role === "agent" ? "agente" : "lead"}
              </p>
              <p>{message.content || "..."}</p>
            </article>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ex.: Como a agente conduz um lead com objecao de orcamento?"
            className="min-h-[120px] w-full rounded-[26px] border border-white/10 bg-black/25 px-4 py-4 text-sm text-white outline-none focus:border-[#7ad2ff]"
          />
          <div className="flex flex-wrap gap-2">
            {starterPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => void sendMessage(prompt)}
                disabled={isStreaming}
                className="rounded-full border border-white/10 px-3 py-2 text-xs text-white/70 transition hover:bg-white/5 disabled:opacity-60"
              >
                {prompt}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-white/45">Esta demo usa o backend publico do MVP, persiste a conversa e reaproveita a sessao para testar memoria.</p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={resetConversation}
                disabled={isStreaming}
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/75 transition hover:bg-white/5 disabled:opacity-60"
              >
                Nova sessao
              </button>
              <button
                type="submit"
                disabled={!canSend}
                className="rounded-full bg-[#ff875a] px-5 py-2.5 text-sm font-semibold text-black disabled:opacity-60"
              >
                {isStreaming ? "Transmitindo..." : "Rodar demo"}
              </button>
            </div>
          </div>
        </form>
      </section>

      <aside className="space-y-4">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <p className="text-[11px] uppercase tracking-[0.26em] text-[#7ad2ff]">Leitura comercial</p>
          <h3 className="mt-3 text-2xl font-semibold text-white">O que a demo mede</h3>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-white/70">
            <li>Diagnostico antes de oferta.</li>
            <li>Objecao respondida com processo, nao com empilhamento de texto.</li>
            <li>Resposta encerrando com proxima acao clara.</li>
            <li>Memoria reaproveitada entre mensagens da mesma sessao.</li>
          </ul>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,135,90,0.12),rgba(255,135,90,0.04))] p-5">
          <p className="text-[11px] uppercase tracking-[0.26em] text-[#ffb86a]">Sinais detectados</p>
          <div className="mt-4 space-y-3">
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <p className="text-[11px] uppercase tracking-wide text-white/35">Follow-up sugerido</p>
              <p className="mt-2 text-sm text-white/78">{followUpSuggestion || "Aguardando uma rodada de demo."}</p>
            </div>
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <p className="text-[11px] uppercase tracking-wide text-white/35">Qualificacao puxada</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {qualificationSignals.length > 0 ? (
                  qualificationSignals.map((item) => (
                    <span key={item} className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/78">
                      {item}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-white/55">Sem sinais ainda.</span>
                )}
              </div>
            </div>
          </div>
          {error ? <p className="mt-4 rounded-2xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
        </section>
      </aside>
    </div>
  );
}
