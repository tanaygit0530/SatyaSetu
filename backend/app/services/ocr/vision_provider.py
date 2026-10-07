import base64
import os
from typing import Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.services.ocr.base import OCRProvider, OCRRawResult


class VisionOCRProvider(OCRProvider):
    """
    Cloud OCR provider using Google Cloud Vision API.
    Acts as fallback engine for degraded or blurry screenshots.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.GOOGLE_VISION_API_KEY

    @property
    def provider_name(self) -> str:
        return "vision"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def extract_text(self, image_path: str) -> OCRRawResult:
        if not self.is_configured():
            logger.info("Google Vision API key not configured; skipping vision OCR fallback.")
            return OCRRawResult(
                text="",
                confidence=0.0,
                provider=self.provider_name,
                metadata={"status": "not_configured"},
            )

        if not os.path.exists(image_path):
            return OCRRawResult(text="", confidence=0.0, provider=self.provider_name)

        try:
            with open(image_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")

            url = f"https://vision.googleapis.com/v1/images:annotate?key={self._api_key}"
            payload = {
                "requests": [
                    {
                        "image": {"content": content},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    }
                ]
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)

            if response.status_code != 200:
                logger.warning("Vision API request failed with status %d: %s", response.status_code, response.text)
                return OCRRawResult(
                    text="",
                    confidence=0.0,
                    provider=self.provider_name,
                    metadata={"error_status": response.status_code},
                )

            data = response.json()
            responses = data.get("responses", [])
            if not responses:
                return OCRRawResult(text="", confidence=0.0, provider=self.provider_name)

            first_resp = responses[0]
            full_annotation = first_resp.get("fullTextAnnotation", {})
            extracted_text = full_annotation.get("text", "").strip()

            # Vision API page/block confidences
            pages = full_annotation.get("pages", [])
            confidences = [p.get("confidence", 0.95) for p in pages if "confidence" in p]
            avg_conf = sum(confidences) / len(confidences) if confidences else (0.90 if extracted_text else 0.0)

            return OCRRawResult(
                text=extracted_text,
                confidence=min(1.0, max(0.0, float(avg_conf))),
                provider=self.provider_name,
                word_count=len(extracted_text.split()),
                metadata={"engine": "google_cloud_vision"},
            )

        except Exception as e:
            logger.warning("Vision OCR execution error: %s", str(e))
            return OCRRawResult(
                text="",
                confidence=0.0,
                provider=self.provider_name,
                metadata={"error": str(e)},
            )
