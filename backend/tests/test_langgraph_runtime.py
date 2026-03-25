from app.services.langgraph_runtime import LangGraphTurnRequest, run_message_through_langgraph


def _simulate_runtime_turns(turns: list[str]) -> list[object]:
    async def _run() -> list[object]:
        history: list[dict[str, str]] = []
        lead_name = None
        lead_phone = None
        lead_cpf = None
        lead_metadata: dict[str, object] = {}
        responses: list[object] = []
        for text in turns:
            response = await run_message_through_langgraph(
                LangGraphTurnRequest(
                    tenant_id="tenant-1",
                    conversation_id="conv-1",
                    message_text=text,
                    conversation_history=list(history),
                    lead_name=lead_name,
                    lead_phone=lead_phone,
                    lead_cpf=lead_cpf,
                    lead_metadata=dict(lead_metadata),
                )
            )
            responses.append(response)
            if response.slot_projection.get("lead_name"):
                lead_name = response.slot_projection["lead_name"]
            if response.slot_projection.get("phone"):
                lead_phone = response.slot_projection["phone"]
            if response.slot_projection.get("cpf"):
                lead_cpf = response.slot_projection["cpf"]
            lead_metadata["langgraph_slot_projection"] = dict(response.slot_projection)
            if response.runtime_metadata:
                lead_metadata["langgraph_runtime_state"] = dict(response.runtime_metadata)
            if response.flow_stage in {"proposal_in_progress", "simulation_delivery"}:
                lead_metadata["pipeline_status"] = "scheduled"
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": response.reply_text})
        return responses

    return __import__("asyncio").run(_run())


def test_langgraph_runtime_advances_without_reasking_name() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Oi",
                conversation_history=[
                    {"role": "assistant", "content": "Qual é o seu nome?"},
                    {"role": "user", "content": "Ilki Amaro"},
                    {"role": "assistant", "content": "Você está buscando imóvel ou veículo?"},
                ],
                lead_name="Ilki Amaro",
                lead_metadata={"langgraph_slot_projection": {"lead_name": "Ilki Amaro"}},
            )
        )
    )

    assert response.reply_fragments == ["Você está buscando imóvel ou veículo?"]
    assert response.slot_projection["lead_name"] == "Ilki Amaro"


def test_langgraph_runtime_requests_only_missing_profile_slot_after_qualification() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Quero um imóvel para morar de 500 mil em 180 meses",
                lead_name="Ilki Amaro",
                lead_phone="12988162249",
                lead_metadata={"langgraph_slot_projection": {"lead_name": "Ilki Amaro"}},
            )
        )
    )

    assert response.flow_stage == "qualification"
    assert response.reply_fragments[-1] == "Qual valor de parcela mensal faz sentido para você?"
    assert response.slot_projection["asset_value"].startswith("R$")
    assert response.slot_projection["timeline"] == "180 meses"


def test_langgraph_runtime_triggers_handoff_when_human_is_requested() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Quero falar com um consultor humano",
            )
        )
    )

    assert response.handoff_requested is True
    assert response.flow_stage == "handoff"


def test_langgraph_runtime_prefers_snapshot_current_question_slot() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Tudo bem?",
                lead_name="Ilki Amaro",
                conversation_context={
                    "tenant_id": "tenant-1",
                    "conversation_id": "conv-1",
                    "lead_name": "Ilki Amaro",
                    "asset_type": "imovel",
                    "goal": "moradia",
                    "asset_value": "R$ 500mil",
                    "timeline": "nao informado",
                    "lance": "nao informado",
                    "last_intent": "generic",
                    "current_question_slot": "timeline",
                    "last_confirmed_slot": "asset_value",
                    "extracted_slots": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                    },
                    "summary": "lead_name=Ilki Amaro; asset_type=imovel; goal=moradia; asset_value=R$ 500mil",
                    "media_summary": "sem midia",
                    "memory_notes": ["pergunta_atual=timeline"],
                    "turn_count": 4,
                },
            )
        )
    )

    assert response.flow_stage == "qualification"
    assert response.reply_fragments == ["Qual prazo faz sentido para você?"]


