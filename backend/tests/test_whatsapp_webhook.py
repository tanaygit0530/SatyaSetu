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
from app.schemas.whatsapp import WhatsAppIncomingMessage
from app.jobs import job_manager
from app.services.whatsapp import WhatsAppWebhookService, whatsapp_webhook_service


@pytest.fixture
def client():
    return TestClient(app)


from app.core.security.rate_limiter import rate_limiter


@pytest.fixture(autouse=True)
def clean_webhook_cache():
    """Clear message deduplication cache and rate limiter counters before each test."""
    with whatsapp_webhook_service._lock:
        whatsapp_webhook_service._processed_messages.clear()
    with rate_limiter._lock:
        rate_limiter._requests.clear()


@pytest.fixture(autouse=True)
def default_sync_dispatch():
    """Default to synchronous TwiML return for legacy test assertions."""
    with patch.object(settings, "TWILIO_ASYNC_DISPATCH", False):
        yield


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
    View full evidence: https://satya-setu-phi.vercel.app/check/...
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
        assert '"UPI will be banned tomorrow."' in content
        assert "Why:\nWe found no official evidence announcing a nationwide UPI shutdown." in content
        assert 'Correction:\nNPCI: "NPCI clarifies UPI remains fully functional nationwide."' in content
        assert "Proof:\nNPCI — https://npci.org.in/upi-clarification" in content
        assert "View full evidence:" in content
        assert "https://satya-setu-phi.vercel.app/check/chk_" in content


# ==============================================================================
# 3b. Multiple Claims Response Formatting Tests
# ==============================================================================

def test_whatsapp_multiple_claims_response_formatting(client):
    """
    Verifies multi-claim WhatsApp formatting matching the user specification:
    Original:
    'UPI is banned tomorrow and everyone must pay a 5% fee.'

    Response:
    🔴 FALSE
    "UPI is banned tomorrow."

    Why:
    No reliable official evidence supports this.

    🟡 PARTLY SUPPORTED
    "Everyone must pay a 5% fee."

    Why:
    Evidence does not support the claim as stated.
    """
    form_params = {
        "MessageSid": "SM_multi_claims_01",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "UPI is banned tomorrow and everyone must pay a 5% fee.",
    }

    mock_result = VerificationResult(
        check_id="chk_multi_01",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="No reliable official evidence supports this.",
                evidence=[],  # No quote, so no invented correction
                normalized_claim="UPI is banned tomorrow.",
            ),
            ClaimVerificationResult(
                claim_id="clm_02",
                verdict=Verdict.PARTLY_SUPPORTED,
                confidence=ConfidenceLevel.MEDIUM,
                explanation="Evidence does not support the claim as stated.",
                evidence=[],
                normalized_claim="Everyone must pay a 5% fee.",
            ),
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_result):

        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200
        content = resp.text

        # Verify Claim 1 block
        assert "🔴 FALSE" in content
        assert '"UPI is banned tomorrow."' in content
        assert "Why:\nNo reliable official evidence supports this." in content

        # Verify Claim 2 block
        assert "🟡 PARTLY SUPPORTED" in content
        assert '"Everyone must pay a 5% fee."' in content
        assert "Why:\nEvidence does not support the claim as stated." in content

        # Verify that no correction was invented because no evidence quote existed
        assert "Correction:" not in content

        # Verify full evidence footer
        assert "View full evidence:" in content
        assert "https://satya-setu-phi.vercel.app/check/chk_multi_01" in content


