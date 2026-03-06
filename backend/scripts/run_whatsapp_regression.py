import asyncio
import base64
import json
import subprocess
import tempfile
import urllib.request
import unicodedata
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = PROJECT_ROOT / "services" / "whatsapp-gateway" / "data" / "runtime.json"
BACKEND_URL = "http://127.0.0.1:8000/api/v1/whatsapp/inbound"
GATEWAY_SECRET = "whatsapp-gateway-local"


def load_runtime_config() -> dict[str, str]:
    return json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))


def call_inbound(payload: dict) -> dict:
    request = urllib.request.Request(
        BACKEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-WhatsApp-Gateway-Secret": GATEWAY_SECRET,
        },
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode("utf-8"))


def create_demo_image(target: Path) -> None:
    command = (
        "Add-Type -AssemblyName System.Drawing; "
        "$bmp = New-Object System.Drawing.Bitmap 900,500; "
        "$g = [System.Drawing.Graphics]::FromImage($bmp); "
        "$g.Clear([System.Drawing.Color]::White); "
        "$font1 = New-Object System.Drawing.Font('Arial',20,[System.Drawing.FontStyle]::Bold); "
        "$font2 = New-Object System.Drawing.Font('Arial',16); "
        "$brush = [System.Drawing.Brushes]::Black; "
        "$g.DrawString('Proposta VINAC - Carta de Credito R$ 145.000', $font1, $brush, 20, 30); "
        "$g.DrawString('Cliente: Maria Silva', $font2, $brush, 20, 100); "
        "$g.DrawString('Parcela estimada: R$ 1.950', $font2, $brush, 20, 135); "
        "$g.DrawString('Produto: Corolla Cross 2022', $font2, $brush, 20, 170); "
        "$bmp.Save('" + str(target) + "',[System.Drawing.Imaging.ImageFormat]::Png); "
        "$g.Dispose(); $bmp.Dispose();"
    )
    subprocess.run(["powershell", "-Command", command], check=True)


def create_demo_audio(target: Path) -> None:
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$synth.SetOutputToWaveFile('" + str(target) + "'); "
        "$synth.Speak('Oi, eu quero entender se consigo entrar em um consorcio para um Corolla Cross 2022 com parcela perto de mil e novecentos e cinquenta reais.'); "
        "$synth.Dispose();"
    )
    subprocess.run(["powershell", "-Command", command], check=True)


def download_vinac_pdf(target: Path) -> None:
    request = urllib.request.Request(
        "https://vinac.com.br/downloads/vinac-consorcios-tabela-impressao.pdf",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        target.write_bytes(response.read())


def build_payload(runtime: dict[str, str], chat_suffix: str, message_id: str, **extra: str) -> dict:
    sender = f"551199999{chat_suffix}@s.whatsapp.net"
    payload = {
        "tenant_id": runtime["tenant_id"],
        "integration_id": runtime["integration_id"],
        "chat_id": sender,
        "sender_id": sender,
        "sender_name": f"Regression {chat_suffix}",
        "message_id": message_id,
        "message_text": "",
        "message_type": "text",
    }
    payload.update(extra)
    return payload


def read_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def assert_case(name: str, response: dict, required_terms: list[str]) -> dict:
    reply = response.get("reply_text", "")
    fragments = response.get("reply_fragments") or []
    folded_reply = "".join(
        char for char in unicodedata.normalize("NFKD", reply.lower()) if not unicodedata.combining(char)
    )
    passed = all(
        "".join(char for char in unicodedata.normalize("NFKD", term.lower()) if not unicodedata.combining(char)) in folded_reply
        for term in required_terms
    ) and len(fragments) >= 2
    return {
        "name": name,
        "passed": passed,
        "reply": reply,
        "fragment_count": len(fragments),
        "required_terms": required_terms,
    }


async def main() -> None:
    runtime = load_runtime_config()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        image_path = temp_path / "whatsapp-image.png"
        audio_path = temp_path / "whatsapp-audio.wav"
        pdf_path = temp_path / "vinac.pdf"

        create_demo_image(image_path)
        create_demo_audio(audio_path)
        download_vinac_pdf(pdf_path)

        results = []

        nonce = uuid4().hex[:8]

        text_response = call_inbound(
            build_payload(
                runtime,
                "0200",
                f"wa-reg-text-{nonce}",
                message_text="Quero saber se consigo um Corolla Cross 2022 com parcela de 1950 reais. Me explica de um jeito simples.",
                message_type="text",
            )
        )
        results.append(assert_case("text", text_response, ["Corolla Cross", "R$ 1.950"]))

        audio_response = call_inbound(
            build_payload(
                runtime,
                "0201",
                f"wa-reg-audio-{nonce}",
                message_type="audio",
                media_kind="audio",
                media_mime_type="audio/wav",
                media_filename="whatsapp-audio.wav",
                media_base64=read_base64(audio_path),
            )
        )
        results.append(assert_case("audio", audio_response, ["Corolla Cross", "parcela"]))

        image_response = call_inbound(
            build_payload(
                runtime,
                "0202",
                f"wa-reg-image-{nonce}",
                message_type="image",
                media_kind="image",
                media_mime_type="image/png",
                media_filename="whatsapp-image.png",
                media_caption="segue a proposta que recebi",
                media_base64=read_base64(image_path),
            )
        )
        results.append(assert_case("image", image_response, ["Corolla Cross", "R$ 1.950"]))

        pdf_response = call_inbound(
            build_payload(
                runtime,
                "0203",
                f"wa-reg-pdf-{nonce}",
                message_type="document",
                media_kind="document",
                media_mime_type="application/pdf",
                media_filename="vinac.pdf",
                media_caption="me ajuda a entender essa tabela",
                media_base64=read_base64(pdf_path),
            )
        )
        results.append(assert_case("pdf", pdf_response, ["credito", "parcela"]))

        passed = sum(1 for item in results if item["passed"])
        print(json.dumps({"passed": passed, "total": len(results), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
