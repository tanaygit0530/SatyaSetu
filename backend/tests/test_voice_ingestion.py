import io
import wave
from unittest.mock import patch
import httpx
import pytest

from app.core.exceptions import InvalidInputException
from app.main import app
from app.schemas.ingestion import VoiceIngestionResult
from app.services.stt.base import STTProvider, STTRawResult
from app.services.voice_ingestion import (
    VoiceIngestionService,
    voice_ingestion_service,
)


def create_test_wav(duration_seconds: float = 2.0, framerate: int = 8000) -> bytes:
    """Generates valid WAV audio bytes in-memory for testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        num_frames = int(duration_seconds * framerate)
        w.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


class MockTestSTTProvider(STTProvider):
    """Configurable mock STT provider for deterministic testing."""

    def __init__(
        self,
        transcript: str = "",
        language: str = "en",
        confidence: float = 0.90,
        is_uncertain: bool = False,
        should_raise: bool = False,
    ):
        self._transcript = transcript
        self._language = language
        self._confidence = confidence
        self._is_uncertain = is_uncertain
        self._should_raise = should_raise
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "sarvam"

    def transcribe(self, audio_path: str, language_hint: str = None) -> STTRawResult:
        self.call_count += 1
        if self._should_raise:
            raise RuntimeError("Provider connection failed")
        return STTRawResult(
            transcript=self._transcript,
            language=self._language,
            confidence=self._confidence,
            provider=self.provider_name,
            is_uncertain=self._is_uncertain,
        )


# ==============================================================================
# 1. Hindi Voice Note Test (Specification Example)
# ==============================================================================

def test_hindi_voice_ingestion_specification_example():
    """
    Validates exact example from specification:
    Voice: "सरकार ने कल से UPI बंद कर दिया है"
    Return:
      language: "hi"
      transcript: "सरकार ने कल से UPI बंद कर दिया है"
      confidence: 0.94
      needs_confirmation: False
    """
    audio_wav = create_test_wav(duration_seconds=3.5)
    mock_provider = MockTestSTTProvider(
        transcript="सरकार ने कल से UPI बंद कर दिया है",
        language="hi",
        confidence=0.94,
        is_uncertain=False,
    )

    service = VoiceIngestionService(provider=mock_provider)
    result = service.ingest_voice(audio_wav, language_hint="hi")

    assert result.language == "hi"
    assert result.transcript == "सरकार ने कल से UPI बंद कर दिया है"
    assert result.confidence == 0.94
    assert result.needs_confirmation is False
    assert result.provider == "sarvam"


# ==============================================================================
# 2. English Voice Note Test
# ==============================================================================

def test_english_voice_ingestion():
    """Validates English voice note ingestion."""
    audio_wav = create_test_wav(duration_seconds=4.0)
    mock_provider = MockTestSTTProvider(
        transcript="The government has officially announced scheme X for college students.",
        language="en",
        confidence=0.96,
    )

    service = VoiceIngestionService(provider=mock_provider)
    result = service.ingest_voice(audio_wav, language_hint="en")

    assert result.language == "en"
    assert "scheme X" in result.transcript
    assert result.confidence == 0.96
    assert result.needs_confirmation is False


# ==============================================================================
# 3. Marathi Voice Note Test
# ==============================================================================

def test_marathi_voice_ingestion():
    """Validates Marathi vernacular voice note ingestion."""
    audio_wav = create_test_wav(duration_seconds=5.0)
    mock_provider = MockTestSTTProvider(
        transcript="शासनाने नवीन शिष्यवृत्ती योजना जाहीर केली आहे.",
        language="mr",
        confidence=0.91,
    )

    service = VoiceIngestionService(provider=mock_provider)
    result = service.ingest_voice(audio_wav, language_hint="mr")

    assert result.language == "mr"
    assert "शिष्यवृत्ती" in result.transcript
    assert result.confidence == 0.91
    assert result.needs_confirmation is False


# ==============================================================================
# 4. Noisy Audio & Uncertainty Test
# ==============================================================================

def test_noisy_audio_marks_needs_confirmation():
    """
    Validates noisy audio:
    - Audio has low confidence (0.42 < 0.65 threshold) or is_uncertain flag is True.
    - Result marks needs_confirmation = True.
    - Never silently treats uncertain speech as accurate.
    """
    audio_wav = create_test_wav(duration_seconds=3.0)
    mock_provider = MockTestSTTProvider(
        transcript="garbled ... noise ... payment ...",
        language="hi",
        confidence=0.42,
        is_uncertain=True,
    )

    service = VoiceIngestionService(provider=mock_provider, confidence_threshold=0.65)
    result = service.ingest_voice(audio_wav)

    assert result.needs_confirmation is True
    assert result.confidence < 0.65


# ==============================================================================
# 5. Audio > 60 Seconds Exceeds Limit Test
# ==============================================================================

def test_audio_exceeding_60_seconds_rejected():
    """
    Validates MVP constraint: audio longer than 60 seconds is rejected.
    """
    long_audio = create_test_wav(duration_seconds=61.5)

    with pytest.raises(InvalidInputException) as exc_info:
        voice_ingestion_service.ingest_voice(long_audio)

    assert "exceeds the maximum limit of 60 seconds" in str(exc_info.value)


# ==============================================================================
# 6. Unsupported Audio Format Test
# ==============================================================================

@pytest.mark.parametrize(
    "bad_bytes,desc",
    [
        (b"%PDF-1.4 file", "PDF document"),
        (b"\x89PNG\r\n\x1a\n image", "PNG image"),
        (b"Random plain text message", "Text file"),
    ],
)
def test_unsupported_audio_formats_rejected(bad_bytes, desc):
    """Ensures non-audio payloads are rejected by MIME magic bytes validation."""
    with pytest.raises(InvalidInputException) as exc_info:
        voice_ingestion_service.ingest_voice(bad_bytes)
    assert "Unsupported audio format" in str(exc_info.value)


# ==============================================================================
# 7. Never Invent Missing Speech & Graceful Degradation
# ==============================================================================

def test_silent_audio_never_invents_missing_speech():
    """
    Ensures silent/empty speech returns empty transcript with needs_confirmation = True.
    """
    audio_wav = create_test_wav(duration_seconds=2.0)
    mock_provider = MockTestSTTProvider(transcript="", language="hi", confidence=0.0)

    service = VoiceIngestionService(provider=mock_provider)
    result = service.ingest_voice(audio_wav)

    assert result.transcript == ""
    assert result.needs_confirmation is True


def test_provider_failure_returns_graceful_degradation():
    """
    Ensures provider crashes degrade gracefully without throwing an unhandled 500 error.
    """
    audio_wav = create_test_wav(duration_seconds=2.0)
    crashing_provider = MockTestSTTProvider(should_raise=True)

    service = VoiceIngestionService(provider=crashing_provider)
    result = service.ingest_voice(audio_wav)

    assert result.transcript == ""
    assert result.confidence == 0.0
    assert result.needs_confirmation is True


# ==============================================================================
# 8. API Route Integration Test
# ==============================================================================

@pytest.mark.asyncio
async def test_api_voice_ingest_endpoint_success():
    """Tests POST /api/v1/ingest/voice via HTTP multipart upload."""
    wav_bytes = create_test_wav(duration_seconds=2.5)
    mock_stt = MockTestSTTProvider(
        transcript="सरकार ने कल से UPI बंद कर दिया है",
        language="hi",
        confidence=0.95,
    )

    with patch("app.services.voice_ingestion.voice_ingestion_service.provider", mock_stt):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("voicenote.wav", wav_bytes, "audio/wav")}
            data = {"language_hint": "hi"}
            response = await client.post("/api/v1/ingest/voice", files=files, data=data)

            assert response.status_code == 200
            res = response.json()
            assert res["language"] == "hi"
            assert res["transcript"] == "सरकार ने कल से UPI बंद कर दिया है"
            assert res["confidence"] == 0.95
            assert res["needs_confirmation"] is False
