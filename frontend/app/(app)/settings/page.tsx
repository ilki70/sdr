"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { SAO_PAULO_TIMEZONE } from "@/lib/datetime";

type SessionPayload = {
  authenticated: boolean;
  userId: string;
  tenantId: string;
  email: string;
  role: string;
  fullName: string;
};

export default function SettingsPage() {
  const [session, setSession] = useState<SessionPayload | null>(null);

  useEffect(() => {
    void fetchJson<SessionPayload>("/api/auth/session").then(setSession).catch(() => null);
  }, []);

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-2 text-sm text-white/70">Configuração operacional inicial do ambiente logado.</p>
      </section>
      <section className="grid gap-5 xl:grid-cols-2">
        <article className="rounded-[28px] border border-white/10 bg-black/20 p-6">
          <h2 className="text-xl font-semibold">Sessão</h2>
          <dl className="mt-4 space-y-3 text-sm text-white/70">
            <div><dt className="text-white/45">Usuário</dt><dd>{session?.fullName || "-"}</dd></div>
            <div><dt className="text-white/45">Email</dt><dd>{session?.email || "-"}</dd></div>
            <div><dt className="text-white/45">Tenant</dt><dd>{session?.tenantId || "-"}</dd></div>
            <div><dt className="text-white/45">Role</dt><dd>{session?.role || "-"}</dd></div>
          </dl>
        </article>
        <article className="rounded-[28px] border border-white/10 bg-black/20 p-6">
          <h2 className="text-xl font-semibold">Regionalização</h2>
          <dl className="mt-4 space-y-3 text-sm text-white/70">
            <div><dt className="text-white/45">Timezone padrão</dt><dd>{SAO_PAULO_TIMEZONE}</dd></div>
            <div><dt className="text-white/45">Locale</dt><dd>pt-BR</dd></div>
            <div><dt className="text-white/45">Status</dt><dd>Datas da UI renderizadas em horário de São Paulo.</dd></div>
          </dl>
        </article>
      </section>
    </main>
  );
}
