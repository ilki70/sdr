import Link from "next/link";
import { BRAND_NAME } from "@/lib/brand";

const highlights = [
  {
    title: "Atendimento mais rapido",
    text: "Organize fluxos de vendas, suporte e pos-venda com agentes preparados para responder com clareza e consistencia.",
  },
  {
    title: "Mais controle da operacao",
    text: "Centralize canais, conversas, acompanhamento e qualidade em uma unica plataforma de operacao conversacional.",
  },
  {
    title: "Escala com padrao",
    text: "Crie atendentes para jornadas diferentes sem perder identidade, contexto e governanca.",
  },
];

const capabilities = [
  {
    eyebrow: "Agentes",
    title: "Crie atendentes para cada jornada",
    text: "Monte agentes para pre-venda, qualificacao, atendimento, recuperacao e pos-venda com configuracao propria.",
  },
  {
    eyebrow: "Canais",
    title: "Comece no WhatsApp e expanda depois",
    text: "Suba a operacao no canal de maior tracao agora e mantenha a base pronta para novas integracoes.",
  },
  {
    eyebrow: "Operacao",
    title: "Acompanhe tudo em um so lugar",
    text: "Converse, monitore, revise respostas e acompanhe o desempenho da operacao sem depender de ferramentas soltas.",
  },
  {
    eyebrow: "Qualidade",
    title: "Melhore continuamente",
    text: "Ajuste agentes, refine conhecimento e evolua a experiencia com base em revisoes e resultados reais.",
  },
];

const outcomes = [
  "Mais velocidade no primeiro atendimento",
  "Padrao de resposta entre equipes e jornadas",
  "Maior capacidade de operacao sem crescer no mesmo ritmo da equipe",
  "Base pronta para vendas, atendimento e relacionamento",
];

export default function MarketingPage() {
  return (
    <main className="overflow-hidden">
      <section className="relative border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(25,195,125,0.18),transparent_28%),radial-gradient(circle_at_82%_18%,rgba(245,158,11,0.12),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0))]" />
        <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-center px-6 py-20">
          <div className="max-w-4xl">
            <p className="inline-flex rounded-full border border-white/15 bg-white/5 px-4 py-1 text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">
              {BRAND_NAME}
            </p>
            <h1 className="mt-8 max-w-5xl text-5xl font-semibold leading-[0.95] tracking-[-0.04em] md:text-7xl">
              Atendentes com IA para vender, atender e acompanhar clientes em escala.
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-white/72 md:text-xl">
              Estruture uma operacao conversacional moderna com agentes especializados, canais integrados,
              acompanhamento centralizado e melhoria continua.
            </p>
          </div>

          <div className="mt-10 flex flex-wrap gap-3">
            <Link
              href="/register"
              className="rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-black transition hover:opacity-90"
            >
              Criar conta
            </Link>
            <Link
              href="/demo"
              className="rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Ver demonstracao
            </Link>
          </div>

          <div className="mt-16 grid gap-4 lg:grid-cols-3">
            {highlights.map((item) => (
              <article key={item.title} className="rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur">
                <h2 className="text-2xl font-semibold">{item.title}</h2>
                <p className="mt-3 text-sm leading-7 text-white/68">{item.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-6 py-20">
        <div className="max-w-3xl">
          <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">Como funciona</p>
          <h2 className="mt-4 text-4xl font-semibold tracking-[-0.03em]">Uma plataforma para a sua operacao, nao apenas um bot.</h2>
          <p className="mt-4 text-base leading-8 text-white/68">
            O produto foi pensado para empresas que precisam escalar conversas com mais velocidade, mais padrao e mais visibilidade
            sobre o que acontece em cada jornada.
          </p>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-2">
          {capabilities.map((item) => (
            <article key={item.title} className="rounded-[28px] border border-white/10 bg-black/20 p-6">
              <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">{item.eyebrow}</p>
              <h3 className="mt-4 text-2xl font-semibold leading-tight">{item.title}</h3>
              <p className="mt-3 text-sm leading-7 text-white/68">{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-white/10 bg-black/15">
        <div className="mx-auto grid w-full max-w-7xl gap-8 px-6 py-20 lg:grid-cols-[1fr_0.9fr]">
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">Resultados</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-[-0.03em]">Feito para transformar atendimento em vantagem operacional.</h2>
            <p className="mt-4 max-w-2xl text-base leading-8 text-white/68">
              A proposta aqui e simples: reduzir friccao no atendimento, aumentar a capacidade da operacao e criar uma base consistente
              para crescer com qualidade.
            </p>
          </div>

          <div className="rounded-[32px] border border-white/10 bg-white/5 p-6">
            <ul className="space-y-3 text-sm leading-7 text-white/70">
              {outcomes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-6 py-20">
        <div className="rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(25,195,125,0.12),transparent_30%),black] p-8 md:p-10">
          <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">CTA</p>
          <h2 className="mt-4 max-w-3xl text-4xl font-semibold tracking-[-0.04em] md:text-5xl">
            Estruture sua operacao conversacional com IA e prepare seu time para crescer com mais controle.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-8 text-white/70">
            Comece com uma base comercial forte, conecte seus canais e evolua a experiencia do cliente com uma plataforma pensada para operacao real.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/register"
              className="rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-black transition hover:opacity-90"
            >
              Comecar agora
            </Link>
            <Link
              href="/login"
              className="rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Entrar
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
