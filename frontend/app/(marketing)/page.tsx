import Link from "next/link";

const pillars = [
  {
    title: "Operacao conversacional",
    text: "Centralize agentes, inbox, canais e handoff humano em uma unica camada operacional.",
  },
  {
    title: "Conversao e produtividade",
    text: "Distribua atendimentos por agente, acelere respostas e monitore a execucao de cada jornada comercial.",
  },
  {
    title: "Qualidade e melhoria continua",
    text: "Avalie conversas, acompanhe achados e refine o agente com versoes, conhecimento e politicas.",
  },
];

const modules = [
  {
    eyebrow: "Studio",
    title: "Crie varios atendentes no mesmo tenant",
    text: "Publique agentes com prompt proprio, historico de versoes, bindings de canal e testes guiados no Agent Lab.",
  },
  {
    eyebrow: "Inbox",
    title: "Enxergue a operacao por agente",
    text: "Filtre conversas, acompanhe sessoes abertas e opere o fluxo inicial de roteamento por inbox e integracao.",
  },
  {
    eyebrow: "Analytics",
    title: "Meça volume, atividade e bindings",
    text: "Dashboard com metricas por agente, conversas abertas, atividade recente e sinais de maturidade operacional.",
  },
  {
    eyebrow: "Quality",
    title: "Revise qualidade sem depender de amostragem manual",
    text: "Monitoria heuristica com score, achados e rastreio do uso de contexto oficial ou fallback de modelo.",
  },
];

const useCases = [
  "Pre-venda e SDR com varios agentes especializados",
  "Pos-venda e acompanhamento com playbooks separados",
  "Operacao inicial via WhatsApp, pronta para Chatwoot depois",
  "Jornadas diferentes por segmento, cliente ou produto",
];

const roadmap = [
  "Agentes com versao publicada e runtime por agent_id",
  "Bindings de canal por agente para roteamento inicial",
  "Inbox e analytics por agente no mesmo produto",
  "Monitoria de qualidade integrada ao fluxo de simulacao",
];

export default function MarketingPage() {
  return (
    <main className="overflow-hidden">
      <section className="relative border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(25,195,125,0.18),transparent_26%),radial-gradient(circle_at_80%_20%,rgba(245,158,11,0.14),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0))]" />
        <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-center px-6 py-20">
          <div className="max-w-4xl">
            <p className="inline-flex rounded-full border border-white/15 bg-white/5 px-4 py-1 text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">
              Conversation Ops Platform
            </p>
            <h1 className="mt-8 max-w-5xl text-5xl font-semibold leading-[0.95] tracking-[-0.04em] md:text-7xl">
              Agentes de IA para vendas, atendimento e pos-venda em uma plataforma operacional.
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-white/72 md:text-xl">
              O `sdr` saiu do modelo de um unico atendente e virou uma base multiagente: Studio, Inbox, Analytics e Quality
              no mesmo produto, com WhatsApp como MVP e arquitetura pronta para Chatwoot.
            </p>
          </div>

          <div className="mt-10 flex flex-wrap gap-3">
            <Link
              href="/register"
              className="rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-black transition hover:opacity-90"
            >
              Criar ambiente de teste
            </Link>
            <Link
              href="/login"
              className="rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Entrar na plataforma
            </Link>
          </div>

          <div className="mt-16 grid gap-4 lg:grid-cols-3">
            {pillars.map((pillar) => (
              <article key={pillar.title} className="rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur">
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/40">Pilar</p>
                <h2 className="mt-4 text-2xl font-semibold">{pillar.title}</h2>
                <p className="mt-3 text-sm leading-7 text-white/68">{pillar.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-6 py-20">
        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">Alinhamento</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-[-0.03em]">O que construimos ate agora</h2>
            <p className="mt-4 max-w-xl text-base leading-8 text-white/68">
              O escopo original era evoluir o caso Vinac para um produto com varios atendentes configuraveis. Isso ja esta refletido no core:
              conversas, integracoes, simulacao, dashboard e monitoria agora operam por agente.
            </p>
            <div className="mt-8 rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.03))] p-6">
              <p className="text-sm font-semibold text-white">Estado atual do produto</p>
              <ul className="mt-4 space-y-3 text-sm leading-7 text-white/70">
                {roadmap.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {modules.map((module) => (
              <article key={module.title} className="rounded-[28px] border border-white/10 bg-black/20 p-6">
                <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">{module.eyebrow}</p>
                <h3 className="mt-4 text-2xl font-semibold leading-tight">{module.title}</h3>
                <p className="mt-3 text-sm leading-7 text-white/68">{module.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-white/10 bg-black/15">
        <div className="mx-auto grid w-full max-w-7xl gap-6 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">Mercado</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-[-0.03em]">Posicionamento certo: plataforma, nao bot isolado</h2>
            <p className="mt-4 max-w-2xl text-base leading-8 text-white/68">
              Players fortes de mercado convergem em alguns pontos: inbox unificado, agentes com IA, copilot, analytics, integracoes e
              qualidade operacional. O diferencial que mais importa agora para o `sdr` e empacotar isso numa oferta clara por modulo e por
              jornada.
            </p>
          </div>

          <div className="rounded-[32px] border border-white/10 bg-white/5 p-6">
            <p className="text-sm font-semibold text-white">Direcao recomendada</p>
            <ul className="mt-4 space-y-3 text-sm leading-7 text-white/70">
              <li>WhatsApp como MVP, mas canais tratados como adapters.</li>
              <li>Agente como entidade central do produto, nao do cliente Vinac.</li>
              <li>Studio + Inbox + Analytics + Quality como narrativa comercial principal.</li>
              <li>Templates por vertical, em vez de hardcode por caso de uso.</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-6 py-20">
        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-[32px] border border-white/10 bg-white/5 p-6">
            <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">Casos de uso</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.03em]">Projetado para varias operacoes no mesmo tenant</h2>
            <div className="mt-6 space-y-3">
              {useCases.map((item) => (
                <article key={item} className="rounded-[22px] border border-white/10 bg-black/20 px-4 py-4 text-sm text-white/72">
                  {item}
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(25,195,125,0.12),transparent_30%),black] p-6">
            <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">CTA</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold tracking-[-0.04em]">
              Coloque sua operacao conversacional para rodar com varios agentes, contexto oficial e qualidade mensuravel.
            </h2>
            <p className="mt-4 max-w-xl text-sm leading-8 text-white/70">
              O produto ja suporta agentes versionados, simulacao real com LLM, bindings de canal e monitoria basica. O proximo salto e
              ligar Chatwoot e transformar isso em inbox operacional real.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
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
                Ver demo
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
