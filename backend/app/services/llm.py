import logging
import json
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@lru_cache
def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)


def _extract_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif hasattr(item, "text") and isinstance(item.text, str):
                parts.append(item.text)
        return " ".join(parts).strip()
    return ""


async def _chat_completion(prompt: str) -> str:
    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Voce e um vendedor consultivo B2B. Responda em portugues do Brasil, "
                    "de forma objetiva, com foco em qualificacao e fechamento."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    if not response.choices:
        return "Nao consegui gerar resposta no momento."
    text = _extract_text(response.choices[0].message)
    return text or "Nao consegui gerar resposta no momento."


async def generate_sales_reply(prompt: str) -> str:
    if not settings.openai_api_key:
        return f"[mock-llm] {prompt[:240]}"
    try:
        return await _chat_completion(prompt)
    except OpenAIError as exc:
        logger.exception("openai_chat_failed", extra={"error": str(exc)})
        return "Falha temporaria no modelo de IA. Tente novamente em alguns segundos."


def _heuristic_judge(user_message: str, assistant_reply: str) -> dict[str, Any]:
    reply_lower = assistant_reply.lower()
    user_lower = user_message.lower()
    qualification = 5 if "?" in assistant_reply else 2
    next_step = 4 if any(term in reply_lower for term in ["adesao", "simul", "proposta", "proximo passo"]) else 2
    grounding = 4 if any(term in reply_lower for term in ["vinac", "banco central", "taxa", "parcela", "consorcio"]) else 2
    objection = 4 if any(term in user_lower for term in ["confi", "taxa", "juros", "seminov", "orçamento"]) and any(
        term in reply_lower for term in ["taxa", "banco central", "seminovo", "orcamento", "parcela"]
    ) else 2
    overall = round((qualification + next_step + grounding + objection) / 4, 2)
    return {
        "overall_score": overall,
        "grounding_score": grounding,
        "qualification_score": qualification,
        "next_step_score": next_step,
        "objection_score": objection,
        "passed": overall >= 3.5,
        "strengths": ["Avaliacao heuristica aplicada."],
        "weaknesses": ["Sem avaliacao LLM; revise manualmente se necessario."],
    }


async def judge_sales_reply(
    scenario_name: str,
    user_message: str,
    assistant_reply: str,
    official_context: str,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return _heuristic_judge(user_message, assistant_reply)

    client = _get_client()
    prompt = (
        "Avalie uma resposta de agente de vendas de consorcio em JSON puro. "
        "Considere notas de 1 a 5 para grounding factual, qualificacao, proximo passo e tratamento de objecao. "
        "Considere aprovado quando a media for >= 4. "
        f"Cenario={scenario_name}. "
        f"Mensagem do lead={user_message}. "
        f"Resposta do agente={assistant_reply}. "
        f"Contexto oficial={official_context}. "
        'Retorne JSON com chaves: overall_score, grounding_score, qualification_score, next_step_score, objection_score, passed, strengths, weaknesses.'
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "Voce e um avaliador rigoroso de agentes de vendas B2B. Responda apenas JSON valido.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = _extract_text(response.choices[0].message)
        return json.loads(content)
    except (OpenAIError, json.JSONDecodeError, IndexError, KeyError) as exc:
        logger.exception("openai_judge_failed", extra={"error": str(exc)})
        return _heuristic_judge(user_message, assistant_reply)


async def transcribe_audio_stub(file_ref: str) -> str:
    if not settings.openai_api_key:
        return f"transcription pending for {file_ref}"
    return f"Transcricao (stub) habilitada para {file_ref}."


async def analyze_image_stub(file_ref: str) -> str:
    if not settings.openai_api_key:
        return f"image analysis pending for {file_ref}"
    return f"Analise de imagem (stub) habilitada para {file_ref}."
