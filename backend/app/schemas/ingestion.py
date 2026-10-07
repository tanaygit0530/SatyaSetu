from typing import Optional
from pydantic import BaseModel, Field


class TextInput(BaseModel):
    """Citizen text ingestion request payload."""
    text: str = Field(..., description="Raw text forward or message to verify")


class TextIngestionResult(BaseModel):
    """Ingested and sanitized text artifact representation."""
    input_type: str = Field(default="TEXT", description="Canonical input modality")
    original_text: str = Field(..., description="Unaltered raw citizen submission")
    normalized_text: str = Field(..., description="Sanitized, Unicode-safe, whitespace-collapsed content")
    content_hash: str = Field(..., description="Deterministic SHA-256 fingerprint")
    language_hint: Optional[str] = Field(default=None, description="Detected script/language hint or null")


class ScreenshotIngestionResult(BaseModel):
    """Ingested screenshot and OCR extraction result."""
    input_type: str = Field(default="SCREENSHOT", description="Canonical input modality")
    extracted_text: str = Field(..., description="Extracted text from image")
    ocr_confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score [0.0 - 1.0]")
    provider: str = Field(..., description="OCR engine provider that produced result")
    needs_confirmation: bool = Field(default=False, description="True if confidence is low, requiring human confirmation")


class VoiceIngestionResult(BaseModel):
    """Ingested voice note and STT transcription result."""
    language: str = Field(..., description="Detected vernacular language code (en, hi, mr)")
    transcript: str = Field(..., description="Transcribed spoken proposition")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Transcription confidence score [0.0 - 1.0]")
    needs_confirmation: bool = Field(default=False, description="True if transcription is ambiguous or uncertain")
    duration_seconds: Optional[float] = Field(None, ge=0.0, description="Audio duration in seconds")
    provider: Optional[str] = Field(default="sarvam", description="STT engine provider")
