"use client";

import { FormEvent, useMemo, useState } from "react";

import { fetchJson } from "@/lib/api";

type MarketingLeadResponse = {
  lead_id: string;
  conversation_id: string;
  status: string;
  message: string;
};

type FormState = {
  name: string;
  email: string;
  company: string;
  message: string;
};

const initialState: FormState = {
  name: "",
  email: "",
  company: "",
  message: "Quero entender como a agente venderia meu produto e como voces operam o handoff comercial.",
};

export function LeadCaptureForm() {
  const [form, setForm] = useState<FormState>(initialState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isValid = useMemo(() => {
    return form.name.trim().length >= 2 && form.email.includes("@") && form.message.trim().length >= 8;
  }, [form]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetchJson<MarketingLeadResponse>("/api/marketing/leads", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          email: form.email.trim(),
          company: form.company.trim() || null,
          message: form.message.trim(),
        }),
      });
      setSuccess(`${response.message} Lead ${response.lead_id.slice(0, 8)} registrado para contato.`);
      setForm(initialState);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao capturar lead.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,24,44,0.96),rgba(8,11,19,0.96))] p-7 md:p-8">
      <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
        <div>
          <p className="text-[11px] uppercase tracking-[0.3em] text-[#7ad2ff]">Captura de demanda</p>
          <h2 className="mt-4 text-4xl font-semibold leading-tight text-white md:text-5xl">
            Traga um caso real e eu registro o contexto para a proxima acao comercial.
          </h2>
          <p className="mt-5 max-w-xl text-lg leading-8 text-white/68">
            Este formulario grava o lead no backend do MVP com tenant publico, conversa inicial e historico persistido. Serve para testar a esteira comercial de ponta a ponta.
          </p>
          <div className="mt-8 space-y-3 text-sm text-white/70">
            <div className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-3">Captura nome, empresa, e-mail e problema comercial.</div>
            <div className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-3">Abre conversa publica persistida para o time retomar depois.</div>
            <div className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-3">Mantem o funil da landing conectado ao mesmo backend do produto.</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="rounded-[32px] border border-white/10 bg-black/20 p-5 md:p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-white/70">
              <span>Nome</span>
              <input
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                className="w-full rounded-[18px] border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-[#7ad2ff]"
                placeholder="Seu nome"
              />
            </label>
            <label className="space-y-2 text-sm text-white/70">
              <span>E-mail</span>
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                className="w-full rounded-[18px] border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-[#7ad2ff]"
                placeholder="voce@empresa.com"
              />
            </label>
          </div>

          <label className="mt-4 block space-y-2 text-sm text-white/70">
            <span>Empresa</span>
            <input
              value={form.company}
              onChange={(event) => setForm((current) => ({ ...current, company: event.target.value }))}
              className="w-full rounded-[18px] border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-[#7ad2ff]"
              placeholder="Nome da empresa"
            />
          </label>

          <label className="mt-4 block space-y-2 text-sm text-white/70">
            <span>Cenario comercial</span>
            <textarea
              value={form.message}
              onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
              className="min-h-[160px] w-full rounded-[22px] border border-white/10 bg-white/5 px-4 py-4 text-white outline-none focus:border-[#7ad2ff]"
              placeholder="Descreva o produto, objecoes recorrentes, ciclo de venda ou canais que precisa terceirizar."
            />
          </label>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-lg text-xs leading-6 text-white/45">
              O objetivo aqui nao e mailing. E capturar um caso real para testar funil, handoff e contexto de conversa no mesmo backend do MVP.
            </p>
            <button
              type="submit"
              disabled={!isValid || isSubmitting}
              className="rounded-full bg-[#ff875a] px-5 py-3 text-sm font-semibold text-black transition hover:bg-[#ff9b75] disabled:opacity-60"
            >
              {isSubmitting ? "Registrando..." : "Quero uma avaliacao consultiva"}
            </button>
          </div>

          {success ? <p className="mt-4 rounded-2xl border border-emerald-400/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{success}</p> : null}
          {error ? <p className="mt-4 rounded-2xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
        </form>
      </div>
    </section>
  );
}
