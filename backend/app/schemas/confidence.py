from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.schemas.enums import ConfidenceLevel, ContradictionStrength, SourceTier, TemporalStatus


class ConfidenceFactorsBreakdown(BaseModel):
    """Internal granular factor scores normalized to [0.0 - 1.0]."""
    source_credibility: float = Field(..., ge=0.0, le=1.0)
    source_agreement: float = Field(..., ge=0.0, le=1.0)
    source_relevance: float = Field(..., ge=0.0, le=1.0)
    recency: float = Field(..., ge=0.0, le=1.0)
    retrieval_quality: float = Field(..., ge=0.0, le=1.0)
    contradiction_strength: float = Field(..., ge=0.0, le=1.0)
    ambiguity: float = Field(..., ge=0.0, le=1.0)
    evidence_quantity: float = Field(..., ge=0.0, le=1.0)
    composite_score: float = Field(..., ge=0.0, le=1.0)


class ConfidenceInput(BaseModel):
    """
    Deterministic confidence calculation input.
    Accepts explicit qualitative/quantitative factors or raw domain objects.
    Strictly evaluated without calling an LLM.
    """
    source_credibility: Optional[Union[float, str, SourceTier]] = Field(
        None,
        description="Credibility score [0.0-1.0], rating string (HIGH/MEDIUM/LOW), or SourceTier",
    )
    source_agreement: Optional[Union[float, str]] = Field(
        None,
        description="Agreement ratio [0.0-1.0] or qualitative rating (e.g. UNANIMOUS, CONFLICTING)",
    )
    source_relevance: Optional[Union[float, str]] = Field(
        None,
        description="Relevance rating [0.0-1.0] or string (HIGH, MEDIUM, LOW, IRRELEVANT)",
    )
    recency: Optional[Union[float, str, TemporalStatus]] = Field(
        None,
        description="Recency score [0.0-1.0], TemporalStatus, or rating string (CURRENT, OUTDATED)",
    )
    retrieval_quality: Optional[Union[float, str]] = Field(
        None,
        description="Retrieval quality score [0.0-1.0] or rating (HIGH, MEDIUM, POOR)",
    )
    contradiction_strength: Optional[Union[float, str, ContradictionStrength]] = Field(
        None,
        description="Strength of contradiction [0.0-1.0] or ContradictionStrength",
    )
    ambiguity: Optional[Union[float, str]] = Field(
        None,
        description="Ambiguity penalty [0.0-1.0] or rating string (LOW, MEDIUM, HIGH)",
    )
    evidence_quantity: Optional[int] = Field(
        None,
        ge=0,
        description="Count of validated evidence items cited",
    )

    # Optional domain objects to auto-extract factors if not explicitly passed
    claim: Optional[Any] = None
    evidence_list: Optional[List[Any]] = None
    evidence_judgments: Optional[List[Any]] = None
    temporal_status: Optional[Union[TemporalStatus, str]] = None


class ConfidenceOutput(BaseModel):
    """
    Output for confidence calculation.
    Exposes strictly HIGH, MEDIUM, or LOW.
    Fake precision (e.g. 0.9738421) is kept internal.
    """
    confidence: ConfidenceLevel = Field(..., description="Categorical confidence rating: HIGH, MEDIUM, LOW")
    internal_score: Optional[float] = Field(
        None,
        description="Internal continuous score [0.0 - 1.0], not displayed to standard citizens",
    )
    factors_breakdown: Optional[ConfidenceFactorsBreakdown] = None
    reasoning: Optional[str] = None


class ClaimConfidenceItem(BaseModel):
    """Confidence profile for an individual atomic claim in a message."""
    claim_id: str = Field(..., description="Unique claim identifier (e.g. CLM-1)")
    confidence: ConfidenceLevel = Field(..., description="Computed confidence rating (HIGH, MEDIUM, LOW)")
    is_important: bool = Field(
        default=True,
        description="Whether this is an important/check-worthy claim that limits overall confidence",
    )
    claim_text: Optional[str] = None


class MessageConfidenceInput(BaseModel):
    """Intake payload for aggregating message-level confidence across claims."""
    claims: List[ClaimConfidenceItem] = Field(
        ...,
        min_length=1,
        description="List of evaluated atomic claims with importance flags",
    )


class MessageConfidenceOutput(BaseModel):
    """
    Aggregated confidence for an entire user forward or message.
    Limited by the weakest important claim.
    """
    overall_confidence: ConfidenceLevel = Field(..., description="HIGH, MEDIUM, or LOW")
    weakest_claim_id: Optional[str] = Field(
        None,
        description="ID of the weakest important claim that bottlenecked overall confidence",
    )
    evaluated_claims_count: int = Field(..., ge=0)
    important_claims_count: int = Field(..., ge=0)
    rule_applied: str = Field(
        default="WEAKEST_IMPORTANT_CLAIM_LIMITATION",
        description="Rule guiding aggregate message confidence",
    )
