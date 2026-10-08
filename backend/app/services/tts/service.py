import os
import time
import uuid
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.core import MetricRecord, VerificationResult
from app.services.localization import localization_service
from app.services.tts.base import TTSProvider, TTSResult
from app.services.tts.sarvam_provider import SarvamTTSProvider


class TTSService:
    """
    Optional Voice/TTS Output Service.

    CRITICAL INVARIANTS:
    1. Voice output is NEVER a hard dependency for verification.
    2. If TTS fails, always gracefully return the text response only.
    3. Metrics telemetry tracks:
       - tts_success
       - tts_failure
       - language
       - latency
    """

    def __init__(
        self,
        provider: Optional[TTSProvider] = None,
        metrics_repo: Optional[MetricsRepository] = None,
        base_public_url: Optional[str] = None,
    ):
        self.provider = provider or SarvamTTSProvider()
        self.metrics_repo = metrics_repo or MetricsRepository()
        self.base_public_url = base_public_url or getattr(settings, "BASE_PUBLIC_URL", "https://sachcheck.in")

    def synthesize_explanation(
        self,
        explanation: str,
        language: str = "en",
        output_path: Optional[str] = None,
    ) -> TTSResult:
        """
        Synthesizes the final explanation into an audio file.
        Tracks tts_success, tts_failure, language, and latency metrics.
        """
        norm_lang = localization_service.normalize_language(language)
        start_time = time.perf_counter()

        # Execute synthesis through provider
        res = self.provider.synthesize(
            text=explanation,
            language=norm_lang,
            output_path=output_path,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        res.latency_ms = latency_ms

        if res.success:
            # Generate public playback URL
            if res.audio_path and not res.audio_url:
                filename = os.path.basename(res.audio_path)
                res.audio_url = f"{self.base_public_url}/media/audio/{filename}"

            # Track tts_success
            self._record_metric(
                metric_name="tts_success",
                value=1.0,
                dimensions={
                    "language": norm_lang,
                    "provider": self.provider.provider_name,
                },
            )
            # Track latency
            self._record_metric(
                metric_name="latency",
                value=latency_ms,
                dimensions={
                    "operation": "tts",
                    "language": norm_lang,
                    "provider": self.provider.provider_name,
                    "status": "success",
                },
            )
        else:
            # Track tts_failure
            self._record_metric(
                metric_name="tts_failure",
                value=1.0,
                dimensions={
                    "language": norm_lang,
                    "provider": self.provider.provider_name,
                    "error": str(res.error or "unknown_failure")[:80],
                },
            )
            # Track latency
            self._record_metric(
                metric_name="latency",
                value=latency_ms,
                dimensions={
                    "operation": "tts",
                    "language": norm_lang,
                    "provider": self.provider.provider_name,
                    "status": "failed",
                },
            )

        return res

    def attach_voice_to_verification_result(
        self,
        verification_result: VerificationResult,
        language: Optional[str] = None,
    ) -> VerificationResult:
        """
        Applies TTS as an optional output layer to a completed VerificationResult.

        Workflow:
        Verification succeeds
        ↓
        text explanation generated
        ↓
        TTS succeeds -> attach voice
        If TTS fails -> keep text only
        """
        # Determine explanation text to voice
        explanation_text = ""
        target_lang = language or verification_result.language or "en"

        if verification_result.claims and len(verification_result.claims) > 0:
            first_claim = verification_result.claims[0]
            explanation_text = first_claim.explanation or ""
            target_lang = getattr(first_claim, "language", None) or target_lang
        elif verification_result.summary:
            explanation_text = verification_result.summary

        if not explanation_text:
            verification_result.tts_success = False
            return verification_result

        # Attempt TTS
        tts_res = self.synthesize_explanation(
            explanation=explanation_text,
            language=target_lang,
        )

        if tts_res.success:
            verification_result.audio_file = tts_res.audio_path
            verification_result.audio_url = tts_res.audio_url
            verification_result.tts_success = True
            if verification_result.claims:
                verification_result.claims[0].audio_file = tts_res.audio_path
        else:
            # TTS failed: return text response only.
            verification_result.audio_file = None
            verification_result.audio_url = None
            verification_result.tts_success = False

        return verification_result

    def _record_metric(self, metric_name: str, value: float, dimensions: dict) -> None:
        """Safely records operational metric into repository."""
        try:
            record = MetricRecord(
                metric_id=f"metric_{metric_name}_{uuid.uuid4().hex[:10]}",
                metric_name=metric_name,
                value=float(value),
                dimensions=dimensions,
            )
            self.metrics_repo.record_metric(record)
        except Exception as e:
            logger.warning("Could not record %s metric: %s", metric_name, e)


# Global singleton instance
tts_service = TTSService()
