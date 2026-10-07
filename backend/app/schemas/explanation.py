from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.schemas.enums import TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem, LockedEvidenceItem


class ExplanationInput(BaseModel):
    """
    Input for Explanation Generation.
    Generated AFTER the deterministic verdict has been decided.
    """
    claim: Union[str, Any] = Field(..., description="The atomic claim assertion or Claim object")
    verdict: Verdict = Field(..., description="Canonical verdict (VERIFIED, FALSE, OUTDATED, PARTLY_SUPPORTED, CANNOT_BE_CONFIRMED)")
    validated_evidence: List[Union[EvidenceItem, LockedEvidenceItem, Dict[str, Any]]] = Field(
        default_factory=list,
        description="List of validated, grounded evidence citations",
    )
    rule_trace: List[str] = Field(
        default_factory=list,
        description="Explicit deterministic rule trace tokens",
    )
    temporal_status: TemporalStatus = Field(
        default=TemporalStatus.CURRENT,
        description="Temporal alignment status (CURRENT, HISTORICAL_TRUE, OUTDATED, etc.)",
    )


class ExplanationOutput(BaseModel):
    """
    Output of explanation generation.
    Strictly under 80 words, citizen-friendly, and 100% grounded.
    """
    explanation: str = Field(..., description="Simple explanation under 80 words")
    word_count: int = Field(..., ge=1, le=80, description="Word count (strictly under 80 words)")
    verdict: Verdict = Field(..., description="Verdict explained")
    is_grounded: bool = Field(default=True, description="Whether all factual numbers/dates are strictly grounded")
    used_safe_template: bool = Field(
        default=False,
        description="Whether fallback safe template was used after grounding validation failure",
    )
    regeneration_count: int = Field(
        default=0,
        ge=0,
        le=2,
        description="Number of regeneration attempts performed (max 1 before fallback)",
    )
    grounded_numbers_dates: List[str] = Field(
        default_factory=list,
        description="Permissible factual numbers and dates grounded in claim or evidence",
    )
    unauthorized_numbers_dates: List[str] = Field(
        default_factory=list,
        description="Unauthorized numbers or dates detected (if any rejected candidate)",
    )
    rule_trace: List[str] = Field(
        default_factory=list,
        description="Audit trace forwarded for dashboard display",
    )
