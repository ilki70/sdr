from __future__ import annotations

import asyncio

from app.services import knowledge


def test_extract_youtube_video_id_supports_common_formats() -> None:
    assert knowledge._extract_youtube_video_id("https://www.youtube.com/watch?v=abc123XYZ") == "abc123XYZ"
    assert knowledge._extract_youtube_video_id("https://youtu.be/def456UVW") == "def456UVW"
    assert knowledge._extract_youtube_video_id("https://www.youtube.com/shorts/ghi789RST") == "ghi789RST"
    assert knowledge._extract_youtube_video_id("https://www.youtube.com/embed/jkl012MNO") == "jkl012MNO"


def test_normalize_source_ref_adds_scheme_for_youtube_urls() -> None:
    assert knowledge._normalize_source_ref("www.youtube.com/watch?v=abc123XYZ") == "https://www.youtube.com/watch?v=abc123XYZ"
    assert knowledge._normalize_source_ref("youtube.com/watch?v=abc123XYZ") == "https://youtube.com/watch?v=abc123XYZ"


def test_extract_youtube_text_prefers_transcript_when_available(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {
                "title": "Titulo do video",
                "author_name": "Canal Exemplo",
            }

    class FakeClient:
        async def get(self, *args, **kwargs):  # noqa: ANN001, ANN002
            return FakeResponse()

    class FakeTranscript:
        def to_raw_data(self):
            return [
                {"text": "Primeira frase"},
                {"text": "Segunda frase"},
            ]

    class FakeYouTubeTranscriptApi:
        def fetch(self, video_id, languages=None):  # noqa: ANN001, ANN201
            assert video_id == "abc123XYZ"
            assert languages == knowledge.YOUTUBE_TRANSCRIPT_LANGUAGES
            return FakeTranscript()

    monkeypatch.setattr(knowledge, "YouTubeTranscriptApi", lambda: FakeYouTubeTranscriptApi())

    extracted = asyncio.run(
        knowledge._extract_youtube_text(FakeClient(), "https://www.youtube.com/watch?v=abc123XYZ")
    )

    assert extracted.source_type == "youtube_video"
    assert extracted.title == "Titulo do video"
    assert extracted.summary == "Primeira frase Segunda frase"
    assert "TRANSCRICAO: Primeira frase Segunda frase" in extracted.content
