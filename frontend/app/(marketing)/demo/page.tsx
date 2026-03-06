import Link from "next/link";

import { AgentStage } from "@/components/marketing/agent-stage";
import { DemoConsole } from "@/components/marketing/demo-console";
import { marketingSans, marketingSerif } from "@/components/marketing/fonts";

const checkpoints = [
  "A agente fragmenta a resposta em blocos curtos, sem soar robotica.",
  "Cada resposta carrega proximo passo sugerido para o lead.",
  "As regras do produto entram no contexto via RAG e playbook versionado.",
  "O objetivo e recuperar contexto comercial, nao so responder bonito.",
];

export default function DemoPage() {
  return (
    <main className={`${marketingSans.variable} ${marketingSerif.variable} min-h-screen bg-[#060b16] px-6 py-10 text-[#f5f1ea] md:px-8 lg:px-10`}>
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-full border border-white/10 bg-white/5 px-5 py-3 backdrop-blur-md">
          <div>
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#7ad2ff]">Demo</p>
            <strong className="mt-1 block text-sm font-medium text-white/88">Mockup da agente comercial com backend real</strong>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/85 transition hover:bg-white/6">
              Voltar para landing
            </Link>
            <Link href="/login" className="rounded-full bg-[#ff875a] px-4 py-2 text-sm font-semibold text-black transition hover:bg-[#ff9b75]">
              Entrar no app
            </Link>
          </div>
        </header>

        <section className="grid gap-10 pb-8 pt-12 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
          <div>
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#ffb86a]">Experiencia visual</p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-white md:text-6xl">
              A tela do computador vira a
              <span className={`${marketingSerif.className} ml-2 text-[#ffccb8]`}>palco</span>
              da vendedora digital.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-white/68">
              Em vez de mostrar um chatbot generico, a demo posiciona a agente como um ativo comercial: rosto, ritmo de conversa, contexto e direcao de fechamento. Agora a conversa publica ja passa pelo backend do MVP e persiste a sessao.
            </p>

            <div className="mt-8 space-y-3">
              {checkpoints.map((item) => (
                <div key={item} className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/78">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <AgentStage variant="demo" />
        </section>

        <DemoConsole />
      </div>
    </main>
  );
}
