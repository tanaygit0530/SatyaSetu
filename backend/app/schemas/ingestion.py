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


class PDFPageText(BaseModel):
    """Extracted text from an individual PDF page."""
    page: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(..., description="Extracted text from this page")
    score: Optional[float] = Field(default=None, description="Claim relevance / ranking score")


class PDFIngestionResult(BaseModel):
    """Result of PDF document ingestion and text extraction."""
    input_type: str = Field(default="PDF", description="Canonical input modality")
    page_count: int = Field(..., ge=0, description="Total number of pages in the PDF")
    text_pages: list[PDFPageText] = Field(default_factory=list, description="Pages containing meaningful text")
    needs_ocr: bool = Field(default=False, description="Flagged true if scanned PDF with missing text layer")
    total_text_length: int = Field(default=0, ge=0, description="Total characters extracted across all pages")
    ranked_claim_pages: Optional[list[int]] = Field(default=None, description="Page numbers ranked by claim relevance")


class URLIngestionInput(BaseModel):
    """Citizen URL submission payload."""
    url: str = Field(..., description="Web link or shortened URL to verify")


class URLIngestionResult(BaseModel):
    """Result of secure URL retrieval, redirect expansion, and article extraction."""
    final_url: str = Field(..., description="Fully resolved destination URL")
    title: str = Field(default="", description="Extracted article or page title")
    publisher: str = Field(default="", description="Publishing entity or domain")
    published_date: Optional[str] = Field(default=None, description="Document issuance date if available")
    text: str = Field(default="", description="Cleaned, readable article body text")
    status: str = Field(default="SUCCESS", description="Ingestion status (SUCCESS, DEAD_PAGE, ERROR)")
