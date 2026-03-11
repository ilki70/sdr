from __future__ import annotations

import unicodedata
from pathlib import Path

from app.agents.graph import run_sales_agent
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.knowledge import ingest_knowledge_source, ingest_manual_knowledge
from app.services.llm import judge_sales_reply
from app.services.messages import create_lab_conversation, get_conversation_or_none, list_recent_conversation_messages, persist_conversation_exchange
from app.services.vector_store import search_rag_context

settings = get_settings()

VINAC_SOURCES = [
    "https://vinac.com.br/",
    "https://vinac.com.br/adesao/",
    "https://vinac.com.br/conheca-as-vantagens-do-consorcio-vinac/",
    "https://vinac.com.br/downloads/vinac-consorcios-tabela-impressao.pdf",
    "https://vinac.com.br/downloads/Certidao_BACEN.pdf",
    "https://www.youtube.com/watch?v=4nwbwXwnjEE&feature=youtu.be",
]

VINAC_PLAYBOOK = """
PLAYBOOK OFICIAL VINAC PARA O AGENTE DE VENDAS.
Use somente estes fatos quando o lead perguntar sobre regras e condicoes.

- Produto: consorcio de carros.
- O credito VINAC permite escolher carro 0km ou seminovo de qualquer marca ou modelo.
- Seminovos: ate 3 anos.
- Grupos: 120 pessoas.
- Contemplacao mensal: dois consorciados por grupo, um por sorteio e outro por lance.
- Prazo dos grupos: 60 meses.
- Parcelas do fluxo online encontradas no site: de R$ 1.000,00 a R$ 1.300,00 com tabela reduzida; de R$ 1.400,00 a R$ 1.990,00; de R$ 2.000,00 a R$ 2.300,00; de R$ 2.300,00 a R$ 4.000,00; acima de R$ 4.000,00.
- Taxa de administracao: 12 por cento, equivalente a 0,2 por cento ao mes.
- Juros: o site informa que consorcio nao tem juros.
- Fundo de reserva: 3 por cento do valor do bem e o site informa que esse valor sera devolvido no final do plano.
- Adesao: preencher a proposta de adesao, assinar o contrato digital, pagar a primeira parcela do grupo e entao ja comecar a concorrer.
- Confiabilidade: a administradora informa que deve ser autorizada pelo Banco Central e publica certidao oficial no site.
- Carta de credito: quando contemplado, o consorciado pode comprar o carro da cota ou escolher outro modelo; na retirada da carta, e necessario alienar um veiculo conforme os termos do contrato.
- Se o lead perguntar algo sem fonte clara, nao invente. Diga que pode confirmar no site oficial ou na proposta/contrato.
- Nao afirmar taxa de adesao, entrada obrigatoria, carencia ou beneficio nao sustentado pelas fontes oficiais.
"""

