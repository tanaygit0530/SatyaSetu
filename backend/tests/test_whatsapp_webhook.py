import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app.core.config import settings
from app.core.exceptions import InvalidInputException
from app.main import app
from app.schemas.core import ClaimVerificationResult, VerificationResult
from app.schemas.enums import ConfidenceLevel, Verdict
from app.schemas.evidence import LockedEvidenceItem
from app.services.whatsapp import WhatsAppWebhookService, whatsapp_webhook_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_webhook_cache():
    """Clear message deduplication cache before each test."""
    with whatsapp_webhook_service._lock:
        whatsapp_webhook_service._processed_messages.clear()


# ==============================================================================
# 1. Twilio Signature Validation Tests
# ==============================================================================

def test_signature_validation_allowed_when_valid(client):
    """Verifies that requests with a valid X-Twilio-Signature are accepted."""
    test_token = "valid_test_secret_token_123"
    validator = RequestValidator(test_token)
    webhook_url = "http://testserver/api/v1/whatsapp/webhook"
    form_params = {
        "MessageSid": "SM_sig_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "Is UPI shutting down tomorrow?",
    }
    signature = validator.compute_signature(webhook_url, form_params)

    with patch.object(settings, "TWILIO_AUTH_TOKEN", test_token), \
         patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", True):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data=form_params,
            headers={"X-Twilio-Signature": signature},
        )
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        assert "<Response>" in resp.text


def test_signature_validation_rejected_when_invalid(client):
    """Verifies that requests with an invalid X-Twilio-Signature are rejected with 403 Forbidden."""
    test_token = "valid_test_secret_token_123"
    form_params = {
        "MessageSid": "SM_sig_bad",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "Is UPI shutting down tomorrow?",
    }

    with patch.object(settings, "TWILIO_AUTH_TOKEN", test_token), \
         patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", True):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data=form_params,
            headers={"X-Twilio-Signature": "invalid_forged_signature"},
        )
        assert resp.status_code == 403
        assert "signature" in resp.json()["detail"].lower()


def test_signature_validation_missing_header_rejected(client):
    """Verifies that missing signature header is rejected when validation is enabled."""
    test_token = "valid_test_secret_token_123"
    form_params = {
        "MessageSid": "SM_sig_missing",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "Test message",
    }

    with patch.object(settings, "TWILIO_AUTH_TOKEN", test_token), \
         patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", True):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data=form_params,
        )
        assert resp.status_code == 403


# ==============================================================================
# 2. MessageSid Deduplication & Replay Attack Prevention Tests
# ==============================================================================

def test_deduplicate_messagesid_prevents_replay(client):
    """
    Verifies that duplicate MessageSid requests do NOT trigger the verification
    orchestrator a second time, preventing replay attacks and duplicate runs.
    """
    form_params = {
        "MessageSid": "SM_dedup_unique_999",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "UPI kal se band ho raha hai kya?",
    }

    mock_result = VerificationResult(
        check_id="chk_dedup_01",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="We found no official evidence announcing a nationwide UPI shutdown.",
                evidence=[
                    LockedEvidenceItem(
                        source_url="https://npci.org.in/press-releases/upi-update",
                        publisher="NPCI",
                        source_title="NPCI Official Bulletin",
                        exact_quote="UPI services operate uninterrupted without shutdown.",
                        source_text_reference="para-1",
                        source_tier=1,
                        retrieved_at="2026-10-08T10:00:00Z",
                        claim_relation="REFUTES",
                    )
                ],
                rule_trace=["TIER_1_SOURCE_PRESENT"],
                normalized_claim="UPI will be banned tomorrow.",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_result) as mock_verify:

        # 1. First execution
        resp1 = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp1.status_code == 200
        assert mock_verify.call_count == 1
        assert "🔴 FALSE" in resp1.text
        assert "NPCI — https://npci.org.in" in resp1.text

        # 2. Second execution (Replay attack with identical MessageSid)
        resp2 = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp2.status_code == 200
        # Verification orchestrator MUST NOT have been called again
        assert mock_verify.call_count == 1
        # Returns identical cached response
        assert resp2.text == resp1.text


# ==============================================================================
# 3. Text Message Verification Flow & Format Conformance
# ==============================================================================

