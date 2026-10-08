import io
import os
import tempfile
import wave
from typing import List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.schemas.ingestion import VoiceIngestionResult
from app.services.stt.base import STTProvider, STTRawResult
from app.services.stt.sarvam_provider import SarvamSTTProvider


class VoiceIngestionService:
    """
    Speech and audio ingestion pipeline for citizen WhatsApp voice notes and recordings.
    Enforces MIME validation, 60s max duration limit, audio chunking, STT extraction,
    and confidence uncertainty checks.
    """

    def __init__(
        self,
        provider: Optional[STTProvider] = None,
        max_duration_seconds: Optional[float] = None,
        max_file_size: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ):
        self.provider = provider or SarvamSTTProvider()
        self.max_duration_seconds = max_duration_seconds or settings.MAX_VOICE_DURATION_SECONDS
        self.max_file_size = max_file_size or settings.MAX_VOICE_FILE_SIZE_BYTES
        self.confidence_threshold = confidence_threshold or settings.STT_CONFIDENCE_THRESHOLD

    def validate_mime_magic_bytes(self, data: bytes) -> str:
        """
        Inspects binary magic bytes to ensure payload is a valid audio format.
        Supports WAV, MP3, OGG (WhatsApp voice notes), M4A/AAC, and WebM.
        """
        if len(data) >= 12 and data.startswith(b"RIFF") and b"WAVE" in data[:12]:
            return "audio/wav"

        if len(data) >= 3 and (
            data.startswith(b"ID3")
            or data.startswith(b"\xff\xfb")
            or data.startswith(b"\xff\xf3")
            or data.startswith(b"\xff\xf2")
        ):
            return "audio/mpeg"

        if len(data) >= 4 and data.startswith(b"OggS"):
            return "audio/ogg"

        if len(data) >= 8 and (b"ftyp" in data[:12] or data.startswith(b"\xff\xf1") or data.startswith(b"\xff\xf9")):
            return "audio/mp4"

        if len(data) >= 4 and data.startswith(b"\x1a\x45\xdf\xa3"):
            return "audio/webm"

        # Check common rejected types for actionable error messages
        if data.startswith(b"%PDF"):
            rejected_type = "application/pdf"
        elif data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff"):
            rejected_type = "image"
        else:
            rejected_type = "unknown/unsupported"

        raise InvalidInputException(
            f"Unsupported audio format '{rejected_type}'. Allowed audio formats: WAV, MP3, OGG, M4A, WebM."
        )

    def extract_duration_seconds(self, data: bytes, mime_type: str) -> float:
        """
        Determines audio duration using wave headers or Mutagen stream inspection.
        """
        # 1. WAV stream inspection via stdlib wave
        if mime_type == "audio/wav":
            try:
                with wave.open(io.BytesIO(data)) as w:
                    frames = w.getnframes()
                    rate = w.getframerate()
                    if rate > 0:
                        return float(frames) / float(rate)
            except Exception as e:
                logger.debug("Failed wave duration parse: %s", e)

        # 2. Universal inspection via mutagen
        try:
            from mutagen import File as MutagenFile
            audio_info = MutagenFile(io.BytesIO(data))
            if audio_info is not None and audio_info.info is not None:
                duration = getattr(audio_info.info, "length", 0.0)
                if duration > 0:
                    return float(duration)
        except Exception as e:
            logger.debug("Failed mutagen duration parse: %s", e)

        # Fallback estimation for raw audio if metadata headers are missing
        return 0.0

    def split_chunks_if_needed(
        self,
        audio_data: bytes,
        mime_type: str,
        duration: float,
        chunk_length_seconds: float = 30.0,
    ) -> List[Tuple[bytes, str]]:
        """
        Splits audio data into sequential chunk segments if duration exceeds chunk_length_seconds.
        For WAV files, splits frame-accurately. For other formats or short audio, returns single chunk.
        """
        if duration <= chunk_length_seconds or mime_type != "audio/wav":
            return [(audio_data, mime_type)]

        try:
            with wave.open(io.BytesIO(audio_data)) as w:
                params = w.getparams()
                framerate = params.framerate
                chunk_frames = int(chunk_length_seconds * framerate)

                chunks: List[Tuple[bytes, str]] = []
                while True:
                    frames = w.readframes(chunk_frames)
                    if not frames:
                        break
                    chunk_buf = io.BytesIO()
                    with wave.open(chunk_buf, "wb") as chunk_w:
                        chunk_w.setparams(params)
                        chunk_w.writeframes(frames)
                    chunks.append((chunk_buf.getvalue(), "audio/wav"))
                return chunks if chunks else [(audio_data, mime_type)]
        except Exception as e:
            logger.warning("WAV chunk splitting failed: %s; falling back to full audio.", e)
            return [(audio_data, mime_type)]

    def ingest_voice(
        self,
        audio_bytes: bytes,
        language_hint: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> VoiceIngestionResult:
        """
        Ingests voice note bytes, verifies size and MIME, checks duration <= 60s,
        chunks if needed, transcribes via STTProvider, merges transcripts,
        and flags uncertainty if confidence is low.
        """
        # 1. Validate file size
        if len(audio_bytes) == 0:
            raise InvalidInputException("Uploaded audio recording is empty (0 bytes).")

        if len(audio_bytes) > self.max_file_size:
            raise InvalidInputException(
                f"Audio recording size ({len(audio_bytes)} bytes) exceeds maximum limit "
                f"of {self.max_file_size} bytes."
            )

        # 2. Validate MIME using magic bytes
        mime_type = self.validate_mime_magic_bytes(audio_bytes)

        # 3. Validate audio duration (60 seconds maximum for MVP)
        duration = self.extract_duration_seconds(audio_bytes, mime_type)
        if duration > self.max_duration_seconds:
            raise InvalidInputException(
                f"Audio recording duration ({duration:.1f}s) exceeds the maximum limit "
                f"of {self.max_duration_seconds:.0f} seconds for claim verification."
            )

        # 4. Split into chunks if needed
        chunks = self.split_chunks_if_needed(audio_bytes, mime_type, duration)

        # 5. Process chunks through STTProvider
        transcripts: List[str] = []
        confidences: List[float] = []
        languages: List[str] = []
        is_uncertain_flags: List[bool] = []

        suffix = ".wav" if mime_type == "audio/wav" else ".mp3"

        for idx, (chunk_data, chunk_mime) in enumerate(chunks):
            temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            temp_path = temp_file.name
            try:
                temp_file.write(chunk_data)
                temp_file.close()

                # Execute STT
                stt_res = self.provider.transcribe(temp_path, language_hint=language_hint)

                if stt_res.transcript.strip():
                    transcripts.append(stt_res.transcript.strip())
                    confidences.append(stt_res.confidence)
                    languages.append(stt_res.language)
                is_uncertain_flags.append(stt_res.is_uncertain)

            except Exception as e:
                # Graceful degradation on chunk failure
                logger.warning("Error transcribing audio chunk %d: %s", idx, e)
                is_uncertain_flags.append(True)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception as clean_err:
                        logger.warning("Failed to remove temp audio file: %s", clean_err)

        # 6. Merge transcript
        from app.core.security.prompt_injection import prompt_injection_defense_service
        merged_transcript = prompt_injection_defense_service.disarm_text(" ".join(transcripts))
        detected_language = languages[0] if languages else (language_hint or "en")

        if confidences:
            avg_confidence = round(sum(confidences) / len(confidences), 2)
        else:
            avg_confidence = 0.0

        # Never invent missing speech! If audio was silent or noisy, transcript is empty
        # If confidence is below threshold, or audio was uncertain, mark needs_confirmation = True
        needs_confirmation = (
            avg_confidence < self.confidence_threshold
            or not merged_transcript
            or any(is_uncertain_flags)
        )

        return VoiceIngestionResult(
            language=detected_language,
            transcript=merged_transcript,
            confidence=avg_confidence,
            needs_confirmation=needs_confirmation,
            duration_seconds=round(duration, 2) if duration > 0 else None,
            provider=self.provider.provider_name,
        )


voice_ingestion_service = VoiceIngestionService()
