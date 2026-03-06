"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const form = new FormData(event.currentTarget);
    const payload = {
      fullName: String(form.get("fullName") || ""),
      email: String(form.get("email") || ""),
      password: String(form.get("password") || ""),
      tenantId: String(form.get("tenantId") || ""),
      role: String(form.get("role") || "operator"),
    };

    const response = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    setIsSubmitting(false);
    if (!response.ok) {
      const detail = await response.text();
      setError(detail || "Falha ao registrar.");
      return;
    }
    router.push("/login");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-xl border border-white/15 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold">Criar Conta de Teste</h1>
        <p className="mt-2 text-sm text-white/70">Use tenant slug (ex.: tenant-lab).</p>

        <label className="mt-6 block text-sm">Nome completo</label>
        <input
          name="fullName"
          required
          className="mt-2 w-full rounded-md border border-white/20 bg-black/20 px-3 py-2"
        />

        <label className="mt-4 block text-sm">Email</label>
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

        <label className="mt-4 block text-sm">Tenant (slug ou id)</label>
        <input
          name="tenantId"
          required
          defaultValue="tenant-lab"
          className="mt-2 w-full rounded-md border border-white/20 bg-black/20 px-3 py-2"
        />

        <label className="mt-4 block text-sm">Role</label>
        <select name="role" className="mt-2 w-full rounded-md border border-white/20 bg-black/20 px-3 py-2">
          <option value="owner">owner</option>
          <option value="admin">admin</option>
          <option value="operator">operator</option>
          <option value="viewer">viewer</option>
        </select>

        {error ? <p className="mt-4 text-sm text-red-400">{error}</p> : null}

        <button
          disabled={isSubmitting}
          className="mt-6 w-full rounded-md bg-[var(--accent)] px-4 py-2 font-semibold text-black disabled:opacity-70"
          type="submit"
        >
          {isSubmitting ? "Criando..." : "Criar conta"}
        </button>

        <p className="mt-4 text-sm text-white/70">
          Ja tem conta?{" "}
          <Link href="/login" className="underline">
            Ir para login
          </Link>
        </p>
      </form>
    </main>
  );
}
