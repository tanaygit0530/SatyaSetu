import base64
import os
import tempfile
from typing import Optional
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.core import ClaimVerificationResult, VerificationResult
from app.schemas.enums import Verdict
from app.services.tts.base import TTSProvider, TTSResult
from app.services.tts.sarvam_provider import SarvamTTSProvider
from app.services.tts.service import TTSService
from app.services.verification_orchestrator import VerificationOrchestrator
from app.services.whatsapp import WhatsAppWebhookService


client = TestClient(app)


# Sample fake MP3 header bytes for mocking
SAMPLE_MP3_BYTES = b"\xff\xfb\x90\x44" + b"\x00" * 200
SAMPLE_B64_MP3 = base64.b64encode(SAMPLE_MP3_BYTES).decode("utf-8")


class MockSuccessTTSProvider(TTSProvider):
    """Mock provider simulating successful synthesis."""
    @property
    def provider_name(self) -> str:
        return "mock_sarvam"

    def is_configured(self) -> bool:
        return True

    def synthesize(self, text: str, language: str = "en", output_path: Optional[str] = None) -> TTSResult:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
            tf.write(SAMPLE_MP3_BYTES)
            temp_path = tf.name
        return TTSResult(
            success=True,
            audio_path=output_path or temp_path,
            audio_bytes=SAMPLE_MP3_BYTES,
            format="mp3",
            language=language,
            provider=self.provider_name,
            latency_ms=125.0,
        )


class MockFailingTTSProvider(TTSProvider):
    """Mock provider simulating an API failure or timeout."""
    @property
    def provider_name(self) -> str:
        return "mock_sarvam_failing"

    def is_configured(self) -> bool:
        return True

    def synthesize(self, text: str, language: str = "en", output_path: Optional[str] = None) -> TTSResult:
        return TTSResult(
            success=False,
            error="Connection to Sarvam TTS timed out (HTTP 504 Gateway Timeout)",
            language=language,
            provider=self.provider_name,
            latency_ms=3000.0,
        )


@pytest.fixture
def clean_metrics_repo():
    repo = MetricsRepository()
    repo._local_metrics.clear()
    return repo


# ==============================================================================
# 1. SARVAM TTS PROVIDER TESTS
# ==============================================================================

def test_sarvam_provider_unconfigured_returns_graceful_failure():
    """When Sarvam API key is not configured, provider returns success=False without crashing."""
    provider = SarvamTTSProvider(api_key="")
    res = provider.synthesize(text="UPI is banned.", language="en")
    assert res.success is False
    assert "not configured" in res.error.lower()
    assert res.audio_path is None