def test_whatsapp_correction_strictly_grounded_in_validated_evidence():
    """
    Verifies that when a claim is FALSE:
    1. A correction is included IF grounded in validated evidence quote.
    2. A correction is NEVER invented if evidence quote is missing.
    """
    service = WhatsAppWebhookService()

    # Case 1: FALSE with validated evidence quote -> Correction present
    claim_with_quote = ClaimVerificationResult(
        claim_id="clm_with_quote",
        verdict=Verdict.FALSE,
        confidence=ConfidenceLevel.HIGH,
        explanation="No evidence supports this.",
        evidence=[
            LockedEvidenceItem(
                source_url="https://npci.org.in/press/01",
                publisher="NPCI",
                source_title="Press Release",
                exact_quote="UPI services operate uninterrupted without shutdown.",
                source_text_reference="ref-1",
                source_tier=1,
                retrieved_at="2026-10-08T10:00:00Z",
                claim_relation="REFUTES",
            )
        ],
        normalized_claim="UPI is banned tomorrow.",
    )

    result_with_quote = VerificationResult(
        check_id="chk_quote_01",
        claims=[claim_with_quote],
        overall_verdict=Verdict.FALSE,
    )
    formatted_1 = service.format_whatsapp_response(result_with_quote, "chk_quote_01")
    assert formatted_1.correction == 'NPCI: "UPI services operate uninterrupted without shutdown."'
    assert 'Correction:\nNPCI: "UPI services operate uninterrupted without shutdown."' in formatted_1.formatted_body

    # Case 2: FALSE with NO evidence quote -> Never invent a correction
    claim_without_quote = ClaimVerificationResult(
        claim_id="clm_no_quote",
        verdict=Verdict.FALSE,
        confidence=ConfidenceLevel.HIGH,
        explanation="No reliable evidence supports this.",
        evidence=[],
        normalized_claim="UPI is banned tomorrow.",
    )

    result_without_quote = VerificationResult(
        check_id="chk_no_quote_01",
        claims=[claim_without_quote],
        overall_verdict=Verdict.FALSE,
    )
    formatted_2 = service.format_whatsapp_response(result_without_quote, "chk_no_quote_01")
    assert formatted_2.correction is None
    assert "Correction:" not in formatted_2.formatted_body


def test_whatsapp_non_false_verdicts_never_add_correction():
    """Verifies that non-FALSE verdicts (VERIFIED, PARTLY_SUPPORTED, OUTDATED, etc.) omit Correction."""
    service = WhatsAppWebhookService()

    for non_false_verdict in [Verdict.VERIFIED, Verdict.PARTLY_SUPPORTED, Verdict.OUTDATED, Verdict.CANNOT_BE_CONFIRMED]:
        claim = ClaimVerificationResult(
            claim_id="clm_other",
            verdict=non_false_verdict,
            confidence=ConfidenceLevel.HIGH,
            explanation="Explanation for verdict.",
            evidence=[
                LockedEvidenceItem(
                    source_url="https://example.gov.in/doc",
                    publisher="Gov Dept",
                    source_title="Title",
                    exact_quote="Verbatim quote text here.",
                    source_text_reference="ref",
                    source_tier=1,
                    retrieved_at="2026-10-08T10:00:00Z",
                    claim_relation="SUPPORTS",
                )
            ],
            normalized_claim="Statement under check.",
        )
        res = VerificationResult(check_id="chk_01", claims=[claim], overall_verdict=non_false_verdict)
        formatted = service.format_whatsapp_response(res, "chk_01")
        assert formatted.correction is None
        assert "Correction:" not in formatted.formatted_body


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
    assert '"Sample claim statement under review."' in formatted.formatted_body
    assert "Why:\nOfficial fact check finding explanation." in formatted.formatted_body
    assert "View full evidence:" in formatted.formatted_body
    assert "https://satya-setu-phi.vercel.app/check/chk_test_emoji" in formatted.formatted_body


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


# ==============================================================================
# 10. Step 18 End-to-End Async Webhook & REST Dispatch Test
# ==============================================================================

