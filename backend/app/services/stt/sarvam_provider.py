import os
from typing import Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.stt.base import STTProvider, STTRawResult


# Map vernacular shortcodes to Sarvam AI BCP-47 locale tags
SARVAM_LANGUAGE_MAP = {
    "hi": "hi-IN",
    "mr": "mr-IN",
    "en": "en-IN",
    "hinglish": "hi-IN",  # Sarvam Saaras/Saarika v2 handles Hinglish under hi-IN
    "hi-in": "hi-IN",
    "mr-in": "mr-IN",
    "en-in": "en-IN",
}


class SarvamSTTProvider(STTProvider):
    """
    Speech-to-Text provider backed by Sarvam AI.
    Specifically fine-tuned for Indian languages: Hindi, Marathi, English, and Hinglish.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self._api_key = api_key or settings.SARVAM_API_KEY
        self._api_url = api_url or settings.SARVAM_API_URL

    @property
    def provider_name(self) -> str:
        return "sarvam"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def transcribe(
        self,
        audio_path: str,
        language_hint: Optional[str] = None,
    ) -> STTRawResult:
        """
        Executes Sarvam AI speech-to-text on the provided audio file path.
        Never invents missing speech; returns graceful degradation on failure.
        """
        if not self.is_configured():
            logger.info("Sarvam API key not configured; returning graceful degradation.")
            return STTRawResult(
                transcript="",
                language=language_hint or "en",
                confidence=0.0,
                provider=self.provider_name,
                is_uncertain=True,
                metadata={"status": "not_configured"},
            )

        if not os.path.exists(audio_path):
            logger.error("Audio file does not exist: %s", audio_path)
            return STTRawResult(
                transcript="",
                language="en",
                confidence=0.0,
                provider=self.provider_name,
                is_uncertain=True,
                metadata={"error": "file_not_found"},
            )

        # Resolve language code
        norm_hint = (language_hint or "").lower().strip()
        sarvam_lang = SARVAM_LANGUAGE_MAP.get(norm_hint, "unknown")

        headers = {
            "api-subscription-key": self._api_key,
        }

        try:
            with open(audio_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(audio_path), audio_file, "audio/wav"),
                }
                data = {
                    "model": "saarika:v2",
                }
                if sarvam_lang != "unknown":
                    data["language_code"] = sarvam_lang

                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        self._api_url,
                        headers=headers,
                        files=files,
                        data=data,
                    )

            if response.status_code != 200:
                logger.warning(
                    "Sarvam STT returned status %d: %s",
                    response.status_code,
                    response.text,
                )
                return STTRawResult(
                    transcript="",
                    language=language_hint or "en",
                    confidence=0.0,
                    provider=self.provider_name,
                    is_uncertain=True,
                    metadata={"http_status": response.status_code},
                )

            res_json = response.json()
            transcript = res_json.get("transcript", "").strip()
            detected_lang = res_json.get("language_code", sarvam_lang).split("-")[0]

            # If empty transcript or silence, never invent speech
            if not transcript:
                return STTRawResult(
                    transcript="",
                    language=detected_lang or "en",
                    confidence=0.0,
                    provider=self.provider_name,
                    is_uncertain=True,
                    metadata={"status": "silence_or_empty"},
                )

            # Sarvam doesn't always provide word-level score; default to high baseline when clean
            confidence = float(res_json.get("confidence", 0.92))

            return STTRawResult(
                transcript=transcript,
                language=detected_lang,
                confidence=min(1.0, max(0.0, confidence)),
                provider=self.provider_name,
                is_uncertain=confidence < settings.STT_CONFIDENCE_THRESHOLD,
                metadata={"model": "saarika:v2"},
            )

        except Exception as e:
            # Graceful degradation: never crash on external API failure
            logger.warning("Sarvam STT execution failed: %s", str(e))
            return STTRawResult(
                transcript="",
                language=language_hint or "en",
                confidence=0.0,
                provider=self.provider_name,
                is_uncertain=True,
                metadata={"error": str(e)},
            )