def test_sarvam_provider_supports_english_hindi_marathi():
    """Verifies that SarvamTTSProvider accepts English, Hindi, and Marathi."""
    provider = SarvamTTSProvider(api_key="test_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"audios": [SAMPLE_B64_MP3]}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        # 1. English
        res_en = provider.synthesize("This claim is not supported.", language="en")
        assert res_en.success is True
        call_en = mock_post.call_args[1]["json"]
        assert call_en["target_language_code"] == "en-IN"

        # 2. Hindi
        res_hi = provider.synthesize("यह दावा सही नहीं है।", language="hi")
        assert res_hi.success is True
        call_hi = mock_post.call_args[1]["json"]
        assert call_hi["target_language_code"] == "hi-IN"

        # 3. Marathi
        res_mr = provider.synthesize("हा दावा योग्य नाही.", language="mr")
        assert res_mr.success is True
        call_mr = mock_post.call_args[1]["json"]
        assert call_mr["target_language_code"] == "mr-IN"


def test_sarvam_provider_handles_http_errors_gracefully():
    """HTTP 500 error from Sarvam produces a clean failure result, not an exception."""
    provider = SarvamTTSProvider(api_key="test_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error in Audio Encoder"

    with patch("httpx.Client.post", return_value=mock_resp):
        res = provider.synthesize("Test explanation text.", language="hi")
        assert res.success is False
        assert "500" in res.error
        assert res.audio_path is None


# ==============================================================================
# 2. TELEMETRY & METRIC TRACKING (tts_success, tts_failure, language, latency)
# ==============================================================================

def test_telemetry_tracking_on_tts_success(clean_metrics_repo):
    """Verifies that tts_success, language, and latency are recorded in metrics on success."""
    service = TTSService(
        provider=MockSuccessTTSProvider(),
        metrics_repo=clean_metrics_repo,
    )

    res = service.synthesize_explanation(
        explanation="यह दावा सही नहीं है।",
        language="hi",
    )
    assert res.success is True
    assert res.audio_path is not None

    # Check metrics
    succ_metrics = clean_metrics_repo.get_metrics("tts_success")
    assert len(succ_metrics) >= 1
    assert succ_metrics[-1].value == 1.0
    assert succ_metrics[-1].dimensions.get("language") == "hi"

    lat_metrics = clean_metrics_repo.get_metrics("latency")
    assert len(lat_metrics) >= 1
    assert lat_metrics[-1].dimensions.get("operation") == "tts"
    assert lat_metrics[-1].dimensions.get("language") == "hi"
    assert lat_metrics[-1].value > 0.0


def test_telemetry_tracking_on_tts_failure(clean_metrics_repo):
    """Verifies that tts_failure, language, and latency are recorded in metrics on failure."""
    service = TTSService(
        provider=MockFailingTTSProvider(),
        metrics_repo=clean_metrics_repo,
    )

    res = service.synthesize_explanation(
        explanation="हा दावा योग्य नाही.",
        language="mr",
    )
    assert res.success is False
    assert res.error is not None

    # Check metrics
    fail_metrics = clean_metrics_repo.get_metrics("tts_failure")
    assert len(fail_metrics) >= 1
    assert fail_metrics[-1].value == 1.0
    assert fail_metrics[-1].dimensions.get("language") == "mr"
    assert "timed out" in fail_metrics[-1].dimensions.get("error", "")

    lat_metrics = clean_metrics_repo.get_metrics("latency")
    assert len(lat_metrics) >= 1
    assert lat_metrics[-1].dimensions.get("status") == "failed"


# ==============================================================================
# 3. VERIFICATION INDEPENDENCE: VOICE OUTPUT IS NOT A HARD DEPENDENCY
# ==============================================================================

def test_verification_succeeds_and_attaches_voice_when_tts_succeeds(clean_metrics_repo):
    """
    Verification succeeds
    ↓
    text explanation generated
    ↓
    TTS succeeds
    ↓
    send text + voice
    """
    tts = TTSService(provider=MockSuccessTTSProvider(), metrics_repo=clean_metrics_repo)
    orchestrator = VerificationOrchestrator(tts_service_instance=tts)

    result = orchestrator.verify(
        content="UPI will be banned from tomorrow.",
        generate_voice=True,
    )
    assert result.overall_verdict is not None
    assert len(result.claims) > 0
    # Text explanation is present
    assert result.claims[0].explanation != ""
    # TTS succeeded -> audio attached
    assert result.tts_success is True
    assert result.audio_file is not None
    assert os.path.exists(result.audio_file)


def test_verification_succeeds_and_keeps_text_only_when_tts_fails(clean_metrics_repo):
    """
    Verification succeeds
    ↓
    text explanation generated
    ↓
    TTS fails
    ↓
    send text only (never crashes verification)
    """
    tts = TTSService(provider=MockFailingTTSProvider(), metrics_repo=clean_metrics_repo)
    orchestrator = VerificationOrchestrator(tts_service_instance=tts)

    result = orchestrator.verify(
        content="UPI will be banned from tomorrow.",
        generate_voice=True,
    )
    # Verification succeeded despite TTS failure
    assert result.overall_verdict is not None
    assert len(result.claims) > 0
    # Text explanation generated intact
    assert result.claims[0].explanation != ""
    # TTS failed -> voice is not attached, text only
    assert result.tts_success is False
    assert result.audio_file is None


# ==============================================================================
# 4. WHATSAPP WEBHOOK: TEXT ONLY ON TTS FAILURE, TEXT + VOICE ON SUCCESS
# ==============================================================================

def test_whatsapp_webhook_sends_text_plus_voice_when_tts_succeeds():
    """WhatsApp response includes TwiML <Media> voice audio when TTS succeeds."""
    mock_tts = TTSService(provider=MockSuccessTTSProvider())
    webhook_service = WhatsAppWebhookService(tts_service_instance=mock_tts)

    verification_result = VerificationResult(
        check_id="chk_tts_001",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_1",
                verdict=Verdict.FALSE,
                confidence="HIGH",
                explanation="This claim is not supported by reliable evidence.",
                language="en",
            )
        ],
    )

    formatted = webhook_service.format_whatsapp_response(
        result=verification_result,
        check_id="chk_tts_001",
        include_voice=True,
    )
    assert formatted.has_voice is True
    assert formatted.voice_path is not None
    assert formatted.voice_url is not None

    # TwiML contains both text message and media audio URL
    twiml = webhook_service.build_twiml_response(formatted.formatted_body, media_url=formatted.voice_url)
    assert "<Media>" in twiml
    assert "<Message>" in twiml
    assert "🔴 FALSE" in twiml


def test_whatsapp_webhook_sends_text_only_when_tts_fails():
    """WhatsApp response contains text body only (no <Media>) when TTS fails."""
    mock_tts = TTSService(provider=MockFailingTTSProvider())
    webhook_service = WhatsAppWebhookService(tts_service_instance=mock_tts)

    verification_result = VerificationResult(
        check_id="chk_tts_002",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_2",
                verdict=Verdict.FALSE,
                confidence="HIGH",
                explanation="This claim is not supported by reliable evidence.",
                language="en",
            )
        ],
    )

    formatted = webhook_service.format_whatsapp_response(
        result=verification_result,
        check_id="chk_tts_002",
        include_voice=True,
    )
    assert formatted.has_voice is False
    assert formatted.voice_url is None

    # TwiML contains text only
    twiml = webhook_service.build_twiml_response(formatted.formatted_body, media_url=None)
    assert "<Media>" not in twiml
    assert "<Message>" in twiml
    assert "🔴 FALSE" in twiml


# ==============================================================================
# 5. FASTAPI /api/v1/tts/synthesize ENDPOINT
# ==============================================================================

def test_api_tts_synthesize_endpoint_with_mock():
    """Tests the /api/v1/tts/synthesize REST endpoint."""
    with patch("app.services.tts.service.tts_service.provider", MockSuccessTTSProvider()):
        resp = client.post(
            "/api/v1/tts/synthesize",
            json={
                "explanation": "यह दावा सही नहीं है। हमें कोई आधिकारिक प्रमाण नहीं मिला।",
                "language": "hi",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["language"] == "hi"
        assert data["format"] == "mp3"
        assert data["audio_path"] is not None