def test_whatsapp_async_webhook_acknowledgment_and_outbound_dispatch(client):
    """
    Step 18 Test:
    1. Request accepted immediately
    2. Message parsed into WhatsAppIncomingMessage
    3. Check created
    4. Real verification service invoked in background
    5. Final result persisted
    6. Outbound Twilio REST API called with actual result
    """
    form_params = {
        "MessageSid": "SM_TEST_STEP18_001",
        "AccountSid": "AC_TEST_ACCOUNT_123",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "Is UPI charging 5% fee from tomorrow?",
        "NumMedia": "0",
    }

    mock_verif_result = VerificationResult(
        check_id="chk_step18_001",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_step18_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="NPCI and RBI have issued no directive imposing a 5% fee on UPI payments.",
                evidence=[
                    LockedEvidenceItem(
                        source_url="https://npci.org.in/press/upi-fee-rumour",
                        publisher="NPCI",
                        source_title="UPI Clarification on Service Fees",
                        exact_quote="Normal UPI transactions remain completely free for citizens.",
                        source_text_reference="p1",
                        source_tier=1,
                        retrieved_at="2026-10-08T10:00:00Z",
                        claim_relation="REFUTES",
                    )
                ],
                normalized_claim="UPI will charge a 5% fee from tomorrow.",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(settings, "TWILIO_ASYNC_DISPATCH", True), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_verif_result) as mock_verify, \
         patch.object(whatsapp_webhook_service, "send_outbound_whatsapp_message") as mock_send_outbound:

        # 1. Post webhook request
        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)

        # 2. Assert webhook returns immediate HTTP 200 with acknowledgment TwiML
        assert resp.status_code == 200
        assert "<Response>" in resp.text
        assert "🔎 Checking this claim with reliable sources" in resp.text

        # 3. Assert real verification orchestrator was invoked
        mock_verify.assert_called_once()
        assert "Is UPI charging 5% fee from tomorrow?" in mock_verify.call_args[1]["content"]

        # 4. Assert outbound Twilio REST API was invoked with the real formatted result
        mock_send_outbound.assert_called_once()
        outbound_args = mock_send_outbound.call_args[1]
        assert outbound_args["to_number"] == "whatsapp:+919876543210"
        assert outbound_args["incoming_message_sid"] == "SM_TEST_STEP18_001"
        assert "🔴 FALSE" in outbound_args["body_text"]
        assert "NPCI" in outbound_args["body_text"]


def test_whatsapp_conversational_greeting_immediate_reply(client):
    """Verifies conversational greetings (hi, hello, etc.) receive instant welcome guide."""
    form_params = {
        "MessageSid": "SM_hi_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "hi",
        "NumMedia": "0",
    }

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False):
        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200
        assert "<Response>" in resp.text
        assert "Welcome to SachCheck" in resp.text
        assert "How to verify:" in resp.text


# ==============================================================================
# 9. Public Evidence URL Production Configuration Tests
# ==============================================================================

def test_public_evidence_url_default_production():
    """Verifies default public evidence URL points to production Vercel app on route /check/{id}."""
    url = settings.get_public_evidence_url("chk_6fa7905ed442")
    assert url == "https://satya-setu-phi.vercel.app/check/chk_6fa7905ed442"
    assert "sachcheck.in" not in url
    assert "/checks/" not in url


def test_public_evidence_url_custom_base_url():
    """Verifies PUBLIC_APP_URL overrides the base URL without trailing slash issues."""
    with patch.object(settings, "PUBLIC_APP_URL", "https://staging.satyasetu.org/"):
        url = settings.get_public_evidence_url("chk_custom_001")
        assert url == "https://staging.satyasetu.org/check/chk_custom_001"


def test_public_evidence_url_legacy_sachcheck_rejected():
    """Verifies legacy sachcheck.in domain is safely sanitized to the production Vercel app."""
    with patch.object(settings, "PUBLIC_APP_URL", "https://sachcheck.in"):
        url = settings.get_public_evidence_url("chk_safe_002")
        assert url == "https://satya-setu-phi.vercel.app/check/chk_safe_002"
        assert "sachcheck.in" not in url


