from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class STTRawResult(BaseModel):
    """Raw transcription output from an STT engine."""
    transcript: str = Field(default="", description="Transcribed text from speech")
    language: str = Field(default="en", description="Detected language code (hi, mr, en, etc.)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score [0.0 - 1.0]")
    provider: str = Field(..., description="Provider identifier (e.g. sarvam)")
    is_uncertain: bool = Field(default=False, description="Flag indicating noisy or uncertain audio")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text transcription engines."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical provider name."""
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language_hint: Optional[str] = None,
    ) -> STTRawResult:
        """
        Transcribes audio file into text proposition, detecting language
        and computing confidence score.
        """
        pass
