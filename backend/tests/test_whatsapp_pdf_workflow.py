import os
import pytest
from unittest.mock import MagicMock, patch

from app.schemas.enums import Verdict
from app.schemas.verification import ClaimVerificationResult, VerificationResult
from app.services.claim_extractor import ClaimExtractorService
from app.services.pdf_ingestion import PDFIngestionService, pdf_ingestion_service
from app.services.whatsapp import WhatsAppWebhookService


SAMPLE_PDF_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "satyasetu_whatsapp_pdf_test.pdf")


@pytest.fixture
def sample_pdf_bytes():
    assert os.path.exists(SAMPLE_PDF_PATH), f"Fixture not found at {SAMPLE_PDF_PATH}"
    with open(SAMPLE_PDF_PATH, "rb") as f:
        return f.read()


def test_pdf_ingestion_extracts_full_text(sample_pdf_bytes):
    """Verifies that PDFIngestionService extracts all substantive text without security violation."""
    res = pdf_ingestion_service.ingest_pdf(sample_pdf_bytes, filename="satyasetu_whatsapp_pdf_test.pdf")
    assert res.page_count == 1
    assert res.needs_ocr is False
    assert len(res.extracted_text) > 400
    assert "Government of India" in res.extracted_text
    assert "365.25 days" in res.extracted_text
    assert "bank OTP" in res.extracted_text


def test_claim_extractor_identifies_three_factual_claims():
    """Verifies that ClaimExtractorService isolates the 3 factual statements and filters meta instructions."""
    with open(SAMPLE_PDF_PATH, "rb") as f:
        data = f.read()
    ingest_res = pdf_ingestion_service.ingest_pdf(data)

    extractor = ClaimExtractorService()
    extractor.groq_model = "openai/gpt-oss-120b"
    claims_output = extractor.extract_claims(ingest_res.extracted_text)

    # Must extract claims and not include the filename or test instructions as a claim
    assert len(claims_output.claims) >= 3
    claim_texts = " ".join([c.normalized_claim or c.original_text for c in claims_output.claims])

    assert "satyasetu_whatsapp_pdf_test.pdf" not in claim_texts
    assert "Purpose" not in claim_texts
    assert "Test instructions" not in claim_texts
    # All 3 core subjects must be represented
    assert any("50,000" in t or "50000" in t or "cash" in t for t in [c.original_text for c in claims_output.claims])
    assert any("365.25" in t or "orbit" in t or "sun" in t.lower() for t in [c.original_text for c in claims_output.claims])
    assert any("otp" in t.lower() or "credentials" in t.lower() for t in [c.original_text for c in claims_output.claims])


def test_whatsapp_identifies_pdf_modality_and_filename():
    """Verifies WhatsAppWebhookService correctly classifies incoming PDF and extracts filename."""
    svc = WhatsAppWebhookService()
    form_data = {
        "MessageSid": "SM_pdf_test_123",
        "From": "whatsapp:+918591784184",
        "To": "whatsapp:+14155238886",
        "Body": "satyasetu_whatsapp_pdf_test.pdf",
        "NumMedia": "1",
        "MediaContentType0": "application/pdf",
        "MediaUrl0": "https://api.twilio.com/mock_media.pdf",
    }

    input_type = svc.identify_input_type(form_data)
    assert input_type == "PDF"

    incoming = svc.parse_incoming_message(form_data)
    assert incoming.filename == "satyasetu_whatsapp_pdf_test.pdf"


def test_whatsapp_formatted_response_for_pdf():
    """Verifies format_whatsapp_response outputs structured document format when document_filename is provided."""
    svc = WhatsAppWebhookService()

    mock_result = VerificationResult(
        check_id="chk_pdf_sample_01",
        overall_verdict=Verdict.PARTLY_SUPPORTED,
        summary="Document containing multiple claims was evaluated.",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_001",
                claim_text="The Government of India has officially declared that every Indian citizen will receive 50,000 cash.",
                verdict=Verdict.FALSE,
                confidence="HIGH",
                explanation="No official scheme offers Rs 50,000 direct cash.",
                evidence=[],
            ),
            ClaimVerificationResult(
                claim_id="clm_002",
                claim_text="The Earth completes one revolution around the Sun in approximately 365.25 days.",
                verdict=Verdict.VERIFIED,
                confidence="HIGH",
                explanation="Verified astronomical constant.",
                evidence=[],
            ),
            ClaimVerificationResult(
                claim_id="clm_003",
                claim_text="A website asking for bank OTP over unsolicited WhatsApp message may be attempting to steal credentials.",
                verdict=Verdict.VERIFIED,
                confidence="HIGH",
                explanation="Authentic cybersecurity alert from CERT-In and RBI.",
                evidence=[],
            ),
        ],
    )

    formatted = svc.format_whatsapp_response(
        result=mock_result,
        check_id="chk_pdf_sample_01",
        document_filename="satyasetu_whatsapp_pdf_test.pdf",
    )

    body = formatted.formatted_body
    assert "PDF received and analyzed" in body
    assert "satyasetu_whatsapp_pdf_test.pdf" in body
    assert "Claims extracted: 3" in body
    assert "1. Claim:" in body
    assert "2. Claim:" in body
    assert "3. Claim:" in body
    assert "View full evidence:" in body
    assert "/check/chk_pdf_sample_01" in body


@pytest.mark.asyncio
async def test_unreadable_pdf_returns_error_instead_of_fake_verdict():
    """Verifies that an unreadable/corrupt PDF produces an error explanation rather than a fact-check verdict on filename."""
    svc = WhatsAppWebhookService()
    form_data = {
        "MessageSid": "SM_corrupted_pdf",
        "From": "whatsapp:+918591784184",
        "To": "whatsapp:+14155238886",
        "Body": "corrupted.pdf",
        "NumMedia": "1",
        "MediaContentType0": "application/pdf",
        "MediaUrl0": "https://mock.twilio.com/corrupt.pdf",
    }

    incoming = svc.parse_incoming_message(form_data)

    with patch.object(svc, "download_media_safely", return_value=b"corrupted binary data not a pdf"):
        mock_send = MagicMock()
        with patch.object(svc, "send_outbound_whatsapp_message", mock_send):
            await svc._run_async_verification(
                incoming=incoming,
                check_id="chk_corrupt_test",
                input_type="PDF",
                user_id=None,
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[1]
            sent_body = call_args["body_text"]
            assert "Unable to verify PDF document" in sent_body
            assert "corrupted.pdf" in sent_body
            # Should NOT contain fact-check verdict emojis
            assert "🔴 FALSE" not in sent_body
            assert "CANNOT BE CONFIRMED" not in sent_body
