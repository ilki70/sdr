import Link from "next/link";

import { AgentStage } from "@/components/marketing/agent-stage";
import { marketingSans, marketingSerif } from "@/components/marketing/fonts";
import { LeadCaptureForm } from "@/components/marketing/lead-capture-form";

const capabilityCards = [
  {
    title: "Diagnostica antes de vender",
    text: "A agente entende dor, urgencia, faixa de preco, maturidade do lead e objecoes antes de empurrar oferta.",
  },
  {
    title: "Conversa como operacao comercial",
    text: "Nao e FAQ com verniz. E um fluxo orientado a meta, proximo passo e conversao.",
  },
  {
    title: "Aprende o seu playbook",
    text: "Produto, politica comercial, persona, scripts, FAQ, objecoes e limites reais do negocio.",
  },
];

const workflow = [
  "Voce sobe paginas, PDFs, videos e documentos do cliente.",
  "Define a persona comercial, tom, regras e limites de venda.",
  "Liga os canais e deixa a agente operar com memoria, RAG e follow-up.",
];

const proofPoints = [
  "WhatsApp, e-mail e operacao omnichannel via Chatwoot",
  "RAG com fontes oficiais e busca semantica",
  "Comissoes configuraveis, historico e auditoria",
  "Laboratorio para simular objecoes e validar grounding",
];

const cases = [
  {
    sector: "Consorcios e credito",
    title: "Agente que nao atropela o lead",
    text: "Abre pela dor, enquadra parcela, puxa o veiculo desejado e encaminha para simulacao sem inventar condicoes.",
    metric: "Memoria + grounding",
  },
  {
    sector: "Servicos B2B complexos",
    title: "Primeiro contato que qualifica de verdade",
    text: "Separa curiosidade de oportunidade real, captura contexto comercial e devolve pro time humano ja com resumo executivo.",
    metric: "SDR digital persistente",
  },
  {
    sector: "Operacao omnichannel",
    title: "Mesmo discurso, varios canais",
    text: "A conversa pode nascer no WhatsApp, migrar para email e seguir com contexto unico dentro do funil.",
    metric: "Canal sem perda de contexto",
  },
];

const credibilityStrip = [
  "Playbook versionado",
  "Mensagens fragmentadas",
  "Follow-up automatico",
  "Memoria por conversa",
  "Roteiro comercial auditavel",
];

