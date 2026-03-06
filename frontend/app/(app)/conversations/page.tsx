"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type Conversation = {
  id: string;
  title: string;
  channel: string;
  status: string;
  message_count: number;
  updated_at: string;
  last_message_preview: string | null;
};

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchJson<Conversation[]>("/api/proxy/messages/conversations")
      .then(setConversations)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Falha ao carregar conversas."));
  }, []);

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Conversas</h1>
            <p className="mt-2 text-sm text-white/70">Histórico consolidado das sessões de laboratório.</p>
          </div>
          <Link href="/agent-lab" className="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black">
            Abrir Agent Lab
          </Link>
        </div>
      </section>
      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      <div className="space-y-3">
        {conversations.map((conversation) => (
          <article key={conversation.id} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
            <div className="flex items-center justify-between gap-3">
              <strong>{conversation.title}</strong>
              <span className="text-xs uppercase tracking-wide text-white/50">{conversation.channel}</span>
            </div>
            <p className="mt-2 text-sm text-white/70">{conversation.last_message_preview || "Sem mensagens."}</p>
            <p className="mt-3 text-xs text-white/40">{conversation.message_count} mensagens • {formatDateTimeSP(conversation.updated_at)}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
