from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import random
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_sales_agent
from app.agents.state import AgentState
from app.models.entities import Agent, AgentVersion, BotPersona, EvaluationRun, PersonaVersion
from app.schemas.agents import AgentVersionCreateRequest
from app.schemas.knowledge import EvaluationRunResponse
from app.schemas.personas import PersonaVersionCreateRequest
from app.schemas.training import AgentTrainingRequest, AgentTrainingResponse, TrainingCycleResponse
from app.services.agents import (
    create_agent_version,
    get_agent_or_none,
    get_published_agent_version_or_none,
)
from app.services.conversation_context import refresh_conversation_context_from_db
from app.services.knowledge_ops import create_evaluation_run, mark_evaluation_finished, mark_evaluation_started
from app.services.llm import judge_sales_reply
from app.services.messages import (
    create_lab_conversation,
    list_recent_conversation_messages,
    persist_conversation_exchange,
)
from app.services.personas import create_persona_version, get_persona_or_none


@dataclass(frozen=True)
class TrainingScenario:
    name: str
    message: str


FOCUS_SCENARIOS: dict[str, list[TrainingScenario]] = {
    "first_attendance": [
        TrainingScenario("abertura", "Oi, estou pesquisando consorcio e quero entender por onde comeco."),
        TrainingScenario("budget", "Tenho um orcamento de R$ 1.800 por mes. O que faz sentido para mim?"),
        TrainingScenario("timeline", "Quero resolver isso em ate 8 meses. Consorcio ajuda ou nao?"),
        TrainingScenario("trust", "Como eu sei que nao vao me empurrar promessa vazia?"),
        TrainingScenario("fees", "Tem juros? E como funciona taxa de administracao?"),
        TrainingScenario("lance", "Se eu quiser usar lance, como voce me orienta?"),
        TrainingScenario("next_step", "Se eu gostar, qual e o proximo passo pratico?"),
        TrainingScenario("follow_up", "Se eu sumir depois, como voce faz o follow-up?"),
    ],
    "qualification": [
        TrainingScenario("goal", "Quero comprar um carro e preciso entender qual faixa cabe no meu caso."),
        TrainingScenario("entry", "Tenho algo para dar de entrada, isso muda bastante?"),
        TrainingScenario("budget", "Qual parcela fica saudavel para mim sem apertar o caixa?"),
        TrainingScenario("timeline", "Meu prazo e de 12 meses, como voce me qualificaria?"),
        TrainingScenario("use_case", "Consorcio faz sentido para uso pessoal ou tambem para trabalho?"),
        TrainingScenario("lance", "Se eu ja tenho lance guardado, como isso entra na conversa?"),
        TrainingScenario("next_step", "Que informacoes voce precisa para avançar comigo?"),
    ],
    "objection_handling": [
        TrainingScenario("price", "Consorcio parece caro. O que eu ganho em trocar de carro por esse caminho?"),
        TrainingScenario("fees", "A taxa de administracao nao pesa demais no final?"),
        TrainingScenario("trust", "Tenho medo de entrar e nao conseguir o bem tao cedo."),
        TrainingScenario("comparison", "Por que nao financiar direto?"),
        TrainingScenario("security", "Como eu confiro se a proposta e segura e oficial?"),
        TrainingScenario("lance", "Nao quero depender so de sorteio. O lance realmente ajuda?"),
        TrainingScenario("next_step", "Se eu ainda estiver em duvida, como voce me conduz sem pressionar?"),
    ],
    "closing": [
        TrainingScenario("proposal", "Se eu decidir seguir agora, como eu fecho sem enrolacao?"),
        TrainingScenario("decision", "Quero objetividade: qual e a melhor proposta para eu analisar?"),
        TrainingScenario("urgency", "Tenho pressa e preciso de um proximo passo claro ainda hoje."),
        TrainingScenario("documents", "Quais dados ou documentos voce precisa para preparar a proposta?"),
        TrainingScenario("follow_up", "Depois da proposta, como voce me acompanha ate a decisao?"),
    ],
    "follow_up": [
        TrainingScenario("first_touch", "Ontem eu olhei e hoje ainda estou avaliando. O que voce me manda?"),
        TrainingScenario("budget", "Eu ainda estou ajustando meu orcamento. Como voce me ajuda sem forcar?"),
        TrainingScenario("decision", "Ainda nao fechei, mas quero manter a conversa viva."),
        TrainingScenario("next_step", "Se eu nao responder agora, qual mensagem de retorno faz sentido?"),
    ],
}


