import base64
import os
import time
import uuid
from typing import Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.tts.base import TTSProvider, TTSResult

# BCP-47 locale code mappings for Sarvam AI
SARVAM_TTS_LANGUAGE_MAP = {
    "hi": "hi-IN",
    "mr": "mr-IN",
    "en": "en-IN",
    "hindi": "hi-IN",
    "marathi": "mr-IN",
    "english": "en-IN",
    "hin": "hi-IN",
    "mar": "mr-IN",
    "eng": "en-IN",
    "hinglish": "hi-IN",
    "hi-in": "hi-IN",
    "mr-in": "mr-IN",
    "en-in": "en-IN",
}


class SarvamTTSProvider(TTSProvider):
    """
    Text-to-Speech synthesis provider backed by Sarvam AI.
    Fine-tuned for Indian vernacular speech (English, Hindi, and Marathi).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        speaker: Optional[str] = None,
        audio_dir: Optional[str] = None,
    ):
        self._api_key = api_key or settings.SARVAM_API_KEY
        self._api_url = api_url or settings.SARVAM_TTS_API_URL
        self._model = model or getattr(settings, "SARVAM_TTS_MODEL", "bulbul:v3")
        self._speaker = speaker or getattr(settings, "SARVAM_TTS_SPEAKER", "shubh")
        self._audio_dir = audio_dir or getattr(settings, "TTS_AUDIO_DIR", "/tmp/sachcheck_audio")

    @property
    def provider_name(self) -> str:
        return "sarvam"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def synthesize(
        self,
        text: str,
        language: str = "en",
        output_path: Optional[str] = None,
    ) -> TTSResult:
        """
        Synthesizes citizen explanation into speech audio.
        Returns TTSResult with audio file on success, or graceful error description on failure.
        Never throws unhandled exceptions to callers.
        """
        start_time = time.perf_counter()
        clean_text = (text or "").strip()
        norm_lang = (language or "en").lower().strip()
        sarvam_lang = SARVAM_TTS_LANGUAGE_MAP.get(norm_lang, "en-IN")

        if not clean_text:
            return TTSResult(
                success=False,
                error="Empty text provided for synthesis",
                language=norm_lang,
                provider=self.provider_name,
                latency_ms=0.0,
            )

        if not self.is_configured():
            logger.info("Sarvam TTS API key not configured; returning unconfigured degradation.")
            return TTSResult(
                success=False,
                error="Sarvam TTS API key not configured",
                language=norm_lang,
                provider=self.provider_name,
                latency_ms=0.0,
            )

        headers = {
            "api-subscription-key": self._api_key,
            "Content-Type": "application/json",
        }

        # Multi-spec payload compatible with Sarvam bulbul v1, v2, and v3 APIs
        payload = {
            "text": clean_text,
            "inputs": [clean_text],
            "target_language_code": sarvam_lang,
            "language_code": sarvam_lang,
            "model": self._model,
            "speaker": self._speaker,
            "output_audio_codec": "mp3",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self._api_url,
                    headers=headers,
                    json=payload,
                )

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if response.status_code != 200:
                logger.warning(
                    "Sarvam TTS API returned status %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return TTSResult(
                    success=False,
                    error=f"Sarvam TTS HTTP {response.status_code}: {response.text[:120]}",
                    language=norm_lang,
                    provider=self.provider_name,
                    latency_ms=latency_ms,
                )

            res_json = response.json()
            # Extract base64 audio string from audios list or audio string
            audio_b64: Optional[str] = None
            if "audios" in res_json and isinstance(res_json["audios"], list) and len(res_json["audios"]) > 0:
                audio_b64 = res_json["audios"][0]
            elif "audio" in res_json and isinstance(res_json["audio"], str):
                audio_b64 = res_json["audio"]

            if not audio_b64:
                return TTSResult(
                    success=False,
                    error="No audio stream received in Sarvam TTS response",
                    language=norm_lang,
                    provider=self.provider_name,
                    latency_ms=latency_ms,
                )

            # Decode base64 audio bytes
            audio_bytes = base64.b64decode(audio_b64)

            # Resolve output file path
            final_output_path = output_path
            if not final_output_path:
                os.makedirs(self._audio_dir, exist_ok=True)
                filename = f"tts_{norm_lang}_{uuid.uuid4().hex[:12]}.mp3"
                final_output_path = os.path.join(self._audio_dir, filename)
            else:
                os.makedirs(os.path.dirname(os.path.abspath(final_output_path)), exist_ok=True)

            with open(final_output_path, "wb") as f:
                f.write(audio_bytes)

            logger.info(
                "Successfully synthesized voice (%s) to %s (size: %d bytes, latency: %.1fms)",
                norm_lang,
                final_output_path,
                len(audio_bytes),
                latency_ms,
            )

            return TTSResult(
                success=True,
                audio_path=final_output_path,
                audio_bytes=audio_bytes,
                format="mp3",
                language=norm_lang,
                provider=self.provider_name,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning("Sarvam TTS execution error: %s", str(e))
            return TTSResult(
                success=False,
                error=str(e),
                language=norm_lang,
                provider=self.provider_name,
                latency_ms=latency_ms,
            )