VINAC_SCENARIOS = [
    {
        "name": "orcamento_abaixo_faixa",
        "turns": [
            "Tenho 900 reais por mes para a parcela e quero trocar de carro ainda este ano.",
            "Se 900 ficar abaixo da faixa, qual seria meu melhor proximo passo com a VINAC?",
        ],
        "must_include": [["simul"], ["1.000", "1000"]],
        "must_avoid": ["taxa de adesao", "entrada obrigatoria"],
    },
    {
        "name": "confiabilidade_bacen",
        "turns": [
            "Como eu sei que a VINAC e confiavel e autorizada para operar consorcio?",
        ],
        "must_include": [["banco central"]],
        "must_avoid": [],
    },
    {
        "name": "seminovo_regras",
        "turns": [
            "Posso usar a carta para comprar um seminovo? O carro tem limite de idade?",
        ],
        "must_include": [["seminovo"], ["3 anos", "ate 3"]],
        "must_avoid": ["nao ha restricao especifica"],
    },
    {
        "name": "taxas_e_juros",
        "turns": [
            "Consorcio VINAC tem juros? Quais taxas entram no plano?",
        ],
        "must_include": [["12%"], ["3%"], ["nao tem juros", "sem juros"]],
        "must_avoid": ["taxa de adesao"],
    },
    {
        "name": "como_funciona_contemplacao",
        "turns": [
            "Me explica como funciona a contemplacao, quantas pessoas tem no grupo e quantas sao contempladas por mes.",
        ],
        "must_include": [["120"], ["sorteio"], ["lance"], ["duas", "2"]],
        "must_avoid": [],
    },
    {
        "name": "adesao_online",
        "turns": [
            "Se eu decidir fechar hoje, como funciona a adesao online e quando comeco a concorrer?",
        ],
        "must_include": [["proposta"], ["contrato digital"], ["primeira parcela"], ["comeca a concorrer", "ja esta concorrendo", "ja comeca a concorrer"]],
        "must_avoid": ["taxa de adesao"],
    },
    {
        "name": "comparacao_financiamento",
        "turns": [
            "Estou comparando consorcio com financiamento. Como voce me convenceria a seguir com consorcio?",
        ],
        "must_include": [["sem juros", "nao tem juros"], ["simul"]],
        "must_avoid": ["nao exige entrada"],
    },
    {
        "name": "carta_de_credito",
        "turns": [
            "Quando eu for contemplado preciso comprar exatamente o carro da minha cota?",
        ],
        "must_include": [["outro modelo", "escolher outro"], ["onde comprar"]],
        "must_avoid": [],
    },
]


async def ensure_vinac_knowledge(tenant_id: str, product_id: str) -> list[str]:
    indexed_sources: list[str] = []
    async with SessionLocal() as session:
        await ingest_manual_knowledge(
            session,
            tenant_id=tenant_id,
            product_id=product_id,
            source_ref="vinac://official-sales-playbook",
            title="VINAC Official Sales Playbook",
            content=VINAC_PLAYBOOK,
        )
        indexed_sources.append("vinac://official-sales-playbook")
        for source_ref in VINAC_SOURCES:
            await ingest_knowledge_source(session, tenant_id=tenant_id, product_id=product_id, source_ref=source_ref)
            indexed_sources.append(source_ref)
    return indexed_sources


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def apply_rule_checks(reply: str, scenario: dict) -> dict:
    lowered = _fold(reply)
    penalties = 0.0
    failures: list[str] = []

    for group in scenario.get("must_include", []):
        if not any(_fold(term) in lowered for term in group):
            penalties += 0.5
            failures.append(f"faltou um destes termos: {', '.join(group)}")

    for term in scenario.get("must_avoid", []):
        if _fold(term) in lowered:
            penalties += 1.0
            failures.append(f"termo proibido encontrado: {term}")

    return {"penalties": penalties, "failures": failures}


async def _run_turn(
    tenant_id: str,
    conversation_id: str,
    lead_id: str,
    channel: str,
    message_text: str,
    scenario_name: str,
) -> dict:
    async with SessionLocal() as session:
        history = await list_recent_conversation_messages(session, tenant_id, conversation_id)
        state = AgentState(
            tenant_id=tenant_id,
            lead_id=lead_id,
            conversation_id=conversation_id,
            channel=channel,
            message_text=message_text,
            conversation_history=[
                {
                    "role": "assistant" if message.sender_type == "assistant" else "user",
                    "content": message.content,
                }
                for message in history
            ],
        )
        state = await run_sales_agent(state)
        knowledge = await search_rag_context(tenant_id, message_text, limit=4)
        official_context = " | ".join([str(item["content"]) for item in knowledge])
        evaluation = await judge_sales_reply(
            scenario_name=scenario_name,
            user_message=message_text,
            assistant_reply=state.draft_reply,
            official_context=official_context,
        )

    async with SessionLocal() as session:
        conversation = await get_conversation_or_none(session, tenant_id, conversation_id)
        assert conversation is not None
        await persist_conversation_exchange(
            db=session,
            conversation=conversation,
            user_text=message_text,
            assistant_text=state.draft_reply,
            intent=state.intent,
            confidence_score=state.confidence_score,
            model_name=settings.openai_model if settings.resolved_openai_api_key else "mock-llm",
        )

    return {
        "user_message": message_text,
        "assistant_reply": state.draft_reply,
        "intent": state.intent,
        "retrieved_context": state.retrieved_context,
        "evaluation": evaluation,
    }