def _merge_unique(existing: list[str], additions: list[str]) -> list[str]:
    seen = set()
    merged: list[str] = []
    for item in [*existing, *additions]:
        normalized = " ".join(item.split()).strip()
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        merged.append(normalized)
    return merged


def _evaluation_run_response(run: EvaluationRun) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        id=run.id,
        tenant_id=run.tenant_id,
        product_id=run.product_id,
        created_by_user_id=run.created_by_user_id,
        evaluation_type=run.evaluation_type,
        status=run.status,
        summary_json=run.summary_json,
        report_markdown=run.report_markdown,
        error_message=run.error_message,
        celery_task_id=run.celery_task_id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _focus_label(focus: str) -> str:
    labels = {
        "first_attendance": "primeiro atendimento",
        "qualification": "qualificacao",
        "objection_handling": "tratamento de objecoes",
        "closing": "fechamento",
        "follow_up": "follow-up",
    }
    return labels.get(focus, focus)


def _scenario_bank(focus: str) -> list[TrainingScenario]:
    return FOCUS_SCENARIOS.get(focus, FOCUS_SCENARIOS["first_attendance"])


def _select_scenarios(focus: str, cycles: int, interactions_per_cycle: int, seed: str) -> list[list[TrainingScenario]]:
    bank = _scenario_bank(focus)
    rng = random.Random(seed)
    pool = bank[:]
    rng.shuffle(pool)
    if not pool:
        pool = FOCUS_SCENARIOS["first_attendance"][:]
    batches: list[list[TrainingScenario]] = []
    cursor = 0
    for cycle in range(cycles):
        batch: list[TrainingScenario] = []
        for turn in range(interactions_per_cycle):
            if cursor >= len(pool):
                rng.shuffle(pool)
                cursor = 0
            scenario = pool[cursor]
            cursor += 1
            batch.append(scenario)
        batches.append(batch)
    return batches


def _build_context_block(persona: BotPersona, persona_version: PersonaVersion, agent: Agent, agent_version: AgentVersion) -> str:
    rules = ", ".join(persona_version.approach_rules_json.get("rules", []))
    objections = "; ".join(f"{key}: {value}" for key, value in persona_version.objection_playbook_json.items())
    policies = "; ".join(str(item) for item in agent_version.policy_json.get("rules", []))
    return (
        f"Agente={agent.name}. Persona={persona.name}. Tom={persona_version.tone}. "
        f"Prompt da persona={persona_version.prompt_system}. Regras da persona={rules}. "
        f"Playbook de objecoes={objections}. Prompt do agente={agent_version.prompt_system}. "
        f"Politicas do agente={policies}."
    )


def _score_to_recommendations(averages: dict[str, float], focus: str) -> list[str]:
    recommendations: list[str] = []
    if averages["grounding"] < 4:
        recommendations.append("Ancorar respostas apenas no contexto oficial e evitar inventar taxa, prazo ou entrada.")
    if averages["qualification"] < 4:
        recommendations.append("Fazer perguntas de qualificacao antes de acelerar para fechamento.")
    if averages["next_step"] < 4:
        recommendations.append("Sempre terminar com um proximo passo claro e pratico.")
    if averages["objection"] < 4:
        recommendations.append("Responder objecoes com validacao curta, explicacao objetiva e encaminhamento.")
    if averages["length"] < 4:
        recommendations.append("Expandir a resposta para nao parecer curta demais no primeiro atendimento.")
    if focus == "follow_up":
        recommendations.append("Usar follow-up consultivo e nao insistente, com linguagem de acompanhamento.")
    return _merge_unique([], recommendations)


