from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceStance(str, Enum):
    """
    Allowed stances an evidence item can hold toward a claim:
    - SUPPORTS: Evidence directly substantiates the claim assertion.
    - CONTRADICTS: Evidence directly refutes or disputes the claim assertion.
    - MIXED: Evidence partially confirms but also introduces conflicting nuances.
    - IRRELEVANT: Evidence does not address the claim assertion.
    NOTE: The judge NEVER outputs a TRUE/FALSE verdict.
    """
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    MIXED = "MIXED"
    IRRELEVANT = "IRRELEVANT"


class EvidenceAssessmentLevel(str, Enum):
    """Qualitative grading for relevance and evidential strength."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceJudgeAssessment(BaseModel):
    """
    Structured judgment produced by the Evidence Judge.
    Strictly restricted to stance, relevance, strength, and rationale.
    No TRUE/FALSE verdicts.
    """
    evidence_id: str = Field(..., description="Target evidence item ID (e.g. 'ev_001', 'CIT-01')")
    stance: EvidenceStance = Field(..., description="Stance: SUPPORTS, CONTRADICTS, MIXED, or IRRELEVANT")
    relevance: EvidenceAssessmentLevel = Field(
        default=EvidenceAssessmentLevel.HIGH,
        description="Relevance to claim: HIGH, MEDIUM, or LOW",
    )
    strength: EvidenceAssessmentLevel = Field(
        default=EvidenceAssessmentLevel.HIGH,
        description="Evidential strength: HIGH, MEDIUM, or LOW",
    )
    direct_support: bool = Field(
        default=False,
        description="Whether evidence directly supports the core relationship/fact rather than merely related topic",
    )
    reason: str = Field(..., description="Concise objective rationale explaining the stance")



class JudgeEvidenceInputItem(BaseModel):
    """
    Sandboxed evidence view presented to the Evidence Judge LLM.
    Contains ONLY: evidence_id, exact_quote, source metadata (publisher, tier, publish_date).
    Does NOT contain tool access or verdict instructions.
    """
    evidence_id: str = Field(..., description="Unique evidence ID")
    exact_quote: str = Field(..., description="Validated verbatim quotation")
    publisher: Optional[str] = Field(None, description="Issuing authority or publication")
    source_tier: Optional[int] = Field(None, description="Precedence tier (1, 2, or 3)")
    published_date: Optional[str] = Field(None, description="Date of document issuance")
    domain: Optional[str] = Field(None, description="Origin domain")


class JudgeEvaluationInput(BaseModel):
    """Input payload for the Evidence Judge."""
    claim_text: str = Field(..., min_length=3, description="Target claim text")
    evidence_items: List[JudgeEvidenceInputItem] = Field(
        ...,
        description="Sandboxed validated evidence citations to evaluate",
    )


class JudgeEvaluationOutput(BaseModel):
    """Structured collection of assessments for a claim."""
    claim_text: str = Field(..., description="Claim evaluated")
    assessments: List[EvidenceJudgeAssessment] = Field(
        default_factory=list,
        description="Structured stance assessments per evidence item",
    )
