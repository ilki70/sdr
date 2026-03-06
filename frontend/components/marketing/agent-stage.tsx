type AgentStageProps = {
  variant?: "hero" | "demo";
};

const heroMessages = [
  { role: "lead", text: "Quero trocar de carro, mas meu orcamento e apertado." },
  { role: "agent", text: "Posso te mostrar uma faixa realista de parcela e conduzir a simulacao agora." },
  { role: "lead", text: "Se couber abaixo de R$ 1.400, eu sigo." },
  { role: "agent", text: "Perfeito. Vou te levar para o menor intervalo viavel e ja separar os proximos passos." },
];

const demoMessages = [
  { role: "lead", text: "Tenho duvida se consorcio vale mais que financiamento." },
  { role: "agent", text: "Depende do seu prazo e urgencia. Se voce puder planejar a compra, eu comparo o custo final com voce." },
  { role: "lead", text: "E se eu quiser um seminovo?" },
  { role: "agent", text: "Eu confirmo a regra do produto, valido a idade do veiculo e sigo com a proposta sem inventar dado." },
];

export function AgentStage({ variant = "hero" }: AgentStageProps) {
  const messages = variant === "hero" ? heroMessages : demoMessages;
  const compact = variant === "hero";

  return (
    <div className="relative mx-auto w-full max-w-[680px]">
      <div className="spot-pulse absolute -left-8 top-14 h-28 w-28 rounded-full bg-[rgba(255,104,61,0.28)] blur-3xl" />
      <div className="spot-pulse absolute -right-4 bottom-8 h-36 w-36 rounded-full bg-[rgba(122,210,255,0.24)] blur-3xl" />

      <div className="float-slow absolute -left-2 top-8 hidden rounded-[22px] border border-white/12 bg-[rgba(8,14,31,0.82)] px-4 py-3 text-sm text-white/75 shadow-[0_18px_50px_rgba(0,0,0,0.35)] md:block">
        <p className="text-[10px] uppercase tracking-[0.24em] text-[#7ad2ff]">Qualificacao</p>
        <strong className="mt-2 block text-lg text-white">Lead aquecido em 02:14</strong>
        <p className="mt-1 max-w-[160px] text-xs text-white/55">Diagnostico, objecao e proximo passo em uma unica conversa.</p>
      </div>

      <div className="float-fast absolute -right-3 top-24 hidden rounded-[22px] border border-white/12 bg-[rgba(8,14,31,0.82)] px-4 py-3 text-sm text-white/75 shadow-[0_18px_50px_rgba(0,0,0,0.35)] lg:block">
        <p className="text-[10px] uppercase tracking-[0.24em] text-[#ffb86a]">Fechamento</p>
        <strong className="mt-2 block text-lg text-white">+27% de avancos</strong>
        <p className="mt-1 max-w-[160px] text-xs text-white/55">Follow-up automatico, memoria e contexto comercial persistente.</p>
      </div>

      <div className="relative overflow-hidden rounded-[36px] border border-white/12 bg-[linear-gradient(180deg,rgba(9,13,28,0.92),rgba(15,24,46,0.96))] p-3 shadow-[0_30px_90px_rgba(0,0,0,0.45)]">
        <div className="absolute inset-0 grid-glow opacity-40" />
        <div className="absolute inset-0 scan-lines opacity-20" />

        <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(21,31,58,0.98),rgba(7,12,24,0.98))] p-4 md:p-5">
          <div className="flex items-center justify-between rounded-[18px] border border-white/8 bg-black/20 px-4 py-3 text-xs text-white/55">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-[#ff6840]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#ffb86a]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#7ad2ff]" />
            </div>
            <span>Agent Console / live selling session</span>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-[220px_1fr]">
            <div className="rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))] p-4">
              <div className="relative mx-auto h-44 w-full max-w-[180px] overflow-hidden rounded-[28px] border border-white/12 bg-[radial-gradient(circle_at_50%_20%,rgba(122,210,255,0.38),transparent_35%),linear-gradient(180deg,#1c355f,#0b1326)]">
                <div className="spot-pulse absolute left-1/2 top-11 h-24 w-24 -translate-x-1/2 rounded-full bg-[#7ad2ff]/18 blur-2xl" />
                <div className="absolute inset-x-0 bottom-0 h-[55%] rounded-t-[38px] bg-[linear-gradient(180deg,#ff9f7a,#ff6d45)]" />
                <div className="absolute left-1/2 top-[22%] h-20 w-20 -translate-x-1/2 rounded-full border border-white/18 bg-[radial-gradient(circle_at_45%_35%,#ffd7b8,transparent_35%),linear-gradient(180deg,#423355,#131a2f)] shadow-[0_12px_22px_rgba(0,0,0,0.28)]" />
                <div className="absolute left-[39%] top-[36%] h-1.5 w-1.5 rounded-full bg-[#2a2533]" />
                <div className="absolute right-[39%] top-[36%] h-1.5 w-1.5 rounded-full bg-[#2a2533]" />
                <div className="blink absolute left-1/2 top-[34%] h-10 w-16 -translate-x-1/2 rounded-[40px] border border-white/10 bg-[#f7c6a1]" />
                <div className="absolute inset-x-6 bottom-0 h-24 rounded-t-[28px] bg-[linear-gradient(180deg,#f3f0ef,#d7d2d8)]" />
                <div className="equalizer absolute bottom-4 left-1/2 flex -translate-x-1/2 items-end gap-1">
                  <span className="bar h-2 w-1 rounded-full bg-[#7ad2ff]" />
                  <span className="bar h-4 w-1 rounded-full bg-[#7ad2ff]" />
                  <span className="bar h-6 w-1 rounded-full bg-[#ffb86a]" />
                  <span className="bar h-3 w-1 rounded-full bg-[#7ad2ff]" />
                </div>
              </div>

              <div className="mt-4 text-center">
                <p className="text-[11px] uppercase tracking-[0.28em] text-[#7ad2ff]">Agente em operacao</p>
                <h3 className="mt-2 text-2xl font-semibold text-white">Aurora Sales AI</h3>
                <p className="mt-2 text-sm text-white/60">Conduz, qualifica, rebate objecoes e puxa o lead para a proxima acao.</p>
              </div>

              <dl className="mt-5 grid grid-cols-2 gap-3 text-left text-sm">
                <div className="rounded-2xl border border-white/8 bg-black/20 p-3">
                  <dt className="text-[11px] uppercase tracking-wide text-white/40">Canal</dt>
                  <dd className="mt-2 text-white">WhatsApp</dd>
                </div>
                <div className="rounded-2xl border border-white/8 bg-black/20 p-3">
                  <dt className="text-[11px] uppercase tracking-wide text-white/40">Modo</dt>
                  <dd className="mt-2 text-white">ao vivo</dd>
                </div>
              </dl>
            </div>

            <div className="space-y-4 rounded-[26px] border border-white/10 bg-[rgba(5,10,20,0.7)] p-4 md:p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.28em] text-white/35">Janela comercial</p>
                  <h3 className="mt-2 text-xl font-semibold text-white">A agente aparece dentro da operacao, nao como um chatbot perdido</h3>
                </div>
                <div className="rounded-full border border-[#7ad2ff]/30 bg-[#7ad2ff]/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-[#7ad2ff]">
                  SDR + closer
                </div>
              </div>

              <div className="space-y-3">
                {messages.map((message, index) => (
                  <article
                    key={`${message.role}-${index}`}
                    className={`max-w-[92%] rounded-[22px] border px-4 py-3 text-sm leading-relaxed ${
                      message.role === "agent"
                        ? "border-[#ff875a]/20 bg-[linear-gradient(180deg,rgba(255,135,90,0.18),rgba(255,135,90,0.08))] text-white"
                        : "ml-auto border-white/10 bg-white/6 text-white/78"
                    }`}
                  >
                    <p className="mb-2 text-[11px] uppercase tracking-[0.22em] text-white/38">
                      {message.role === "agent" ? "agente" : "lead"}
                    </p>
                    <p>{message.text}</p>
                  </article>
                ))}
              </div>

              <div className={`grid gap-3 ${compact ? "md:grid-cols-3" : "md:grid-cols-2"}`}>
                <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/38">Roteiro vivo</p>
                  <p className="mt-2 text-sm text-white/72">Persona, produto, regra comercial e memorizacao da conversa.</p>
                </div>
                <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/38">Acao seguinte</p>
                  <p className="mt-2 text-sm text-white/72">Simulacao, proposta, recuperacao de lead e follow-up automatico.</p>
                </div>
                {compact ? (
                  <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] uppercase tracking-[0.22em] text-white/38">Confiabilidade</p>
                    <p className="mt-2 text-sm text-white/72">Responde ancorada no RAG e no playbook oficial da sua operacao.</p>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
