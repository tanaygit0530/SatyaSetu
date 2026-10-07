import io
import fitz
import httpx
from PIL import Image
import pytest

from app.core.exceptions import InvalidInputException
from app.main import app
from app.schemas.ingestion import PDFIngestionResult
from app.services.pdf.ranker import ClaimBearingPageRanker
from app.services.pdf_ingestion import PDFIngestionService, pdf_ingestion_service


# Helper to generate in-memory PDFs using PyMuPDF
def create_test_pdf(pages_content: list[str]) -> bytes:
    """Generates an in-memory PDF with text on specified pages."""
    doc = fitz.open()
    for text in pages_content:
        page = doc.new_page()
        if text:
            page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_scanned_pdf(num_pages: int = 2) -> bytes:
    """Generates a PDF containing images on pages but ZERO text layer (simulating scanned document)."""
    doc = fitz.open()
    img = Image.new("RGB", (300, 300), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_data = buf.getvalue()

    for _ in range(num_pages):
        page = doc.new_page()
        page.insert_image(page.rect, stream=img_data)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ==============================================================================
# 1. Normal Text PDF Test
# ==============================================================================

def test_normal_text_pdf_ingestion():
    """
    Validates normal PDF ingestion with meaningful text:
    Extracts text per page, preserves page numbers, calculates total text length.
    """
    page1_text = "Ministry of Education Circular No. 2026/04. Official scholarship scheme is notified."
    page2_text = "All eligible undergraduate students will receive grant directly via DBT transfer."
    pdf_bytes = create_test_pdf([page1_text, page2_text])

    result = pdf_ingestion_service.ingest_pdf(pdf_bytes)

    assert result.input_type == "PDF"
    assert result.page_count == 2
    assert result.needs_ocr is False
    assert len(result.text_pages) == 2

    assert result.text_pages[0].page == 1
    assert "Ministry of Education" in result.text_pages[0].text

    assert result.text_pages[1].page == 2
    assert "DBT transfer" in result.text_pages[1].text
    assert result.total_text_length > 100


# ==============================================================================
# 2. Specification Example: 20-Page PDF with Sparse Text Pages
# ==============================================================================

def test_twenty_page_pdf_with_sparse_meaningful_pages():
    """
    Validates exact scenario from specification:
    20-page PDF where only page 4 and page 12 contain meaningful text.
    Result returns page_count = 20 and text_pages for pages 4 and 12.
    """
    pages_list = [""] * 20
    pages_list[3] = "Notification: The government launched Scheme X in 2025 across all union territories."  # Page 4 (1-indexed)
    pages_list[11] = "Clause 12: Disbursement of Rs. 12,000 per annum sanctioned with immediate effect."  # Page 12 (1-indexed)

    pdf_bytes = create_test_pdf(pages_list)

    result = pdf_ingestion_service.ingest_pdf(pdf_bytes)

    assert result.page_count == 20
    assert result.needs_ocr is False
    assert len(result.text_pages) == 2

    page_numbers = [p.page for p in result.text_pages]
    assert page_numbers == [4, 12]
    assert "Scheme X in 2025" in result.text_pages[0].text
    assert "Rs. 12,000" in result.text_pages[1].text


# ==============================================================================
# 3. Empty PDF Test
# ==============================================================================

def test_empty_pdf_pages():
    """
    Validates PDF with 3 pages containing zero text:
    needs_ocr is flagged True because text layer is absent.
    """
    pdf_bytes = create_test_pdf(["", "", ""])
    result = pdf_ingestion_service.ingest_pdf(pdf_bytes)

    assert result.page_count == 3
    assert len(result.text_pages) == 0
    assert result.needs_ocr is True


def test_zero_bytes_pdf_rejected():
    """Ensures 0-byte upload raises InvalidInputException."""
    with pytest.raises(InvalidInputException) as exc_info:
        pdf_ingestion_service.ingest_pdf(b"")
    assert "empty (0 bytes)" in str(exc_info.value)


# ==============================================================================
# 4. Scanned PDF Test (Missing Text Layer)
# ==============================================================================

def test_scanned_pdf_detects_missing_text_layer():
    """
    Validates scanned PDF:
    PDF contains raster images but NO searchable text stream.
    Service detects missing text layer and returns needs_ocr = True without running expensive OCR.
    """
    scanned_bytes = create_scanned_pdf(num_pages=3)

    result = pdf_ingestion_service.ingest_pdf(scanned_bytes)

    assert result.page_count == 3
    assert len(result.text_pages) == 0
    assert result.needs_ocr is True


# ==============================================================================
# 5. Page Limit Validation (> 100 Pages)
# ==============================================================================

def test_exceeding_max_page_limit_rejected():
    """Ensures PDFs exceeding max page limit (e.g. 101 pages) are rejected."""
    service = PDFIngestionService(max_page_count=10)
    pdf_bytes = create_test_pdf(["Page content"] * 12)

    with pytest.raises(InvalidInputException) as exc_info:
        service.ingest_pdf(pdf_bytes)

    assert "exceeds maximum allowed limit of 10 pages" in str(exc_info.value)


# ==============================================================================
# 6. Corrupted & Non-PDF File Rejection
# ==============================================================================

def test_corrupted_pdf_rejected():
    """Validates malformed/corrupted PDF bytes starting with %PDF- header."""
    corrupted_bytes = b"%PDF-1.4\n trailer\n<< /Root >>\n corrupted garbage payload"
    with pytest.raises(InvalidInputException) as exc_info:
        pdf_ingestion_service.ingest_pdf(corrupted_bytes)
    assert "Corrupted or malformed PDF" in str(exc_info.value)


def test_unsupported_non_pdf_file_rejected():
    """Ensures non-PDF files (e.g. PNG image or text) are rejected by magic bytes."""
    fake_pdf = b"\x89PNG\r\n\x1a\nNot a PDF"
    with pytest.raises(InvalidInputException) as exc_info:
        pdf_ingestion_service.ingest_pdf(fake_pdf)
    assert "Unsupported file format" in str(exc_info.value)


# ==============================================================================
# 7. Page Ranking Abstraction Test
# ==============================================================================

def test_claim_bearing_page_ranking():
    """
    Tests ClaimBearingPageRanker prioritization:
    Page with statutory order keywords and financial amounts ranks higher than generic pages.
    """
    pages = [
        "Generic table of contents, preface, acknowledgments, copyright details.",
        "Notification MoE-2026: Ministry sanctions Rs. 50,000 subsidy grant under PM Scheme.",
        "General index of terms, glossary, and appendix footnotes.",
    ]
    pdf_bytes = create_test_pdf(pages)
    result = pdf_ingestion_service.ingest_pdf(pdf_bytes)

    assert result.ranked_claim_pages is not None
    # Page 2 (with scheme, ministry, rs. 50,000, grant) must be ranked #1
    assert result.ranked_claim_pages[0] == 2


# ==============================================================================
# 8. API Route Integration Test
# ==============================================================================

@pytest.mark.asyncio
async def test_api_pdf_ingest_endpoint_success():
    """Tests POST /api/v1/ingest/pdf via HTTP multipart upload."""
    doc_text = "Official Gazette of India notification regarding PM scholarship guidelines 2026."
    pdf_bytes = create_test_pdf([doc_text])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("circular.pdf", pdf_bytes, "application/pdf")}
        response = await client.post("/api/v1/ingest/pdf", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["input_type"] == "PDF"
        assert data["page_count"] == 1
        assert data["needs_ocr"] is False
        assert len(data["text_pages"]) == 1
        assert data["text_pages"][0]["page"] == 1
        assert "Official Gazette" in data["text_pages"][0]["text"]
