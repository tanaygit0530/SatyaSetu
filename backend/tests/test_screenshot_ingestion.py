import io
import os
from unittest.mock import patch
import httpx
import pytest
from PIL import Image, ImageDraw

from app.core.exceptions import InvalidInputException
from app.main import app
from app.schemas.ingestion import ScreenshotIngestionResult
from app.services.ocr.base import OCRProvider, OCRRawResult
from app.services.screenshot_ingestion import (
    JPEG_MAGIC,
    PNG_MAGIC,
    ScreenshotIngestionService,
    screenshot_ingestion_service,
)


# Helper to generate test images in-memory
def create_test_image(
    format: str = "PNG",
    size: tuple = (400, 150),
    text: str = "Official Notice 2026",
) -> bytes:
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


class MockTestOCRProvider(OCRProvider):
    """Configurable mock OCR provider for deterministic test assertions."""

    def __init__(self, name: str, text: str = "", confidence: float = 0.0):
        self._name = name
        self._text = text
        self._confidence = confidence
        self.call_count = 0
        self.last_image_path = None

    @property
    def provider_name(self) -> str:
        return self._name

    def extract_text(self, image_path: str) -> OCRRawResult:
        self.call_count += 1
        self.last_image_path = image_path
        # Verify the file actually exists while OCR is running!
        assert os.path.exists(image_path), f"Temp file {image_path} must exist during OCR!"
        return OCRRawResult(
            text=self._text,
            confidence=self._confidence,
            provider=self._name,
            word_count=len(self._text.split()),
        )


# ==============================================================================
# 1. Normal Screenshot Test
# ==============================================================================

def test_normal_screenshot_ingestion():
    """
    Validates normal clear screenshot:
    - Primary provider (Tesseract) produces high confidence text.
    - Temporary file is stored and deleted after execution.
    - needs_confirmation is False.
    """
    image_bytes = create_test_image(format="PNG", text="Government announces Scheme X in 2025.")

    primary_mock = MockTestOCRProvider(
        name="tesseract",
        text="Government announces Scheme X in 2025.",
        confidence=0.92,
    )
    fallback_mock = MockTestOCRProvider(name="vision", text="", confidence=0.0)

    service = ScreenshotIngestionService(
        primary_provider=primary_mock,
        fallback_provider=fallback_mock,
        confidence_threshold=0.70,
    )

    result = service.ingest_screenshot(image_bytes)

    assert result.input_type == "SCREENSHOT"
    assert result.extracted_text == "Government announces Scheme X in 2025."
    assert result.ocr_confidence == 0.92
    assert result.provider == "tesseract"
    assert result.needs_confirmation is False

    # Verify fallback was NOT needed
    assert primary_mock.call_count == 1
    assert fallback_mock.call_count == 0

    # Verify temporary file was deleted
    assert not os.path.exists(primary_mock.last_image_path)


# ==============================================================================
# 2. Blurry Screenshot & Fallback Test
# ==============================================================================

def test_blurry_screenshot_triggers_vision_fallback():
    """
    Validates blurry screenshot:
    - Tesseract yields poor confidence (0.45 < 0.70 threshold).
    - Pipeline triggers Vision OCR fallback.
    - Vision yields higher confidence (0.88), which is adopted.
    """
    image_bytes = create_test_image(format="JPEG", text="Blurry text")

    primary_mock = MockTestOCRProvider(
        name="tesseract",
        text="Gov... ann... Sch...",
        confidence=0.45,
    )
    fallback_mock = MockTestOCRProvider(
        name="vision",
        text="Government announces Scheme X in 2025.",
        confidence=0.88,
    )

    service = ScreenshotIngestionService(
        primary_provider=primary_mock,
        fallback_provider=fallback_mock,
        confidence_threshold=0.70,
    )

    result = service.ingest_screenshot(image_bytes)

    assert result.input_type == "SCREENSHOT"
    assert result.extracted_text == "Government announces Scheme X in 2025."
    assert result.ocr_confidence == 0.88
    assert result.provider == "vision"
    assert result.needs_confirmation is False

    assert primary_mock.call_count == 1
    assert fallback_mock.call_count == 1


def test_severely_degraded_screenshot_marks_needs_confirmation():
    """
    Validates that if both primary and fallback OCR have low confidence,
    needs_confirmation is set to True. Never silently treat low-confidence as accurate.
    """
    image_bytes = create_test_image(format="PNG", text="Indecipherable blur")

    primary_mock = MockTestOCRProvider(name="tesseract", text="...", confidence=0.30)
    fallback_mock = MockTestOCRProvider(name="vision", text="...", confidence=0.40)

    service = ScreenshotIngestionService(
        primary_provider=primary_mock,
        fallback_provider=fallback_mock,
        confidence_threshold=0.70,
    )

    result = service.ingest_screenshot(image_bytes)

    assert result.needs_confirmation is True
    assert result.ocr_confidence < 0.70