def _apply_persona_revision(
    persona_version: PersonaVersion,
    recommendations: list[str],
    cycle_no: int,
    focus: str,
) -> PersonaVersionCreateRequest:
    added_rules = [
        "Responder com tom consultivo, claro, simpatico e pratico.",
        "Abrir o primeiro atendimento com boas-vindas, apresentacao e pergunta sobre o nome do lead.",
        "Explicar que esta disponivel para ajudar com duvidas sobre consorcios.",
        "Conduzir a conversa com delicadeza para entender a intencao do lead e preparar a melhor proposta.",
        "Evitar repeticao desnecessaria de saudacoes, perguntas e formulas de texto.",
        "Fazer no maximo uma pergunta por turno.",
        "Confirmar apenas dados novos ou conflitantes, sem repetir o resumo inteiro em toda resposta.",
        "Nunca encerrar sem indicar o proximo passo.",
    ]
    if any("contexto oficial" in item.lower() for item in recommendations):
        added_rules.append("Usar apenas fatos confirmados pelo contexto oficial.")
    if any("qualificacao" in item.lower() for item in recommendations):
        added_rules.append("Fazer qualificacao com objetivo, prazo e faixa de parcela antes de aprofundar.")
    if any("objec" in item.lower() for item in recommendations):
        added_rules.append("Tratar objecoes com validacao + explicacao + proximo passo.")
    if any("follow-up" in item.lower() for item in recommendations):
        added_rules.append("No follow-up, ser acompanhadora e objetiva.")

    revised_prompt = [
        persona_version.prompt_system.rstrip(),
        "",
        f"Ajustes do ciclo {cycle_no} para foco em {_focus_label(focus)}:",
    ]
    revised_prompt.append(
        "Diretriz adicional fixa: manter abertura simpatica, se apresentar no primeiro contato, perguntar o nome do lead, "
        "explicar que esta disponivel para ajudar com consorcios, evitar repeticao, fazer no maximo uma pergunta por turno e "
        "confirmar apenas os dados novos ou conflitantes, sem repetir o resumo inteiro a cada resposta."
    )
    for item in recommendations:
        revised_prompt.append(f"- {item}")
    revised_prompt.append("- Manter o texto em portugues do Brasil.")

    objection_playbook = dict(persona_version.objection_playbook_json)
    if "tempo de contemplacao" not in objection_playbook:
        objection_playbook["tempo de contemplacao"] = (
            "Explicar que contemplacao nao e garantida e que o foco e alinhar expectativa, prazo e estrategia comercial oficial."
        )
    if "taxa ou custo" not in objection_playbook:
        objection_playbook["taxa ou custo"] = (
            "Explicar que o custo precisa ser confirmado na proposta oficial e que a comparacao correta considera parcela, prazo e objetivo."
        )
    if "seguranca" not in objection_playbook:
        objection_playbook["seguranca"] = "Reforcar que a proposta deve ser confirmada no material oficial e no acompanhamento humano."

    return PersonaVersionCreateRequest(
        tone=persona_version.tone,
        prompt_system="\n".join(revised_prompt).strip(),
        approach_rules=_merge_unique(persona_version.approach_rules_json.get("rules", []), added_rules),
        objection_playbook=objection_playbook,
        publish=True,
    )