async def run_vinac_lab(tenant_id: str) -> list[dict]:
    results: list[dict] = []
    for scenario in VINAC_SCENARIOS:
        async with SessionLocal() as session:
            conversation = await create_lab_conversation(
                session,
                tenant_id=tenant_id,
                channel="lab",
                title=f"VINAC Lab - {scenario['name']}",
            )
            lead_id = conversation.lead_id

        turns: list[dict] = []
        for turn in scenario["turns"]:
            result = await _run_turn(tenant_id, conversation.id, lead_id, "lab", turn, scenario["name"])
            rules = apply_rule_checks(result["assistant_reply"], scenario)
            result["rule_checks"] = rules
            result["adjusted_score"] = max(float(result["evaluation"].get("overall_score", 0)) - rules["penalties"], 0)
            turns.append(result)

        average_score = round(sum(float(turn["adjusted_score"]) for turn in turns) / max(len(turns), 1), 2)
        results.append(
            {
                "name": scenario["name"],
                "conversation_id": conversation.id,
                "average_score": average_score,
                "passed": average_score >= 4.0,
                "turns": turns,
            }
        )
    return results


def build_vinac_report(results: list[dict]) -> str:
    lines = [
        "# VINAC Sales Lab Report",
        "",
        "Simulacoes automatizadas do agente de vendas usando conteudo oficial da VINAC.",
        "",
        "| Cenario | Media | Status |",
        "| --- | ---: | --- |",
    ]
    for result in results:
        lines.append(f"| `{result['name']}` | {result['average_score']:.2f} | {'PASS' if result['passed'] else 'FAIL'} |")

    for result in results:
        lines.extend(
            [
                "",
                f"## {result['name']}",
                "",
                f"- Conversation ID: `{result['conversation_id']}`",
                f"- Media: `{result['average_score']:.2f}`",
                "",
            ]
        )
        for index, turn in enumerate(result["turns"], start=1):
            evaluation = turn["evaluation"]
            lines.extend(
                [
                    f"### Turno {index}",
                    "",
                    f"**Lead**: {turn['user_message']}",
                    "",
                    f"**Agente**: {turn['assistant_reply']}",
                    "",
                    f"- Intent: `{turn['intent']}`",
                    f"- Nota geral LLM: `{float(evaluation.get('overall_score', 0)):.2f}`",
                    f"- Nota ajustada: `{float(turn.get('adjusted_score', 0)):.2f}`",
                    f"- Grounding: `{evaluation.get('grounding_score', '-')}`",
                    f"- Qualification: `{evaluation.get('qualification_score', '-')}`",
                    f"- Next step: `{evaluation.get('next_step_score', '-')}`",
                    f"- Objection: `{evaluation.get('objection_score', '-')}`",
                    f"- Strengths: `{'; '.join(evaluation.get('strengths', []))}`",
                    f"- Weaknesses: `{'; '.join(evaluation.get('weaknesses', []))}`",
                    f"- Rule failures: `{'; '.join(turn.get('rule_checks', {}).get('failures', [])) or 'none'}`",
                    "",
                ]
            )
    return "\n".join(lines)


def summarize_vinac_results(results: list[dict]) -> dict:
    passed = sum(1 for item in results if item["passed"])
    failed = len(results) - passed
    average = round(sum(float(item["average_score"]) for item in results) / max(len(results), 1), 2)
    return {
        "scenario_count": len(results),
        "passed_count": passed,
        "failed_count": failed,
        "average_score": average,
        "passed": failed == 0,
    }


def write_vinac_report(report_markdown: str) -> str:
    report_path = Path(__file__).resolve().parents[3] / "docs" / "vinac-simulation-report.md"
    report_path.write_text(report_markdown, encoding="utf-8")
    return str(report_path)
