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