def _apply_agent_revision(
    agent_version: AgentVersion,
    persona_id: str,
    persona_version_no: int,
    recommendations: list[str],
    cycle_no: int,
    focus: str,
) -> AgentVersionCreateRequest:
    revised_prompt = [
        agent_version.prompt_system.rstrip(),
        "",
        f"Atualizacao de treino do ciclo {cycle_no} para {_focus_label(focus)}:",
    ]
    revised_prompt.append(
        "Diretriz adicional fixa: manter abertura simpatica, se apresentar no primeiro contato, perguntar o nome do lead, "
        "explicar que esta disponivel para ajudar com consorcios, evitar repeticao, fazer no maximo uma pergunta por turno e "
        "confirmar apenas os dados novos ou conflitantes, sem repetir o resumo inteiro a cada resposta."
    )
    for item in recommendations:
        revised_prompt.append(f"- {item}")
    revised_prompt.append("- Priorizar respostas praticas, com tom humano e proximo passo sempre claro.")
    return AgentVersionCreateRequest(
        persona_id=persona_id,
        persona_version_no=persona_version_no,
        prompt_system="\n".join(revised_prompt).strip(),
        policy_json=agent_version.policy_json,
        tool_config_json=agent_version.tool_config_json,
        knowledge_config_json=agent_version.knowledge_config_json,
        channel_config_json=agent_version.channel_config_json,
        publish=True,
    )


async def _run_cycle(
    db: AsyncSession,
    *,
    tenant_id: str,
    agent: Agent,
    focus: str,
    cycle_no: int,
    interactions_per_cycle: int,
    scenario_seed: str,
) -> tuple[TrainingCycleResponse, list[dict[str, Any]], AgentVersion | None, PersonaVersion | None]:
    agent_version = await get_published_agent_version_or_none(db, tenant_id, agent.id)
    if not agent_version:
        raise ValueError("Agent has no published version")
    if not agent_version.persona_id or agent_version.persona_version_no is None:
        raise ValueError("Agent has no linked persona version")

    persona = await get_persona_or_none(db, tenant_id, agent_version.persona_id)
    if not persona:
        raise ValueError("Linked persona not found")
    persona_version_result = await db.execute(
        select(PersonaVersion).where(
            PersonaVersion.tenant_id == tenant_id,
            PersonaVersion.persona_id == persona.id,
            PersonaVersion.version_no == agent_version.persona_version_no,
        )
    )
    persona_version = persona_version_result.scalar_one_or_none()
    if not persona_version:
        raise ValueError("Linked persona version not found")

    conversation = await create_lab_conversation(
        db,
        tenant_id=tenant_id,
        agent_id=agent.id,
        channel="lab",
        title=f"Treino {agent.name} - ciclo {cycle_no}",
    )
    history_results: list[dict[str, Any]] = []
    scenario_batches = _select_scenarios(focus, 1, interactions_per_cycle, f"{scenario_seed}:{cycle_no}")
    scenarios = scenario_batches[0]
    context_block = _build_context_block(persona, persona_version, agent, agent_version)
    score_buckets = {"grounding": [], "qualification": [], "next_step": [], "objection": [], "length": []}
    findings_counter: Counter[str] = Counter()

    for turn_no, scenario in enumerate(scenarios, start=1):
        history = await list_recent_conversation_messages(db, tenant_id, conversation.id)
        state = AgentState(
            tenant_id=tenant_id,
            agent_id=agent.id,
            lead_id=conversation.lead_id,
            conversation_id=conversation.id,
            channel="lab",
            message_text=scenario.message,
            conversation_history=[
                {
                    "role": "assistant" if message.sender_type == "assistant" else "user",
                    "content": message.content,
                }
                for message in history
            ],
        )
        state = await run_sales_agent(state)
        await persist_conversation_exchange(
            db=db,
            conversation=conversation,
            user_text=scenario.message,
            assistant_text=state.draft_reply,
            intent=state.intent,
            confidence_score=state.confidence_score,
            model_name="training-simulator",
            reply_fragments=state.reply_fragments,
            follow_up_suggestion=state.follow_up_suggestion,
        )
        await refresh_conversation_context_from_db(
            db,
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            last_intent=state.intent,
            media_notes=[],
        )
        evaluation = await judge_sales_reply(
            scenario_name=f"{focus}:{scenario.name}",
            user_message=scenario.message,
            assistant_reply=state.draft_reply,
            official_context=context_block,
        )
        reply_lower = state.draft_reply.lower()
        findings: list[str] = list(evaluation.get("weaknesses", []))
        if len(state.draft_reply.strip()) < 120:
            findings.append("Resposta curta demais para consolidar o primeiro atendimento.")
        if not state.follow_up_suggestion:
            findings.append("Resposta sem proximo passo sugerido.")
        if "mock-llm" in reply_lower:
            findings.append("Resposta ainda depende de modo mock.")

        score_buckets["grounding"].append(float(evaluation.get("grounding_score", 0)))
        score_buckets["qualification"].append(float(evaluation.get("qualification_score", 0)))
        score_buckets["next_step"].append(float(evaluation.get("next_step_score", 0)))
        score_buckets["objection"].append(float(evaluation.get("objection_score", 0)))
        score_buckets["length"].append(5.0 if len(state.draft_reply.strip()) >= 220 else 3.0 if len(state.draft_reply.strip()) >= 120 else 1.5)
        findings_counter.update(findings)
        history_results.append(
            {
                "cycle_no": cycle_no,
                "turn_no": turn_no,
                "scenario_name": scenario.name,
                "lead_message": scenario.message,
                "assistant_reply": state.draft_reply,
                "evaluation": evaluation,
                "findings": findings,
                "conversation_id": conversation.id,
            }
        )

    averages = {key: round(mean(values), 2) if values else 0.0 for key, values in score_buckets.items()}
    average_score = round(mean([averages["grounding"], averages["qualification"], averages["next_step"], averages["objection"]]), 2)
    recommendations = _score_to_recommendations(averages, focus)
    cycle_result = TrainingCycleResponse(
        cycle_no=cycle_no,
        average_score=average_score,
        total_turns=interactions_per_cycle,
        findings=[item for item, _count in findings_counter.most_common(8)],
        recommendations=recommendations,
        conversation_ids=[conversation.id],
    )
    return cycle_result, history_results, agent_version, persona_version


