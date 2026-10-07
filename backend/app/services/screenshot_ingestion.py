import io
import os
import tempfile
from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.core.config import settings
from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.schemas.ingestion import ScreenshotIngestionResult
from app.services.ocr.base import OCRProvider, OCRRawResult
from app.services.ocr.tesseract_provider import TesseractOCRProvider
from app.services.ocr.vision_provider import VisionOCRProvider


# Magic byte signatures
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ScreenshotIngestionService:
    """
    Service for ingesting, validating, re-encoding, and performing multi-engine
    OCR on citizen screenshot submissions.
    """

    def __init__(
        self,
        primary_provider: Optional[OCRProvider] = None,
        fallback_provider: Optional[OCRProvider] = None,
        confidence_threshold: Optional[float] = None,
        max_file_size: Optional[int] = None,
    ):
        self.primary_provider = primary_provider or TesseractOCRProvider()
        self.fallback_provider = fallback_provider or VisionOCRProvider()
        self.confidence_threshold = confidence_threshold or settings.OCR_CONFIDENCE_THRESHOLD
        self.max_file_size = max_file_size or settings.MAX_IMAGE_FILE_SIZE_BYTES

    def validate_magic_bytes(self, data: bytes) -> str:
        """
        Validates file MIME type using binary magic bytes.
        Only JPEG and PNG are permitted; unsupported formats are rejected.
        """
        if len(data) >= 3 and data.startswith(JPEG_MAGIC):
            return "image/jpeg"
        if len(data) >= 8 and data.startswith(PNG_MAGIC):
            return "image/png"

        # Check common rejected signatures for informative errors
        if len(data) >= 4 and data.startswith(b"%PDF"):
            mime_detected = "application/pdf"
        elif len(data) >= 6 and (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            mime_detected = "image/gif"
        elif len(data) >= 12 and data.startswith(b"RIFF") and b"WEBP" in data[:16]:
            mime_detected = "image/webp"
        else:
            mime_detected = "application/octet-stream"

        raise InvalidInputException(
            f"Unsupported file format '{mime_detected}'. Only JPG/JPEG and PNG screenshots are allowed."
        )

    def preprocess_and_reencode(self, data: bytes) -> Image.Image:
        """
        Validates image structure, strips EXIF metadata, and enhances for OCR.
        Returns a clean in-memory PIL image.
        """
        try:
            # 1. Verify byte integrity
            with Image.open(io.BytesIO(data)) as img_check:
                img_check.verify()

            # 2. Re-open to re-encode and strip EXIF
            with Image.open(io.BytesIO(data)) as raw_img:
                # Discard EXIF by creating a new clean RGB surface
                clean_img = Image.new("RGB", raw_img.size, (255, 255, 255))
                if raw_img.mode in ("RGBA", "LA"):
                    clean_img.paste(raw_img, mask=raw_img.split()[-1])
                elif raw_img.mode == "P":
                    converted = raw_img.convert("RGBA")
                    clean_img.paste(converted, mask=converted.split()[-1])
                else:
                    clean_img.paste(raw_img.convert("RGB"))

                # 3. Preprocessing for optimal OCR readability:
                # Convert to grayscale, apply contrast enhancement and slight sharpening
                gray = ImageOps.grayscale(clean_img)

                # Upscale small images to improve character resolution
                w, h = gray.size
                if w < 1000 or h < 1000:
                    scale = min(2.0, max(1.2, 1200 / max(w, h)))
                    gray = gray.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

                enhancer = ImageEnhance.Contrast(gray)
                enhanced = enhancer.enhance(1.4)

                return enhanced

        except Exception as e:
            if isinstance(e, InvalidInputException):
                raise
            raise InvalidInputException(f"Invalid or corrupted image file: {str(e)}") from e

    def ingest_screenshot(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
    ) -> ScreenshotIngestionResult:
        """
        Validates file size and magic bytes, re-encodes to strip EXIF,
        writes temporary file, runs OCR with fallback, and guarantees temporary
        file deletion.
        """
        # 1. Validate file size
        if len(image_bytes) == 0:
            raise InvalidInputException("Uploaded screenshot file is empty (0 bytes).")

        if len(image_bytes) > self.max_file_size:
            raise InvalidInputException(
                f"Screenshot file size ({len(image_bytes)} bytes) exceeds maximum limit "
                f"of {self.max_file_size} bytes."
            )

        # 2. Validate MIME using magic bytes (allow JPG/JPEG/PNG, reject others)
        self.validate_magic_bytes(image_bytes)

        # 3. Re-encode and preprocess image
        processed_img = self.preprocess_and_reencode(image_bytes)

        # 4. Save to temporary file only
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_path = temp_file.name

        try:
            processed_img.save(temp_path, format="PNG")
            temp_file.close()

            # 5. Multi-engine OCR execution with fallback
            ocr_result = self._execute_ocr_with_fallback(temp_path)

            extracted_text = ocr_result.text.strip()
            confidence = round(ocr_result.confidence, 2)
            provider = ocr_result.provider

            # Never silently treat low-confidence or empty OCR as accurate
            needs_confirmation = (
                confidence < self.confidence_threshold
                or not extracted_text
            )

            return ScreenshotIngestionResult(
                input_type="SCREENSHOT",
                extracted_text=extracted_text,
                ocr_confidence=confidence,
                provider=provider,
                needs_confirmation=needs_confirmation,
            )

        finally:
            # 6. Delete temporary file after processing
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning("Failed to remove temporary OCR file %s: %s", temp_path, str(e))

    def _execute_ocr_with_fallback(self, image_path: str) -> OCRRawResult:
        """
        Executes primary OCR (Tesseract). If confidence is below threshold or empty,
        falls back to secondary engine (Vision OCR).
        """
        # Run primary engine (Tesseract)
        primary_result = self.primary_provider.extract_text(image_path)
        logger.info(
            "Primary OCR (%s) executed: confidence=%.2f, words=%d",
            primary_result.provider,
            primary_result.confidence,
            primary_result.word_count,
        )

        # If primary has good confidence and non-empty text, accept it
        if primary_result.confidence >= self.confidence_threshold and primary_result.text.strip():
            return primary_result

        # Fallback to Vision OCR if primary confidence is poor
        if self.fallback_provider:
            logger.info(
                "Primary OCR confidence (%.2f) below threshold (%.2f); falling back to %s...",
                primary_result.confidence,
                self.confidence_threshold,
                self.fallback_provider.provider_name,
            )
            fallback_result = self.fallback_provider.extract_text(image_path)
            logger.info(
                "Fallback OCR (%s) executed: confidence=%.2f, words=%d",
                fallback_result.provider,
                fallback_result.confidence,
                fallback_result.word_count,
            )

            if fallback_result.confidence > primary_result.confidence and fallback_result.text.strip():
                return fallback_result

        # Return primary if fallback didn't yield better results
        return primary_result


screenshot_ingestion_service = ScreenshotIngestionService()