export default function MarketingPage() {
  return (
    <main className={`${marketingSans.variable} ${marketingSerif.variable} min-h-screen overflow-hidden bg-[#060b16] text-[#f5f1ea]`}>
      <div className="relative isolate">
        <div className="absolute inset-x-0 top-0 h-[760px] bg-[radial-gradient(circle_at_18%_12%,rgba(255,128,76,0.28),transparent_32%),radial-gradient(circle_at_88%_20%,rgba(122,210,255,0.22),transparent_30%),linear-gradient(180deg,#08101d,#060b16)]" />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,transparent,rgba(6,11,22,0.9)_70%,#060b16)]" />

        <div className="relative mx-auto flex w-full max-w-7xl flex-col px-6 pb-20 pt-6 md:px-8 lg:px-10">
          <header className="flex flex-wrap items-center justify-between gap-4 rounded-full border border-white/10 bg-white/5 px-5 py-3 backdrop-blur-md">
            <div>
              <p className="text-[11px] uppercase tracking-[0.32em] text-[#7ad2ff]">Super Vendedor</p>
              <strong className="mt-1 block text-sm font-medium text-white/88">Sales agents that close</strong>
            </div>
            <nav className="flex items-center gap-3 text-sm text-white/60">
              <a href="#como-funciona" className="transition hover:text-white">Como funciona</a>
              <a href="#motor" className="transition hover:text-white">Motor comercial</a>
              <a href="#cases" className="transition hover:text-white">Casos</a>
              <a href="#demo" className="transition hover:text-white">Demo</a>
              <a href="#captura" className="transition hover:text-white">Contato</a>
            </nav>
            <div className="flex items-center gap-3">
              <Link href="/login" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/85 transition hover:bg-white/6">
                Entrar
              </Link>
              <Link href="/demo" className="rounded-full bg-[#ff875a] px-4 py-2 text-sm font-semibold text-black transition hover:bg-[#ff9b75]">
                Ver a agente
              </Link>
            </div>
          </header>

          <section className="grid gap-12 pb-16 pt-14 lg:grid-cols-[1.02fr_0.98fr] lg:items-center lg:pb-20 lg:pt-20">
            <div className="max-w-3xl">
              <p className="inline-flex rounded-full border border-[#7ad2ff]/20 bg-[#7ad2ff]/8 px-4 py-2 text-[11px] uppercase tracking-[0.26em] text-[#7ad2ff]">
                terceirize seu time de vendas sem terceirizar conversao
              </p>
              <h1 className="mt-7 max-w-4xl text-5xl font-semibold leading-[0.94] tracking-[-0.04em] text-white md:text-7xl lg:text-[5.4rem]">
                Coloque uma
                <span className={`${marketingSerif.className} mx-3 text-[#ffccb8]`}>agente comercial</span>
                viva na tela da sua operacao.
              </h1>
              <p className="mt-7 max-w-2xl text-lg leading-8 text-white/70 md:text-xl">
                O Super Vendedor instala uma especialista em vendas dentro do seu funil. Ela aparece, conversa, qualifica, rebate objecoes e puxa o lead para a proxima acao com memoria, RAG e playbook real.
              </p>

              <div className="mt-9 flex flex-wrap gap-4">
                <Link href="/demo" className="rounded-full bg-[#ff875a] px-6 py-3 text-sm font-semibold text-black transition hover:bg-[#ff9b75]">
                  Ver experiencia da agente
                </Link>
                <a href="#captura" className="rounded-full border border-white/12 px-6 py-3 text-sm font-semibold text-white/88 transition hover:bg-white/6">
                  Pedir avaliacao consultiva
                </a>
              </div>

              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                <div className="rounded-[24px] border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">Canal</p>
                  <strong className="mt-2 block text-lg text-white">WhatsApp + e-mail</strong>
                </div>
                <div className="rounded-[24px] border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">Cerebro</p>
                  <strong className="mt-2 block text-lg text-white">RAG + memoria + follow-up</strong>
                </div>
                <div className="rounded-[24px] border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">Objetivo</p>
                  <strong className="mt-2 block text-lg text-white">Levar lead ate o fechamento</strong>
                </div>
              </div>
            </div>

            <AgentStage variant="hero" />
          </section>

          <section className="grid gap-4 border-y border-white/8 py-6 text-sm text-white/56 lg:grid-cols-5">
            <div>
              <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">Opera com</p>
              <strong className="mt-2 block text-base text-white/84">Chatwoot, automacao e roteiros comerciais</strong>
            </div>
            {proofPoints.map((item) => (
              <div key={item} className="rounded-[22px] border border-white/8 bg-white/4 px-4 py-3">
                {item}
              </div>
            ))}
          </section>
        </div>
      </div>

      <section id="como-funciona" className="mx-auto w-full max-w-7xl px-6 py-20 md:px-8 lg:px-10">
        <div className="grid gap-10 lg:grid-cols-[0.7fr_1.3fr] lg:items-start">
          <div>
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#7ad2ff]">Como entra em operacao</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              Montamos uma
              <span className={`${marketingSerif.className} ml-2 text-[#ffccb8]`}>vendedora digital</span>
              em cima do seu negocio.
            </h2>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {workflow.map((item, index) => (
              <article key={item} className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] p-6">
                <p className="text-[11px] uppercase tracking-[0.3em] text-white/35">Etapa 0{index + 1}</p>
                <p className="mt-5 text-lg leading-8 text-white/80">{item}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="motor" className="mx-auto w-full max-w-7xl px-6 pb-20 md:px-8 lg:px-10">
        <div className="grid gap-5 lg:grid-cols-[1fr_0.95fr]">
          <div className="rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,24,44,0.96),rgba(8,11,19,0.96))] p-8">
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#7ad2ff]">Motor comercial</p>
            <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              A estetica importa, mas o valor esta em uma conversa orientada a venda.
            </h2>
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {capabilityCards.map((card) => (
                <article key={card.title} className="rounded-[26px] border border-white/10 bg-white/5 p-5">
                  <h3 className="text-xl font-semibold text-white">{card.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-white/66">{card.text}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,135,90,0.12),rgba(122,210,255,0.06))] p-8">
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#ffb86a]">Estrutura de oferta</p>
            <div className="mt-5 space-y-4">
              <div className="rounded-[26px] border border-white/10 bg-black/20 p-5">
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">Memoria</p>
                <p className="mt-3 text-lg text-white/82">Cada conversa volta com historico, intencao, contexto e proximo passo sugerido.</p>
              </div>
              <div className="rounded-[26px] border border-white/10 bg-black/20 p-5">
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">Governanca</p>
                <p className="mt-3 text-lg text-white/82">A agente trabalha dentro das regras comerciais e das fontes oficiais do cliente.</p>
              </div>
              <div className="rounded-[26px] border border-white/10 bg-black/20 p-5">
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">Resultado esperado</p>
                <p className="mt-3 text-lg text-white/82">Menos abandono, mais qualificacao consistente e fechamento guiado por processo.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="cases" className="mx-auto w-full max-w-7xl px-6 pb-20 md:px-8 lg:px-10">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#7ad2ff]">Casos e leitura de valor</p>
            <h2 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              A mesma interface pode vender
              <span className={`${marketingSerif.className} ml-2 text-[#ffccb8]`}>segmentos diferentes</span>
              sem perder disciplina comercial.
            </h2>
          </div>
          <div className="rounded-full border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/66">
            O formato muda. O principio continua: qualificar, conduzir e fechar.
          </div>
        </div>

        <div className="mt-8 grid gap-5 lg:grid-cols-3">
          {cases.map((item) => (
            <article key={item.title} className="rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] p-6">
              <p className="text-[11px] uppercase tracking-[0.28em] text-white/35">{item.sector}</p>
              <h3 className="mt-4 text-2xl font-semibold text-white">{item.title}</h3>
              <p className="mt-4 text-sm leading-7 text-white/68">{item.text}</p>
              <div className="mt-6 rounded-[22px] border border-white/10 bg-black/20 px-4 py-3 text-sm text-[#7ad2ff]">
                {item.metric}
              </div>
            </article>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          {credibilityStrip.map((item) => (
            <span key={item} className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70">
              {item}
            </span>
          ))}
        </div>
      </section>

      <section id="demo" className="mx-auto w-full max-w-7xl px-6 pb-24 md:px-8 lg:px-10">
        <div className="overflow-hidden rounded-[40px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-7 md:p-10">
          <div className="grid gap-10 lg:grid-cols-[0.78fr_1.22fr] lg:items-center">
            <div>
              <p className="text-[11px] uppercase tracking-[0.3em] text-[#7ad2ff]">Demo visual</p>
              <h2 className="mt-4 text-4xl font-semibold leading-tight text-white md:text-5xl">
                A agente aparece como parte da
                <span className={`${marketingSerif.className} ml-2 text-[#ffccb8]`}>maquina de vendas</span>.
              </h2>
              <p className="mt-5 max-w-xl text-lg leading-8 text-white/70">
                Foi essa sensacao que puxamos da referencia: a vendedora ocupando a tela e conduzindo a narrativa. Aqui isso vira um mockup proprio, focado em conversao e operacao omnichannel.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link href="/demo" className="rounded-full bg-[#7ad2ff] px-6 py-3 text-sm font-semibold text-black transition hover:bg-[#95dcff]">
                  Abrir demo interativa
                </Link>
                <a href="#captura" className="rounded-full border border-white/12 px-6 py-3 text-sm font-semibold text-white/85 transition hover:bg-white/6">
                  Capturar um caso real
                </a>
              </div>
            </div>

            <AgentStage variant="demo" />
          </div>
        </div>
      </section>

      <section id="captura" className="mx-auto w-full max-w-7xl px-6 pb-24 md:px-8 lg:px-10">
        <LeadCaptureForm />
      </section>
    </main>
  );
}