def test_whatsapp_response_uses_public_app_url():
    """Verifies format_whatsapp_response uses get_public_evidence_url and real verification ID."""
    mock_res = VerificationResult(
        check_id="chk_whatsapp_prod_test",
        claims=[
            ClaimVerificationResult(
                claim_id="c1",
                verdict=Verdict.VERIFIED,
                confidence=ConfidenceLevel.HIGH,
                explanation="Verified against authoritative sources.",
                claim_text="Government launches new portal.",
                evidence=[],
            )
        ],
        overall_verdict=Verdict.VERIFIED,
    )
    formatted = whatsapp_webhook_service.format_whatsapp_response(mock_res, "chk_whatsapp_prod_test")
    assert formatted.full_evidence_url == "https://satya-setu-phi.vercel.app/check/chk_whatsapp_prod_test"
    assert "View full evidence:\nhttps://satya-setu-phi.vercel.app/check/chk_whatsapp_prod_test" in formatted.formatted_body


def test_whatsapp_verification_persists_record_and_accessible_via_public_api(client):
    """
    Verifies that a WhatsApp verification creates a persisted Check record
    that is immediately retrievable via GET /api/v1/checks/{check_id} with full findings.
    """
    import re
    from app.jobs import job_manager

    form_params = {
        "MessageSid": "SM_persist_test_001",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "Body": "Is RBI issuing new 1000 rupee notes?",
    }

    mock_result = VerificationResult(
        check_id="chk_rbi_persist_01",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_rbi_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="RBI has issued no notification regarding the reintroduction of Rs 1000 notes.",
                evidence=[
                    LockedEvidenceItem(
                        source_url="https://rbi.org.in/press/1000-note-clarification",
                        publisher="Reserve Bank of India",
                        source_title="RBI Clarification Press Release",
                        exact_quote="Reserve Bank of India clarifies that there is no proposal to introduce Rs 1000 currency notes.",
                        source_text_reference="para 2",
                        source_tier=1,
                        retrieved_at="2026-10-11T12:00:00Z",
                        claim_relation="REFUTES",
                    )
                ],
                rule_trace=["RULE-DIRECT-REFUTATION"],
                claim_text="RBI is introducing new 1000 rupee notes.",
                normalized_claim="RBI is introducing new 1000 rupee notes.",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_result):

        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200
        content = resp.text

        # Extract the evidence URL from the WhatsApp reply
        url_match = re.search(r"https://satya-setu-phi\.vercel\.app/check/([a-zA-Z0-9_\-]+)", content)
        assert url_match is not None, f"No valid evidence URL found in response: {content}"
        persisted_check_id = url_match.group(1)

        # 1. Verify the record is in job_manager / CheckRepository
        saved_check = job_manager.get_check(persisted_check_id)
        assert saved_check is not None, f"Check {persisted_check_id} was not persisted in check_repo!"
        assert saved_check.status.value == "COMPLETED"
        assert saved_check.result is not None
        assert saved_check.result.overall_verdict == Verdict.FALSE

        # 2. Verify the public API GET /api/v1/checks/{check_id} returns the saved dossier
        api_resp = client.get(f"/api/v1/checks/{persisted_check_id}")
        assert api_resp.status_code == 200
        data = api_resp.json()
        assert data["check_id"] == persisted_check_id
        assert data["status"] == "COMPLETED"
        assert data["result"]["overall_verdict"] == "FALSE"
        assert len(data["claims"]) >= 1
        assert "Reserve Bank of India" in data["claims"][0]["evidence"][0]["publisher"]
        assert data["claims"][0]["evidence"][0]["source_url"] == "https://rbi.org.in/press/1000-note-clarification"


