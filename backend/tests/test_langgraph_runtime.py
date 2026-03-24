from app.services.langgraph_runtime import LangGraphTurnRequest, run_message_through_langgraph


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

    assert response.flow_stage == "registration"
    assert response.reply_fragments == ["Antes de seguir com a simulação, preciso confirmar seu CPF."]
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

    assert response.reply_fragments[0] == "Perfeito, anotei bem: imovel."
    assert response.reply_fragments[1] == "Seu objetivo principal é morar, investir ou outro?"


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
