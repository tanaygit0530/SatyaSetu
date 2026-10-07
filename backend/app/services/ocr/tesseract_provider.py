import os
from typing import Optional
from PIL import Image
from app.core.config import settings
from app.core.logging import logger
from app.services.ocr.base import OCRProvider, OCRRawResult

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None


class TesseractOCRProvider(OCRProvider):
    """
    On-device OCR provider using Google Tesseract OCR engine.
    Computes word-level average confidence scores.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self._cmd = tesseract_cmd or settings.TESSERACT_CMD
        if self._cmd and PYTESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = self._cmd

    @property
    def provider_name(self) -> str:
        return "tesseract"

    def extract_text(self, image_path: str) -> OCRRawResult:
        if not PYTESSERACT_AVAILABLE:
            logger.warning("pytesseract is not available in environment.")
            return OCRRawResult(text="", confidence=0.0, provider=self.provider_name)

        if not os.path.exists(image_path):
            logger.error("Image file not found for OCR: %s", image_path)
            return OCRRawResult(text="", confidence=0.0, provider=self.provider_name)

        try:
            with Image.open(image_path) as img:
                # Use image_to_data to extract both text and confidence
                data = pytesseract.image_to_data(
                    img,
                    output_type=pytesseract.Output.DICT,
                )

                words = []
                confidences = []

                n_boxes = len(data.get("text", []))
                for i in range(n_boxes):
                    word = data["text"][i].strip()
                    try:
                        conf = float(data["conf"][i])
                    except (ValueError, TypeError):
                        conf = -1.0

                    # Tesseract assigns -1 to empty/whitespace blocks
                    if word and conf >= 0:
                        words.append(word)
                        confidences.append(conf)

                extracted_text = " ".join(words).strip()
                if confidences:
                    # Tesseract confidence is 0-100; normalize to 0.0-1.0
                    avg_conf = sum(confidences) / len(confidences) / 100.0
                    avg_conf = max(0.0, min(1.0, avg_conf))
                else:
                    avg_conf = 0.0

                return OCRRawResult(
                    text=extracted_text,
                    confidence=avg_conf,
                    provider=self.provider_name,
                    word_count=len(words),
                    metadata={"box_count": n_boxes},
                )

        except Exception as e:
            logger.warning("Tesseract OCR execution error: %s", str(e))
            return OCRRawResult(
                text="",
                confidence=0.0,
                provider=self.provider_name,
                metadata={"error": str(e)},
            )