def test_whatsapp_text_claim_verification_format(client):
    """
    Tests text message verification matching the user prompt's exact example:
    User sends: 'UPI kal se band ho raha hai kya?'
    Expected response:
    🔴 FALSE
    Claim: UPI will be banned tomorrow.
    Why: We found no official evidence announcing a nationwide UPI shutdown.
    Proof: NPCI — [source]
    View full evidence: https://sachcheck.in/checks/...
    """
    form_params = {
        "MessageSid": "SM_text_upi_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "UPI kal se band ho raha hai kya?",
    }

    mock_result = VerificationResult(
        check_id="chk_upi_999",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_001",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="We found no official evidence announcing a nationwide UPI shutdown.",
                evidence=[
                    LockedEvidenceItem(
                        source_url="https://npci.org.in/upi-clarification",
                        publisher="NPCI",
                        source_title="NPCI Press Release",
                        exact_quote="NPCI clarifies UPI remains fully functional nationwide.",
                        source_text_reference="p1",
                        source_tier=1,
                        retrieved_at="2026-10-08T10:00:00Z",
                        claim_relation="REFUTES",
                    )
                ],
                rule_trace=["TIER_1_SOURCE_PRESENT"],
                claim_text="UPI will be banned tomorrow.",
                normalized_claim="UPI will be banned tomorrow.",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_result) as mock_verify:

        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200
        content = resp.text

        # Verify orchestrator was invoked
        mock_verify.assert_called_once()
        call_kwargs = mock_verify.call_args[1]
        assert "UPI kal se band ho raha hai kya?" in call_kwargs["content"]
        assert call_kwargs["input_type"] == "WHATSAPP"

        # Verify response formatting conforms strictly to specification
        assert "🔴 FALSE" in content
        assert "Claim:\nUPI will be banned tomorrow." in content
        assert "Why:\nWe found no official evidence announcing a nationwide UPI shutdown." in content
        assert "Proof:\nNPCI — https://npci.org.in/upi-clarification" in content
        assert "View full evidence:" in content
        assert "https://sachcheck.in/checks/chk_" in content


# ==============================================================================
# 4. Image / Screenshot Media Ingestion Flow
# ==============================================================================

def test_whatsapp_image_media_handling(client):
    """
    Verifies that screenshot attachments trigger safe download, OCR ingestion,
    and routing to the SAME VerificationOrchestrator.
    """
    form_params = {
        "MessageSid": "SM_image_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "NumMedia": "1",
        "MediaUrl0": "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages/MM123/Media/ME001",
        "MediaContentType0": "image/jpeg",
        "Body": "Is this viral screenshot real?",
    }

    dummy_image_bytes = b"\xff\xd8\xff" + b"dummy_jpeg_bytes"

    mock_ocr_result = MagicMock()
    mock_ocr_result.extracted_text = "Reserve Bank of India cancels 500 rupee notes from tomorrow"

    mock_verif_result = VerificationResult(
        check_id="chk_img_001",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_img_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="RBI has issued no notification withdrawing 500 denomination currency.",
                evidence=[
                    LockedEvidenceItem(
                        source_url="https://rbi.org.in/currency-status",
                        publisher="RBI",
                        source_title="RBI Official Release",
                        exact_quote="500 rupee notes remain legal tender.",
                        source_text_reference="para-1",
                        source_tier=1,
                        retrieved_at="2026-10-08T10:00:00Z",
                        claim_relation="REFUTES",
                    )
                ],
                normalized_claim="RBI cancels 500 rupee notes from tomorrow.",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service, "download_media_safely", AsyncMock(return_value=dummy_image_bytes)), \
         patch.object(whatsapp_webhook_service.screenshot_service, "ingest_screenshot", return_value=mock_ocr_result), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_verif_result) as mock_verify:

        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200

        # Verify orchestrator received combined user query and OCR extracted text
        mock_verify.assert_called_once()
        verify_call_content = mock_verify.call_args[1]["content"]
        assert "Reserve Bank of India cancels 500 rupee notes" in verify_call_content
        assert "Is this viral screenshot real?" in verify_call_content

        assert "🔴 FALSE" in resp.text
        assert "RBI — https://rbi.org.in/currency-status" in resp.text


# ==============================================================================
# 5. Audio / Voice Media Ingestion Flow
# ==============================================================================

def test_whatsapp_voice_audio_handling(client):
    """
    Verifies that voice notes trigger safe download, STT transcription,
    and routing to the SAME VerificationOrchestrator.
    """
    form_params = {
        "MessageSid": "SM_voice_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "NumMedia": "1",
        "MediaUrl0": "https://api.twilio.com/audio/voice_note.ogg",
        "MediaContentType0": "audio/ogg",
    }

    dummy_audio_bytes = b"OggS" + b"dummy_opus_audio"

    mock_voice_result = MagicMock()
    mock_voice_result.transcript = "Old pension scheme will be implemented in all states from November."

    mock_verif_result = VerificationResult(
        check_id="chk_voice_001",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_voice_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="Central government has not issued any circular restoring OPS across states.",
                evidence=[],
                normalized_claim="Old pension scheme will be implemented in all states from November.",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service, "download_media_safely", AsyncMock(return_value=dummy_audio_bytes)), \
         patch.object(whatsapp_webhook_service.voice_service, "ingest_voice", return_value=mock_voice_result), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_verif_result) as mock_verify:

        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200

        mock_verify.assert_called_once()
        assert "Old pension scheme" in mock_verify.call_args[1]["content"]
        assert "🔴 FALSE" in resp.text


# ==============================================================================
# 6. PDF Media Ingestion Flow
# ==============================================================================

