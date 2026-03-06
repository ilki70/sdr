import Link from "next/link";

export default function MarketingPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-6 py-16">
      <p className="mb-4 inline-flex w-fit rounded-full border border-white/20 px-3 py-1 text-xs">
        Sales Command Center
      </p>
      <h1 className="max-w-3xl text-4xl font-semibold leading-tight md:text-6xl">
        Terceirize seu time de vendas com agentes de IA especialistas.
      </h1>
      <p className="mt-6 max-w-2xl text-base text-white/80 md:text-lg">
        Defina produtos, publique persona comercial e opere canais via Chatwoot com metricas e comissao configuravel.
      </p>
      <div className="mt-10 flex gap-3">
        <Link
          href="/login"
          className="rounded-md bg-[var(--accent)] px-5 py-3 font-medium text-black transition hover:opacity-90"
        >
          Entrar
        </Link>
        <Link href="/demo" className="rounded-md border border-white/20 px-5 py-3 font-medium hover:bg-white/5">
          Ver demo
        </Link>
      </div>
    </main>
  );
}
