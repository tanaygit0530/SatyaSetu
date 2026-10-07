from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.enums import ConfidenceLevel, InputType, Language, Verdict
from app.schemas.claim import ClaimResult


class VerificationRequest(BaseModel):
    """Citizen verification intake request."""
    input_type: InputType = Field(default=InputType.TEXT, description="Submission channel")
    content: str = Field(..., min_length=3, max_length=10000, description="Submitted text, transcript, or link URL")
    language: Optional[Language] = Field(default=Language.EN, description="Preferred language")
    client_id: Optional[str] = Field(default="web-portal", description="Originating client interface")
    is_demo: bool = Field(default=False, description="Whether requesting explicitly labeled cached demo data")


class VerificationResponse(BaseModel):
    """Complete structured forensic verification dossier response."""
    id: str = Field(..., description="Unique verification record ID (e.g. SC-2026-8941)")
    public_id: str = Field(..., description="Shareable identifier for public dossier")
    input_type: InputType
    submitted_at: datetime
    completed_at: datetime
    processing_duration_ms: int
    source_origin: str = Field(default="WHATSAPP")
    original_message: str
    overall_verdict: Verdict = Field(..., description="Aggregate verdict computed across atomic claims")
    overall_confidence: Optional[ConfidenceLevel] = Field(
        default=ConfidenceLevel.HIGH,
        description="Overall message confidence rating limited by the weakest important claim",
    )
    verdict_summary: str = Field(..., description="Clear citizen summary in simple language")
    claims: List[ClaimResult] = Field(..., min_length=1)
    cache_hit: bool = Field(default=False)
    cached_from_id: Optional[str] = None
    repository_id: str = Field(default="0x9AF...41B")
    is_demo: bool = Field(default=False, description="Flag explicitly indicating demo cached record")