def test_whatsapp_pdf_document_handling(client):
    """
    Verifies that PDF attachments trigger safe download, PDF text extraction,
    and routing to the SAME VerificationOrchestrator.
    """
    form_params = {
        "MessageSid": "SM_pdf_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "NumMedia": "1",
        "MediaUrl0": "https://api.twilio.com/circular.pdf",
        "MediaContentType0": "application/pdf",
        "Body": "Is this gazette notification genuine?",
    }

    dummy_pdf_bytes = b"%PDF-1.4 dummy pdf"

    mock_pdf_result = MagicMock()
    mock_pdf_result.extracted_text = "Ministry of Finance official notification regarding tax exemptions."

    mock_verif_result = VerificationResult(
        check_id="chk_pdf_001",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_pdf_01",
                verdict=Verdict.VERIFIED,
                confidence=ConfidenceLevel.HIGH,
                explanation="Notification matches Gazette of India Order No. 2026-42.",
                evidence=[
                    LockedEvidenceItem(
                        source_url="https://egazette.gov.in/order-2026-42",
                        publisher="Gazette of India",
                        source_title="Notification 2026-42",
                        exact_quote="Tax exemption granted under Section 80C.",
                        source_text_reference="para-2",
                        source_tier=1,
                        retrieved_at="2026-10-08T10:00:00Z",
                        claim_relation="SUPPORTS",
                    )
                ],
                normalized_claim="Ministry of Finance granted tax exemptions in Notification 2026-42.",
            )
        ],
        overall_verdict=Verdict.VERIFIED,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service, "download_media_safely", AsyncMock(return_value=dummy_pdf_bytes)), \
         patch.object(whatsapp_webhook_service.pdf_service, "ingest_pdf", return_value=mock_pdf_result), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_verif_result) as mock_verify:

        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200

        mock_verify.assert_called_once()
        assert "Ministry of Finance" in mock_verify.call_args[1]["content"]
        assert "🟢 VERIFIED" in resp.text
        assert "Gazette of India — https://egazette.gov.in" in resp.text


# ==============================================================================
# 7. WhatsApp Response Format & Emoji Mappings for All Canonical Verdicts
# ==============================================================================

@pytest.mark.parametrize(
    "verdict,expected_emoji_header",
    [
        (Verdict.FALSE, "🔴 FALSE"),
        (Verdict.VERIFIED, "🟢 VERIFIED"),
        (Verdict.OUTDATED, "🟠 OUTDATED"),
        (Verdict.PARTLY_SUPPORTED, "🟡 PARTLY SUPPORTED"),
        (Verdict.CANNOT_BE_CONFIRMED, "⚪ CANNOT BE CONFIRMED"),
    ],
)
def test_whatsapp_emoji_and_verdict_headers(verdict, expected_emoji_header):
    """Verifies that all 5 canonical verdicts map to their assigned emoji headers."""
    mock_res = VerificationResult(
        check_id="chk_test_emoji",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_01",
                verdict=verdict,
                confidence=ConfidenceLevel.HIGH,
                explanation="Official fact check finding explanation.",
                evidence=[],
                normalized_claim="Sample claim statement under review.",
            )
        ],
        overall_verdict=verdict,
    )

    formatted = whatsapp_webhook_service.format_whatsapp_response(mock_res, "chk_test_emoji")
    assert formatted.verdict_emoji_header == expected_emoji_header
    assert expected_emoji_header in formatted.formatted_body
    assert "Claim:\nSample claim statement under review." in formatted.formatted_body
    assert "Why:\nOfficial fact check finding explanation." in formatted.formatted_body
    assert "View full evidence:" in formatted.formatted_body
    assert "https://sachcheck.in/checks/chk_test_emoji" in formatted.formatted_body


# ==============================================================================
# 8. Media Download Safety Boundaries
# ==============================================================================

@pytest.mark.asyncio
async def test_download_media_safely_rejects_unsafe_schemes():
    """Verifies that unsafe URL schemes (file://, ftp://) are rejected."""
    service = WhatsAppWebhookService()
    with pytest.raises(InvalidInputException, match="Only HTTPS permitted"):
        await service.download_media_safely("ftp://example.com/malicious.bin")


@pytest.mark.asyncio
async def test_download_media_safely_rejects_oversized_payload():
    """Verifies that payloads exceeding maximum allowed size are rejected."""
    service = WhatsAppWebhookService()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"x" * (1024 * 1024 * 30)  # 30MB

    mock_client = MagicMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(InvalidInputException, match="exceeds maximum limit"):
            await service.download_media_safely("https://api.twilio.com/file.bin", max_bytes=25 * 1024 * 1024)


# ==============================================================================
# 9. Empty Submission Handling
# ==============================================================================

def test_whatsapp_empty_submission(client):
    """Verifies that empty user submissions receive an informative guide prompt."""
    form_params = {
        "MessageSid": "SM_empty_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "",
        "NumMedia": "0",
    }

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False):
        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200
        assert "⚪ CANNOT BE CONFIRMED" in resp.text
        assert "Please forward a factual statement" in resp.text
