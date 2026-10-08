from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field


class TTSResult(BaseModel):
    """Result data structure for synthesized speech output."""
    success: bool = Field(..., description="Whether voice synthesis succeeded")
    audio_path: Optional[str] = Field(default=None, description="Local filesystem path to generated audio file")
    audio_bytes: Optional[bytes] = Field(default=None, description="Raw binary audio bytes")
    audio_url: Optional[str] = Field(default=None, description="Public web URL to audio stream/file")
    format: str = Field(default="mp3", description="Audio format container (mp3, wav, etc.)")
    language: str = Field(default="en", description="Normalized target language code (en, hi, mr)")
    provider: str = Field(default="none", description="TTS provider name (e.g. sarvam)")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Synthesis duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Diagnostic error reason if synthesis failed")


class TTSProvider(ABC):
    """Abstract interface for Text-to-Speech synthesis engines."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns canonical provider identifier."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Indicates whether credentials/endpoint for this provider are configured."""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        language: str = "en",
        output_path: Optional[str] = None,
    ) -> TTSResult:
        """
        Synthesizes text explanation into an audio file.
        Must never throw unhandled exceptions to callers; return TTSResult with success=False on failure.
        """
        pass