def test_whatsapp_verification_links_sender_to_verified_account(client):
    """
    Verifies that when an authenticated user registered via Twilio Verify sends a WhatsApp claim,
    the persisted Check is automatically associated with their user_id and appears in their history.
    """
    import re
    from app.services.auth_service import auth_service
    from app.schemas.core import User, UserRole
    from app.jobs import job_manager

    # Register/mock user with phone number verified via Twilio
    verified_phone = "+919988776655"
    test_user = User(
        user_id="usr_verified_citizen_77",
        phone_number=verified_phone,
        role=UserRole.CITIZEN,
        phone_verified=True,
    )
    auth_service.user_repo.save_user(test_user)

    form_params = {
        "MessageSid": "SM_auth_user_001",
        "From": f"whatsapp:{verified_phone}",
        "To": "whatsapp:+14155238886",
        "Body": "Is Aadhaar mandatory for board exams?",
    }

    mock_result = VerificationResult(
        check_id="chk_aadhaar_001",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_aadhaar_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="UIDAI and CBSE circular states Aadhaar is not mandatory for board exams.",
                evidence=[],
                claim_text="Aadhaar is mandatory for board exams.",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    with patch.object(settings, "TWILIO_VALIDATE_SIGNATURE", False), \
         patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_result):

        resp = client.post("/api/v1/whatsapp/webhook", data=form_params)
        assert resp.status_code == 200

        # Extract check_id
        url_match = re.search(r"https://satya-setu-phi\.vercel\.app/check/([a-zA-Z0-9_\-]+)", resp.text)
        assert url_match is not None
        check_id = url_match.group(1)

        # Verify Check was associated with test_user.user_id
        saved_check = job_manager.get_check(check_id)
        assert saved_check is not None
        assert saved_check.user_id == "usr_verified_citizen_77"

        # Verify check appears in user's history list
        user_checks = job_manager.check_repo.list_checks(user_id="usr_verified_citizen_77")
        assert any(c.check_id == check_id for c in user_checks)


# =========================================================================
# 12. Twilio Error 21654 & Outbound Dispatch Safety Tests
# =========================================================================