async def run_agent_training(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    agent_id: str,
    payload: AgentTrainingRequest,
) -> AgentTrainingResponse:
    agent = await get_agent_or_none(db, tenant_id, agent_id)
    if not agent:
        raise ValueError("Agent not found")
    run = await create_evaluation_run(
        db,
        tenant_id=tenant_id,
        product_id=None,
        created_by_user_id=user_id,
        evaluation_type="persona_training",
    )
    await mark_evaluation_started(db, run)

    try:
        cycles: list[TrainingCycleResponse] = []
        all_turns: list[dict[str, Any]] = []
        applied_persona_version_no: int | None = None
        applied_agent_version_no: int | None = None
        current_persona: BotPersona | None = None
        current_persona_version: PersonaVersion | None = None
        current_agent_version: AgentVersion | None = None

        for cycle_no in range(1, payload.cycles + 1):
            cycle_result, turns, current_agent_version, current_persona_version = await _run_cycle(
                db,
                tenant_id=tenant_id,
                agent=agent,
                focus=payload.focus,
                cycle_no=cycle_no,
                interactions_per_cycle=payload.interactions_per_cycle,
                scenario_seed=f"{run.id}:{cycle_no}",
            )
            cycles.append(cycle_result)
            all_turns.extend(turns)
            if current_agent_version and current_persona_version and payload.auto_apply and cycle_result.recommendations:
                current_persona = await get_persona_or_none(db, tenant_id, current_persona_version.persona_id)
                if current_persona:
                    persona_payload = _apply_persona_revision(
                        current_persona_version,
                        cycle_result.recommendations,
                        cycle_no,
                        payload.focus,
                    )
                    revised_persona = await create_persona_version(
                        db,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        persona=current_persona,
                        payload=persona_payload,
                    )
                    applied_persona_version_no = revised_persona.version_no

                    agent_payload = _apply_agent_revision(
                        current_agent_version,
                        persona_id=current_persona.id,
                        persona_version_no=revised_persona.version_no,
                        recommendations=cycle_result.recommendations,
                        cycle_no=cycle_no,
                        focus=payload.focus,
                    )
                    revised_agent = await create_agent_version(
                        db,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        agent=agent,
                        payload=agent_payload,
                    )
                    applied_agent_version_no = revised_agent.version_no
                    cycle_result = cycle_result.model_copy(
                        update={
                            "applied_persona_version_no": applied_persona_version_no,
                            "applied_agent_version_no": applied_agent_version_no,
                        }
                    )

        summary_json = {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "focus": payload.focus,
            "cycles": [cycle.model_dump() for cycle in cycles],
            "turns": len(all_turns),
            "applied_persona_version_no": applied_persona_version_no,
            "applied_agent_version_no": applied_agent_version_no,
        }
        report_lines = [
            "# Training Report",
            "",
            f"Agente: {agent.name}",
            f"Foco: {_focus_label(payload.focus)}",
            f"Ciclos: {payload.cycles}",
            f"Interacoes por ciclo: {payload.interactions_per_cycle}",
            f"Aplicar melhorias automaticamente: {'sim' if payload.auto_apply else 'nao'}",
            "",
            "| Ciclo | Score medio | Turnos | Recomendacoes |",
            "| --- | ---: | ---: | --- |",
        ]
        for cycle in cycles:
            report_lines.append(
                f"| {cycle.cycle_no} | {cycle.average_score:.2f} | {cycle.total_turns} | {len(cycle.recommendations)} |"
            )
        report_lines.extend(["", "## Recomendacoes", ""])
        all_recommendations = _merge_unique([], [item for cycle in cycles for item in cycle.recommendations])
        if all_recommendations:
            for item in all_recommendations:
                report_lines.append(f"- {item}")
        else:
            report_lines.append("- Nenhum ajuste critico identificado.")

        if applied_persona_version_no or applied_agent_version_no:
            report_lines.extend(["", "## Versoes publicadas", ""])
            if applied_persona_version_no:
                report_lines.append(f"- Persona publicada: v{applied_persona_version_no}")
            if applied_agent_version_no:
                report_lines.append(f"- Agente publicado: v{applied_agent_version_no}")

        report_lines.extend(["", "## Achados", ""])
        if all_turns:
            for turn in all_turns[:12]:
                report_lines.append(
                    f"- Ciclo {turn['cycle_no']} / {turn['scenario_name']}: {turn['assistant_reply'][:180].strip()}"
                )
        else:
            report_lines.append("- Nenhuma interacao executada.")

        report_markdown = "\n".join(report_lines)
        await mark_evaluation_finished(
            db,
            run,
            status="completed",
            summary_json=summary_json,
            report_markdown=report_markdown,
        )
        await db.refresh(run)
        return AgentTrainingResponse(
            evaluation_run=_evaluation_run_response(run),
            agent=await _agent_response(db, tenant_id, agent.id),
            persona=await _persona_response(db, tenant_id, current_persona_version.persona_id if current_persona_version else None),
            cycles=cycles,
            summary_json=summary_json,
            report_markdown=report_markdown,
        )
    except Exception as exc:
        await mark_evaluation_finished(db, run, status="failed", error_message=str(exc))
        raise


async def _agent_response(db: AsyncSession, tenant_id: str, agent_id: str) -> Any:
    agent = await get_agent_or_none(db, tenant_id, agent_id)
    if not agent:
        return None
    from app.schemas.agents import AgentResponse

    return AgentResponse.model_validate(agent)


async def _persona_response(db: AsyncSession, tenant_id: str, persona_id: str | None) -> Any:
    if not persona_id:
        return None
    persona = await get_persona_or_none(db, tenant_id, persona_id)
    if not persona:
        return None
    from app.schemas.personas import PersonaResponse

    return PersonaResponse.model_validate(persona)