def test_langgraph_runtime_prefers_existing_missing_profile_fields() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="oi",
                lead_name="Ilki Amaro",
                lead_phone="12988162249",
                lead_metadata={
                    "required_profile_fields_missing": ["cpf"],
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "180 meses",
                        "budget_monthly": "R$ 3mil",
                    },
                },
            )
        )
    )

    assert response.flow_stage == "registration"
    assert response.reply_fragments == ["Antes de seguir com a simulação, preciso confirmar seu CPF."]


def test_langgraph_runtime_respects_existing_handoff_pipeline_status() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Queria saber se você viu minha mensagem",
                lead_metadata={"pipeline_status": "handoff"},
            )
        )
    )

    assert response.flow_stage == "handoff"
    assert response.handoff_requested is True


def test_langgraph_runtime_confirms_new_data_before_next_question() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Quero um imóvel",
                conversation_history=[{"role": "assistant", "content": "Você está buscando imóvel ou veículo?"}],
            )
        )
    )

    assert response.reply_fragments == ["Seu objetivo principal é morar, investir ou outro?"]


def test_langgraph_runtime_handles_objection_without_losing_flow() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Tenho receio da taxa, como isso funciona?",
                lead_metadata={
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                    }
                },
                conversation_context={
                    "tenant_id": "tenant-1",
                    "conversation_id": "conv-1",
                    "lead_name": "Ilki Amaro",
                    "asset_type": "imovel",
                    "asset_value": "nao informado",
                    "target_use_case": "nao informado",
                    "goal": "nao informado",
                    "timeline": "nao informado",
                    "lance": "nao informado",
                    "last_intent": "question",
                    "current_question_slot": "goal",
                    "last_confirmed_slot": "asset_type",
                    "extracted_slots": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                    },
                    "summary": "lead_name=Ilki Amaro; asset_type=imovel",
                    "media_summary": "sem midia",
                    "memory_notes": ["pergunta_atual=goal"],
                    "turn_count": 2,
                },
            )
        )
    )

    assert response.flow_stage == "objection_handling"
    assert "taxa" in response.reply_fragments[0].lower() or "custo" in response.reply_fragments[0].lower()
    assert response.reply_fragments[-1] == "Seu objetivo principal é morar, investir ou outro?"


def test_langgraph_runtime_uses_persona_tone_for_shorter_prompting() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Oi",
                metadata={
                    "policy_context": {
                        "persona_tone": "consultivo e objetivo",
                        "approach_rules": ["Faça perguntas curtas."],
                    }
                },
            )
        )
    )

    assert response.reply_fragments == ["Você busca imóvel ou veículo?"]


def test_langgraph_runtime_uses_persona_objection_playbook_when_available() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Tenho receio da taxa",
                metadata={
                    "policy_context": {
                        "objection_playbook": {
                            "taxa": "Explique o custo total com clareza e leve o lead para a proposta oficial.",
                        }
                    }
                },
                lead_metadata={"langgraph_slot_projection": {"asset_type": "imovel"}},
            )
        )
    )

    assert response.flow_stage == "objection_handling"
    assert "custo total" in response.reply_text


def test_langgraph_runtime_keeps_simulation_in_progress_without_restarting_flow() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Oi",
                lead_name="Ilki Amaro",
                lead_phone="12988162249",
                lead_cpf="002.752.307-16",
                lead_metadata={
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "180 meses",
                    }
                },
                conversation_history=[
                    {"role": "assistant", "content": "Perfeito. Com esses dados, eu sigo para a simulação."},
                ],
            )
        )
    )

    assert response.flow_stage == "proposal_in_progress"
    assert "simulação" in response.reply_fragments[0].lower() or "simulacao" in response.reply_fragments[0].lower()
    assert "reiniciar" in response.reply_fragments[-1].lower()


def test_langgraph_runtime_requests_only_missing_profile_field_during_simulation_progress() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="Tudo certo",
                lead_name="Ilki Amaro",
                lead_metadata={
                    "required_profile_fields_missing": ["cpf"],
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "180 meses",
                    },
                    "pipeline_status": "scheduled",
                },
            )
        )
    )

    assert response.flow_stage == "proposal_in_progress"
    assert response.reply_fragments[-1] == "Antes de seguir com a simulação, preciso confirmar seu CPF."