def test_send_outbound_whatsapp_message_uses_body_for_active_reply():
    """
    Verifies that standard active-session messages are sent via 'body'
    and NEVER pass content_variables or content_sid to client.messages.create().
    """
    mock_client_cls = MagicMock()
    mock_client_instance = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "SM_outbound_123"
    mock_msg.status = "sent"
    mock_client_instance.messages.create.return_value = mock_msg
    mock_client_cls.return_value = mock_client_instance

    with patch("twilio.rest.Client", mock_client_cls), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", "ACmock123"), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", "mocktoken123"), \
         patch.object(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"):

        sid = whatsapp_webhook_service.send_outbound_whatsapp_message(
            to_number="+919876543210",
            body_text="Your claim is FALSE.",
            check_id="chk_test_101",
            incoming_message_sid="SM_inbound_101",
        )

        assert sid == "SM_outbound_123"
        mock_client_instance.messages.create.assert_called_once()
        create_kwargs = mock_client_instance.messages.create.call_args[1]

        # Explicitly verify body is used and template kwargs are ABSENT
        assert create_kwargs["body"] == "Your claim is FALSE."
        assert create_kwargs["to"] == "whatsapp:+919876543210"
        assert create_kwargs["from_"] == "whatsapp:+14155238886"
        assert "content_sid" not in create_kwargs
        assert "content_variables" not in create_kwargs


def test_send_outbound_whatsapp_message_strips_content_variables_when_body_present():
    """
    Verifies that if content_variables is accidentally passed alongside body_text,
    it is safely stripped and NOT passed to Twilio's client.messages.create().
    """
    mock_client_cls = MagicMock()
    mock_client_instance = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "SM_outbound_456"
    mock_msg.status = "sent"
    mock_client_instance.messages.create.return_value = mock_msg
    mock_client_cls.return_value = mock_client_instance

    with patch("twilio.rest.Client", mock_client_cls), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", "ACmock123"), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", "mocktoken123"), \
         patch.object(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"):

        sid = whatsapp_webhook_service.send_outbound_whatsapp_message(
            to_number="+919876543210",
            body_text="Regular text message",
            content_variables={"1": "ignored_var"},
        )

        assert sid == "SM_outbound_456"
        create_kwargs = mock_client_instance.messages.create.call_args[1]
        assert create_kwargs["body"] == "Regular text message"
        assert "content_variables" not in create_kwargs
        assert "content_sid" not in create_kwargs


def test_send_outbound_whatsapp_message_rejects_content_variables_without_content_sid():
    """
    Verifies that passing content_variables without a valid Content SID (and without body)
    safely aborts instead of causing Twilio error 21654 (ContentSid Required).
    """
    mock_client_cls = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_cls.return_value = mock_client_instance

    with patch("twilio.rest.Client", mock_client_cls), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", "ACmock123"), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", "mocktoken123"), \
         patch.object(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"), \
         patch.object(settings, "TWILIO_CONTENT_SID", None):

        sid = whatsapp_webhook_service.send_outbound_whatsapp_message(
            to_number="+919876543210",
            body_text="",
            content_variables={"1": "something"},
        )

        # Must return None and never invoke Twilio create()
        assert sid is None
        mock_client_instance.messages.create.assert_not_called()


def test_send_outbound_whatsapp_message_handles_twilio_error_21654_safely():
    """
    Verifies that when Twilio REST API returns error 21654 (or any TwilioRestException),
    it logs cleanly, emits audit event, and returns None without raising or crashing callers.
    """
    from twilio.base.exceptions import TwilioRestException

    mock_client_cls = MagicMock()
    mock_client_instance = MagicMock()
    # Simulate Twilio 21654 ContentSid Required exception
    mock_client_instance.messages.create.side_effect = TwilioRestException(
        status=400,
        uri="/Accounts/AC123/Messages.json",
        msg="Unable to create record: ContentSid Required",
        code=21654,
    )
    mock_client_cls.return_value = mock_client_instance

    with patch("twilio.rest.Client", mock_client_cls), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", "ACmock123"), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", "mocktoken123"), \
         patch.object(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"):

        # Should NOT raise
        sid = whatsapp_webhook_service.send_outbound_whatsapp_message(
            to_number="+919876543210",
            body_text="Test message body",
            check_id="chk_error_test",
        )

        assert sid is None


@pytest.mark.asyncio
async def test_async_verification_outbound_failure_preserves_check_record():
    """
    Verifies that if outbound dispatch fails (e.g. Twilio API error or limit),
    the verification check record is preserved in the repository and NOT overwritten or marked failed.
    """
    incoming = WhatsAppIncomingMessage(
        message_sid="SM_preserve_test_01",
        from_number="whatsapp:+919876543210",
        to_number="whatsapp:+14155238886",
        body="Does Earth orbit the Sun in 365 days?",
    )
    test_check_id = "chk_preserve_001"

    mock_result = VerificationResult(
        check_id=test_check_id,
        claims=[
            ClaimVerificationResult(
                claim_id="clm_01",
                verdict=Verdict.VERIFIED,
                confidence=ConfidenceLevel.HIGH,
                explanation="Earth orbits the Sun in approximately 365.25 days.",
                evidence=[],
                claim_text="Earth orbits the Sun in 365 days",
            )
        ],
        overall_verdict=Verdict.VERIFIED,
    )

    # Mock orchestrator to succeed, but send_outbound_whatsapp_message to return None (failure)
    with patch.object(whatsapp_webhook_service.orchestrator, "verify", return_value=mock_result), \
         patch.object(whatsapp_webhook_service, "send_outbound_whatsapp_message", return_value=None) as mock_send:

        await whatsapp_webhook_service._run_async_verification(
            incoming=incoming,
            check_id=test_check_id,
            input_type="TEXT",
        )

        # Outbound was attempted once for the verdict
        assert mock_send.call_count == 1
        # Check that the verification check is present in job_manager repository
        saved = job_manager.get_check(test_check_id)
        assert saved is not None
        assert saved.result.overall_verdict == Verdict.VERIFIED
        # Ensure failure notice was NOT dispatched because verification itself succeeded
        assert "I couldn't complete the verification" not in mock_send.call_args[1].get("body_text", "")