# ==============================================================================
# 3. Unsupported File Format Tests
# ==============================================================================

@pytest.mark.parametrize(
    "bad_bytes,description",
    [
        (b"%PDF-1.4 simulated pdf document data", "PDF file"),
        (b"GIF89a\x01\x00\x01\x00 simulated gif data", "GIF image"),
        (b"RIFF\x20\x00\x00\x00WEBPVP8 simulated webp data", "WebP image"),
        (b"MZ\x90\x00\x03\x00\x00\x00 executable payload", "EXE file"),
        (b"<html><body>Not an image</body></html>", "HTML file"),
    ],
)
def test_unsupported_file_formats_rejected(bad_bytes, description):
    """Ensures non-JPEG/PNG formats are rejected with InvalidInputException."""
    with pytest.raises(InvalidInputException) as exc_info:
        screenshot_ingestion_service.ingest_screenshot(bad_bytes)
    assert "Unsupported file format" in str(exc_info.value)


# ==============================================================================
# 4. Oversized File Test
# ==============================================================================

def test_oversized_file_rejected():
    """Ensures images larger than max_file_size are rejected."""
    service = ScreenshotIngestionService(max_file_size=1024)  # 1 KB limit
    oversized_data = JPEG_MAGIC + b"\x00" * 2000

    with pytest.raises(InvalidInputException) as exc_info:
        service.ingest_screenshot(oversized_data)
    assert "exceeds maximum limit" in str(exc_info.value)


# ==============================================================================
# 5. Empty OCR Result Test
# ==============================================================================

def test_empty_ocr_result_marks_needs_confirmation():
    """
    Validates empty image (blank screenshot where OCR finds no words):
    Result returns empty extracted_text and needs_confirmation = True.
    """
    blank_image = create_test_image(format="PNG", text="")

    empty_primary = MockTestOCRProvider(name="tesseract", text="", confidence=0.0)
    empty_fallback = MockTestOCRProvider(name="vision", text="", confidence=0.0)

    service = ScreenshotIngestionService(
        primary_provider=empty_primary,
        fallback_provider=empty_fallback,
        confidence_threshold=0.70,
    )

    result = service.ingest_screenshot(blank_image)

    assert result.extracted_text == ""
    assert result.ocr_confidence == 0.0
    assert result.needs_confirmation is True


def test_empty_file_bytes_rejected():
    """Ensures 0-byte upload is immediately rejected."""
    with pytest.raises(InvalidInputException) as exc_info:
        screenshot_ingestion_service.ingest_screenshot(b"")
    assert "empty (0 bytes)" in str(exc_info.value)


# ==============================================================================
# 6. Temporary File Cleanup Guarantee
# ==============================================================================

def test_temporary_file_deleted_even_when_ocr_fails():
    """
    Ensures temporary file is deleted even if OCR provider raises an exception.
    """
    image_bytes = create_test_image(format="PNG", text="Test")

    class CrashingOCR(OCRProvider):
        @property
        def provider_name(self) -> str:
            return "crasher"

        def extract_text(self, image_path: str) -> OCRRawResult:
            self.saved_path = image_path
            raise RuntimeError("OCR Engine crashed unexpectedly")

    crashing_provider = CrashingOCR()
    service = ScreenshotIngestionService(
        primary_provider=crashing_provider,
        fallback_provider=None,
    )

    with pytest.raises(RuntimeError):
        service.ingest_screenshot(image_bytes)

    # Verify temp file was cleaned up despite the exception
    assert not os.path.exists(crashing_provider.saved_path)


# ==============================================================================
# 7. API Route Integration Test
# ==============================================================================

@pytest.mark.asyncio
async def test_api_screenshot_ingest_endpoint_success():
    """Tests POST /api/v1/ingest/screenshot via HTTP multipart upload."""
    png_bytes = create_test_image(format="PNG", text="Official Announcement")

    mock_ocr = MockTestOCRProvider(name="tesseract", text="Official Announcement", confidence=0.91)
    with patch("app.services.screenshot_ingestion.screenshot_ingestion_service.primary_provider", mock_ocr):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("screenshot.png", png_bytes, "image/png")}
            response = await client.post("/api/v1/ingest/screenshot", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["input_type"] == "SCREENSHOT"
            assert data["extracted_text"] == "Official Announcement"
            assert data["ocr_confidence"] == 0.91
            assert data["provider"] == "tesseract"
            assert data["needs_confirmation"] is False