def test_langgraph_runtime_adjusts_simulation_to_max_installments_without_reasking_budget() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="quero o maximo de parcelas",
                lead_name="Ilki Amaro",
                lead_phone="12988162249",
                lead_cpf="002.752.307-16",
                lead_metadata={
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "1 ano",
                        "budget_monthly": "R$ 3mil",
                        "lance": "R$ 100mil",
                    },
                    "pipeline_status": "scheduled",
                },
            )
        )
    )

    assert response.flow_stage == "proposal_in_progress"
    assert "maior prazo possível" in response.reply_fragments[-1] or "maior prazo possivel" in response.reply_fragments[-1].lower()
    assert "R$ 3mil" in response.reply_fragments[-1]


def test_langgraph_runtime_stores_budget_monthly_when_prompted() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="3mil",
                conversation_history=[
                    {"role": "assistant", "content": "Qual valor de parcela mensal faz sentido para você?"},
                ],
            )
        )
    )

    assert response.slot_projection["budget_monthly"] == "R$ 3mil"


def test_langgraph_runtime_closes_conversation_after_negative_reply_to_help_offer() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="nao",
                conversation_history=[
                    {
                        "role": "assistant",
                        "content": "Vou enviar a simulação pelo WhatsApp. Gostaria de esclarecer alguma dúvida ou prefere que eu aguarde seu retorno?",
                    }
                ],
                lead_metadata={
                    "pipeline_status": "scheduled",
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "12 meses",
                        "budget_monthly": "R$ 4mil",
                    },
                },
            )
        )
    )

    assert response.flow_stage == "closing"
    assert "à disposição" in response.reply_fragments[0] or "disposição" in response.reply_fragments[0]


def test_langgraph_runtime_does_not_confirm_every_single_slot() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="500mil",
                conversation_history=[
                    {"role": "assistant", "content": "Qual é a faixa de valor do bem que você busca?"},
                ],
            )
        )
    )

    assert response.reply_fragments == ["Você está buscando imóvel ou veículo?"]


def test_langgraph_runtime_uses_known_phone_when_lead_points_to_previous_context() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="o q já passei",
                lead_name="Ilki Amaro",
                lead_phone="12988162249",
                lead_metadata={
                    "pipeline_status": "scheduled",
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "12 meses",
                        "budget_monthly": "R$ 4mil",
                        "preferred_delivery_channel": "whatsapp",
                    },
                    "langgraph_runtime_state": {
                        "current_topic": "simulation_delivery",
                        "conversation_mode": "delivering",
                        "last_agent_commitment": "send_simulation",
                    },
                },
                conversation_history=[
                    {"role": "assistant", "content": "Perfeito, vou enviar a simulação pelo WhatsApp para você. Pode me confirmar o número para envio?"},
                ],
            )
        )
    )

    assert response.flow_stage == "simulation_delivery"
    assert "12988162249" in response.reply_fragments[0]
    assert response.runtime_metadata["last_agent_commitment"] == "send_simulation"


def test_langgraph_runtime_marks_delivery_request_in_runtime_metadata() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="whatsapp",
                lead_name="Ilki Amaro",
                lead_phone="12988162249",
                lead_metadata={
                    "pipeline_status": "scheduled",
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "12 meses",
                    },
                    "langgraph_runtime_state": {
                        "last_agent_commitment": "prepare_simulation",
                    },
                },
                conversation_history=[
                    {"role": "assistant", "content": "Você prefere receber essa simulação por e-mail ou WhatsApp?"},
                ],
            )
        )
    )

    assert response.flow_stage == "simulation_delivery"
    assert "WhatsApp" in response.reply_fragments[0]
    assert response.runtime_metadata["current_topic"] == "simulation_delivery"
    assert response.runtime_metadata["conversation_mode"] == "delivering"


def test_langgraph_runtime_prefers_generic_conversation_runtime_state() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="oi",
                lead_metadata={
                    "conversation_runtime_state": {
                        "current_topic": "simulation_delivery",
                        "conversation_mode": "delivering",
                        "last_agent_commitment": "send_simulation",
                    },
                    "langgraph_slot_projection": {
                        "lead_name": "Ilki Amaro",
                        "asset_type": "imovel",
                        "goal": "moradia",
                        "asset_value": "R$ 500mil",
                        "timeline": "12 meses",
                        "budget_monthly": "R$ 4mil",
                        "phone": "12988162249",
                    },
                    "pipeline_status": "scheduled",
                },
            )
        )
    )

    assert response.flow_stage == "proposal_in_progress"
    assert "simulação" in response.reply_fragments[0].lower() or "simulacao" in response.reply_fragments[0].lower()


