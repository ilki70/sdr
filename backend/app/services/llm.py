import logging
import json
import base64
import io
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from pypdf import PdfReader

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


async def transcribe_audio_bytes(
    file_bytes: bytes,
    mime_type: str = "audio/ogg",
    file_name: str = "audio-message.ogg",
    prompt: str | None = None,
) -> str:
    if not file_bytes:
        return ""
    if not settings.openai_api_key:
        return f"Transcricao pendente para {file_name}."
    try:
        client = _get_client()
        response = await client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(file_name, file_bytes, mime_type),
            response_format="text",
            language="pt",
            prompt=prompt or "Contexto comercial de consorcio de carros no Brasil. Termos frequentes: VINAC, consorcio, carta de credito, parcela, proposta, Corolla Cross, seminovo, adesao.",
            temperature=0,
        )
        if isinstance(response, str):
            return response.strip()
        if hasattr(response, "text") and isinstance(response.text, str):
            return response.text.strip()
        return ""
    except OpenAIError as exc:
        logger.exception("openai_audio_transcription_failed", extra={"error": str(exc)})
        return ""


async def analyze_image_bytes(
    file_bytes: bytes,
    mime_type: str = "image/jpeg",
    prompt: str | None = None,
) -> str:
    if not file_bytes:
        return ""
    if not settings.openai_api_key:
        return "Analise de imagem pendente."
    try:
        client = _get_client()
        data_url = f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode('utf-8')}"
        response = await client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                            or (
                                "Descreva a imagem em portugues do Brasil com foco no que ajuda um vendedor. "
                                "Extraia produto, modelo, ano, faixa de valor aparente, documento ou informacao comercial visivel. "
                                "Se nao der para afirmar algo, diga explicitamente."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url,
                        },
                    ],
                }
            ],
            temperature=0.2,
        )
        output_text = getattr(response, "output_text", "")
        return output_text.strip() if isinstance(output_text, str) else ""
    except OpenAIError as exc:
        logger.exception("openai_image_analysis_failed", extra={"error": str(exc)})
        return ""


def _extract_pdf_text(file_bytes: bytes) -> str:
    pages: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages[:12]:
            extracted = (page.extract_text() or "").strip()
            if extracted:
                pages.append(extracted)
    except Exception:
        return ""
    return "\n".join(pages).strip()


async def analyze_document_bytes(
    file_bytes: bytes,
    mime_type: str = "application/pdf",
    file_name: str = "documento.pdf",
) -> str:
    if not file_bytes:
        return ""

    if mime_type.startswith("image/"):
        return await analyze_image_bytes(
            file_bytes,
            mime_type=mime_type,
            prompt=(
                "Leia esta imagem de documento em portugues do Brasil. "
                "Extraia tipo de documento, valores, parcelas, datas, nome do cliente, produto e qualquer proximo passo comercial visivel. "
                "Nao invente campos nao visiveis."
            ),
        )

    extracted_text = ""
    if "pdf" in mime_type or file_name.lower().endswith(".pdf"):
        extracted_text = _extract_pdf_text(file_bytes)
    elif mime_type.startswith("text/") or file_name.lower().endswith((".txt", ".md")):
        extracted_text = file_bytes.decode("utf-8", errors="ignore").strip()

    if not extracted_text:
        return ""

    if not settings.openai_api_key:
        return extracted_text[:1200]

    try:
        client = _get_client()
        response = await client.responses.create(
            model=settings.openai_model,
            input=(
                "Leia o texto extraido de um documento comercial e produza um resumo guiado em portugues do Brasil. "
                "Extraia, se existirem: tipo de documento, nome do cliente, produto, credito, valor total, valor de parcela, vencimento, taxa, observacoes e proximo passo. "
                "Se alguma informacao nao estiver presente, diga isso explicitamente.\n\n"
                f"Arquivo: {file_name}\n"
                f"Texto extraido:\n{extracted_text[:12000]}"
            ),
            temperature=0.1,
        )
        output_text = getattr(response, "output_text", "")
        return output_text.strip() if isinstance(output_text, str) else extracted_text[:1200]
    except OpenAIError as exc:
        logger.exception("openai_document_analysis_failed", extra={"error": str(exc)})
        return extracted_text[:1200]
