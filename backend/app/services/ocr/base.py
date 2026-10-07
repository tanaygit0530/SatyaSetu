from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class OCRRawResult(BaseModel):
    """Raw output from an OCR engine execution."""
    text: str = Field(default="", description="Recognized character text")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized confidence [0.0 - 1.0]")
    provider: str = Field(..., description="Provider identifier (e.g. tesseract, vision)")
    word_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OCRProvider(ABC):
    """Abstract interface for optical character recognition engines."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical provider name."""
        pass

    @abstractmethod
    def extract_text(self, image_path: str) -> OCRRawResult:
        """
        Executes OCR on an image file path and returns recognized text
        alongside a normalized confidence rating [0.0 - 1.0].
        """
        pass
