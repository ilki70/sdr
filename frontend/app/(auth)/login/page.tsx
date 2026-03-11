"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BRAND_NAME } from "@/lib/brand";

type LoginError = string | null;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<LoginError>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const payload = {
      email: String(formData.get("email") || ""),
      password: String(formData.get("password") || ""),
      tenantId: String(formData.get("tenantId") || ""),
    };

    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    setIsSubmitting(false);
    if (!response.ok) {
      let detail = "Credenciais invalidas ou tenant sem acesso.";
      try {
        const payload = (await response.json()) as { message?: string };
        if (payload.message) {
          detail = payload.message;
        }
      } catch {
        detail = "Falha no login.";
      }
      setError(detail);
      return;
    }
    router.push("/dashboard");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-xl border border-white/15 bg-white/5 p-6">
        <p className="text-xs uppercase tracking-[0.24em] text-[var(--accent)]">{BRAND_NAME}</p>
        <h1 className="text-2xl font-semibold">Entrar</h1>
        <p className="mt-2 text-sm text-white/70">Acesse sua operacao conversacional.</p>

        <label className="mt-6 block text-sm">Email</label>
        <input
          name="email"
          type="email"
          required
          className="mt-2 w-full rounded-md border border-white/20 bg-black/20 px-3 py-2"
        />

        <label className="mt-4 block text-sm">Senha</label>
        <input
          name="password"
          type="password"
          minLength={8}
          required
          className="mt-2 w-full rounded-md border border-white/20 bg-black/20 px-3 py-2"
        />

        <label className="mt-4 block text-sm">Tenant ID</label>
        <input
          name="tenantId"
          required
          className="mt-2 w-full rounded-md border border-white/20 bg-black/20 px-3 py-2"
        />

        {error ? <p className="mt-4 text-sm text-red-400">{error}</p> : null}

        <button
          disabled={isSubmitting}
          className="mt-6 w-full rounded-md bg-[var(--accent)] px-4 py-2 font-semibold text-black disabled:opacity-70"
          type="submit"
        >
          {isSubmitting ? "Entrando..." : "Entrar"}
        </button>

        <p className="mt-4 text-sm text-white/70">
          Primeiro acesso?{" "}
          <Link href="/register" className="underline">
            Criar conta de teste
          </Link>
        </p>
      </form>
    </main>
  );
}
