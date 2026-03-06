import { NextRequest } from "next/server";

type DemoScenario = {
  reply: string;
  nextStep: string;
  qualification: string[];
};

const scenarios: Array<{ keywords: string[]; output: DemoScenario }> = [
  {
    keywords: ["orcamento", "parcela", "cabe no meu bolso", "renda"],
    output: {
      reply:
        "Eu nao vou te empurrar um plano fora de realidade. Primeiro eu enquadro sua faixa de parcela, depois cruzo com o tipo de produto e so entao te levo para uma simulacao objetiva.",
      nextStep: "Mapear faixa de parcela e abrir simulacao guiada.",
      qualification: ["orcamento", "urgencia", "faixa de parcela"],
    },
  },
  {
    keywords: ["financiamento", "juros", "vale a pena"],
    output: {
      reply:
        "Se a compra precisa acontecer imediatamente, eu comparo urgencia contra custo final. Se existe margem de planejamento, eu posiciono o consorcio como compra programada e conduzo a conversa sem prometer economia inventada.",
      nextStep: "Comparar urgencia do lead com horizonte de compra.",
      qualification: ["prazo", "urgencia", "perfil financeiro"],
    },
  },
  {
    keywords: ["seminovo", "usado", "idade do carro"],
    output: {
      reply:
        "Quando o lead fala de seminovo, eu puxo a regra oficial do produto antes de responder. Isso evita erro comercial e transforma a conversa em proposta viavel, nao em chute bonito.",
      nextStep: "Validar regra do produto e ano do veiculo desejado.",
      qualification: ["modelo", "ano", "regra do produto"],
    },
  },
  {
    keywords: ["whatsapp", "chatwoot", "canal", "atendimento"],
    output: {
      reply:
        "A agente pode nascer no WhatsApp, seguir por email e manter memoria da conversa inteira. O ponto nao e o canal; e preservar contexto comercial enquanto ela conduz para a proxima acao.",
      nextStep: "Mapear canal principal e configurar roteamento omnichannel.",
      qualification: ["canal", "handoff", "seguimento"],
    },
  },
];

function chooseScenario(message: string): DemoScenario {
  const folded = message.toLowerCase();
  for (const scenario of scenarios) {
    if (scenario.keywords.some((keyword) => folded.includes(keyword))) {
      return scenario.output;
    }
  }
  return {
    reply:
      "Eu entro na conversa como uma vendedora operacional: entendo contexto, diagnostico a dor, puxo a objecao real e sempre termino com um proximo passo comercial claro.",
    nextStep: "Descobrir contexto, objecao principal e meta do lead.",
    qualification: ["dor", "momento", "proximo passo"],
  };
}

function streamFromText(payload: DemoScenario, leadMessage: string) {
  const encoder = new TextEncoder();
  const fullReply = `${payload.reply} Proximo passo sugerido: ${payload.nextStep}`;
  const tokens = fullReply.split(" ");

  return new ReadableStream({
    async start(controller) {
      controller.enqueue(encoder.encode(`data: ${JSON.stringify({ lead_message: leadMessage, started: true })}\n\n`));
      for (const token of tokens) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ token })}\n\n`));
        await new Promise((resolve) => setTimeout(resolve, 28));
      }
      controller.enqueue(
        encoder.encode(
          `data: ${JSON.stringify({ done: true, next_step: payload.nextStep, qualification: payload.qualification })}\n\n`,
        ),
      );
      controller.close();
    },
  });
}

export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => null)) as { message?: string } | null;
  const message = body?.message?.trim();

  if (!message) {
    return new Response(JSON.stringify({ message: "Message is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const scenario = chooseScenario(message);
  const stream = streamFromText(scenario, message);

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