def test_langgraph_runtime_does_not_capture_non_name_phrases_as_lead_name() -> None:
    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="uso proprio",
                conversation_history=[
                    {"role": "assistant", "content": "Seu objetivo principal é morar, investir ou outro?"},
                ],
                lead_metadata={
                    "langgraph_slot_projection": {
                        "asset_type": "imovel",
                    }
                },
            )
        )
    )

    assert "lead_name" not in response.slot_projection
    assert response.slot_projection["goal"] == "moradia"


def test_langgraph_runtime_does_not_overwrite_asset_value_with_timeline_or_budget() -> None:
    responses = _simulate_runtime_turns(["oi", "imovel", "uso proprio", "500mil", "12 meses", "4mil"])

    assert responses[3].slot_projection["asset_value"] == "R$ 500mil"
    assert responses[4].slot_projection["asset_value"] == "R$ 500mil"
    assert responses[4].slot_projection["timeline"] == "12 meses"
    assert responses[5].slot_projection["asset_value"] == "R$ 500mil"
    assert responses[5].slot_projection["budget_monthly"] == "R$ 4mil"


def test_langgraph_runtime_moves_to_delivery_channel_after_simulation_confirmation() -> None:
    responses = _simulate_runtime_turns(
        ["oi", "imovel", "uso proprio", "500mil", "12 meses", "4mil", "Ilki Amaro", "00275230716", "12988162249", "sim"]
    )

    response = responses[-1]
    assert response.flow_stage == "simulation_delivery"
    assert response.reply_fragments == ["Perfeito. Você prefere receber a simulação por WhatsApp ou por e-mail?"]


def test_langgraph_runtime_closes_after_negative_reply_post_delivery_commitment() -> None:
    responses = _simulate_runtime_turns(
        [
            "oi",
            "imovel",
            "uso proprio",
            "500mil",
            "12 meses",
            "4mil",
            "Ilki Amaro",
            "00275230716",
            "12988162249",
            "sim",
            "whatsapp",
            "nao",
        ]
    )

    response = responses[-1]
    assert response.flow_stage == "closing"
    assert "retomar" in response.reply_fragments[0].lower()


def test_langgraph_runtime_preserves_goal_and_timeline_through_profile_and_lance_collection() -> None:
    responses = _simulate_runtime_turns(
        [
            "oi",
            "imovel",
            "uso",
            "até um ano",
            "500mil",
            "00275230716",
            "12988162249",
            "5mil",
            "tenho 100mil",
            "12 meses",
            "100mil",
        ]
    )

    assert responses[2].slot_projection["goal"] == "moradia"
    assert responses[3].slot_projection["timeline"] == "1 ano"
    assert responses[7].slot_projection["budget_monthly"] == "R$ 5mil"
    assert responses[8].slot_projection["lance"] == "R$ 100mil"
    assert responses[8].slot_projection["asset_value"] == "R$ 500mil"
    assert responses[9].slot_projection["timeline"] == "12 meses"
    assert responses[9].slot_projection["asset_value"] == "R$ 500mil"
    assert responses[10].slot_projection["goal"] == "moradia"
    assert responses[10].slot_projection["lance"] == "R$ 100mil"
    assert responses[10].slot_projection["asset_value"] == "R$ 500mil"
    assert "objetivo" not in " ".join(responses[10].reply_fragments).lower()


def test_langgraph_runtime_accepts_semantic_interpretation_for_compact_goal_reply(monkeypatch) -> None:
    async def _fake_interpretation(**kwargs):
        return {
            "slot_updates": {"goal": "moradia"},
            "speech_act": "inform",
        }

    monkeypatch.setattr("app.services.langgraph_runtime.interpret_turn_semantics", _fake_interpretation)

    response = __import__("asyncio").run(
        run_message_through_langgraph(
            LangGraphTurnRequest(
                tenant_id="tenant-1",
                conversation_id="conv-1",
                message_text="pra mim",
                conversation_history=[
                    {"role": "assistant", "content": "Seu objetivo principal é morar, investir ou outro?"},
                ],
                lead_metadata={
                    "langgraph_slot_projection": {
                        "asset_type": "imovel",
                    }
                },
            )
        )
    )

    assert response.slot_projection["goal"] == "moradia"
    assert response.reply_fragments == ["Qual é a faixa de valor do bem que você busca?"]
