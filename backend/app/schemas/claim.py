from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.enums import Language, TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem


class ExtractedClaim(BaseModel):
    """An individual atomic factual proposition extracted from citizen input."""
    claim_number: int = Field(..., ge=1, description="Sequential index of claim in message")
    claim_text: str = Field(..., min_length=5, description="Isolated factual assertion in standard language")
    original_language_text: Optional[str] = Field(None, description="Original vernacular assertion (Hindi/Marathi)")
    language: Language = Field(default=Language.EN, description="Primary language of claim")
    category: Optional[str] = Field(None, description="Scheme, Finance, Transportation, Education, Public Health")


class ClaimResult(BaseModel):
    """The complete verified result for an individual atomic claim."""
    id: str = Field(..., description="Unique claim ID (e.g. CLM-8941-1)")
    claim_number: int = Field(..., ge=1)
    claim_text: str = Field(..., description="The audited assertion")
    original_language_text: Optional[str] = None
    language: Language = Language.EN
    verdict: Verdict = Field(..., description="Deterministic decision from 5 canonical verdicts")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Algorithmic certainty percentage")
    summary: str = Field(..., description="Clear human-readable reason for verdict")
    detailed_analysis: str = Field(..., description="Forensic evidential reasoning and legal citation context")
    temporal_status: TemporalStatus = Field(default=TemporalStatus.CURRENT)
    rule_matched: str = Field(..., description="Deterministic rule name that triggered verdict")
    counter_evidence_summary: Optional[str] = None
    source_citations: List[EvidenceItem] = Field(default_factory=list)
