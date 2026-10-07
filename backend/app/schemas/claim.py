from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, model_validator
from app.schemas.enums import ConfidenceLevel, Language, TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem


class ExtractedClaim(BaseModel):
    """An individual atomic factual proposition extracted from citizen input."""
    claim_number: int = Field(..., ge=1, description="Sequential index of claim in message")
    claim_text: str = Field(..., min_length=5, description="Isolated factual assertion in standard language")
    original_language_text: Optional[str] = Field(None, description="Original vernacular assertion (Hindi/Marathi)")
    language: Language = Field(default=Language.EN, description="Primary language of claim")
    category: Optional[str] = Field(None, description="Scheme, Finance, Transportation, Education, Public Health")


class AtomicClaim(BaseModel):
    """
    An individual atomic factual claim extracted from citizen input.
    Guarantees:
    - Verbatim preserved original wording
    - Clear distinction between facts, opinions, predictions, and questions
    - Language-neutral fact slots (entities, numbers, dates, locations, temporal_expression)
    """
    claim_id: str = Field(..., description="Unique claim identifier, e.g. 'clm_001'")
    original_text: str = Field(..., description="Preserved verbatim source wording from the user message")
    text: Optional[str] = Field(None, description="Verbatim claim text (mirror of original_text for spec compatibility)")
    normalized_claim: str = Field(..., description="Standardized, self-contained canonical factual proposition")
    language: str = Field(default="en", description="Detected language code (en, hi, mr)")
    entities: List[str] = Field(default_factory=list, description="Extracted named entities, institutions, and platforms")
    numbers: List[Union[int, float, str]] = Field(default_factory=list, description="Extracted numerical figures and percentages")
    dates: List[str] = Field(default_factory=list, description="Extracted calendar dates, relative days, and deadlines")
    locations: List[str] = Field(default_factory=list, description="Extracted geographic locations and jurisdictions")
    temporal_expression: Optional[str] = Field(None, description="Extracted temporal phrase (e.g. 'from tomorrow')")
    claim_type: str = Field(default="policy", description="Categorization: policy, financial, health, opinion, prediction, question, etc.")
    check_worthiness: bool = Field(default=True, description="Whether claim is check-worthy (false for opinions, predictions, questions)")

    @model_validator(mode="after")
    def sync_text_fields(self) -> "AtomicClaim":
        if not self.text:
            self.text = self.original_text
        elif not self.original_text:
            self.original_text = self.text
        return self

    def to_extracted_claim(self, claim_number: int = 1) -> ExtractedClaim:
        """Converts to backward-compatible ExtractedClaim for downstream verification engine."""
        return ExtractedClaim(
            claim_number=claim_number,
            claim_text=self.normalized_claim or self.original_text,
            original_language_text=self.original_text,
            language=Language(self.language) if self.language in ["en", "hi", "mr"] else Language.EN,
            category=self.claim_type,
        )


class AtomicClaimsOutput(BaseModel):
    """Structured LLM output container for extracted atomic claims."""
    claims: List[AtomicClaim] = Field(default_factory=list, description="List of atomic claims")


class ClaimExtractionInput(BaseModel):
    """Input payload for atomic claim extraction."""
    text: str = Field(..., min_length=1, description="Citizen forward or message to decompose")
    is_demo: bool = Field(default=False, description="Whether to run in demo/offline mode")


class ClaimResult(BaseModel):
    """The complete verified result for an individual atomic claim."""
    id: str = Field(..., description="Unique claim ID (e.g. CLM-8941-1)")
    claim_number: int = Field(..., ge=1)
    claim_text: str = Field(..., description="The audited assertion")
    original_language_text: Optional[str] = None
    language: Language = Language.EN
    verdict: Verdict = Field(..., description="Deterministic decision from 5 canonical verdicts")
    confidence: Union[ConfidenceLevel, float, str] = Field(..., description="Categorical confidence rating (HIGH, MEDIUM, LOW) or numeric percentage")
    confidence_level: Optional[ConfidenceLevel] = Field(default=None, description="Categorical confidence rating: HIGH, MEDIUM, LOW")
    summary: str = Field(..., description="Clear human-readable reason for verdict")
    detailed_analysis: str = Field(..., description="Forensic evidential reasoning and legal citation context")
    temporal_status: TemporalStatus = Field(default=TemporalStatus.CURRENT)
    rule_matched: str = Field(..., description="Deterministic rule name that triggered verdict")
    rule_trace: List[str] = Field(
        default_factory=list,
        description="Explicit deterministic rule trace for frontend/admin dashboard audit display",
    )
    counter_evidence_summary: Optional[str] = None
    source_citations: List[EvidenceItem] = Field(default_factory=list)
