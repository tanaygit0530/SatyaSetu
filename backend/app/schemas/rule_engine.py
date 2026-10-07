from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.schemas.claim import ExtractedClaim
from app.schemas.enums import SourceTier, TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem, LockedEvidenceItem
from app.schemas.judge import EvidenceJudgeAssessment


class VerdictEngineInput(BaseModel):
    """
    Structured input for the deterministic verdict engine.
    The verdict engine MUST NOT call an LLM.
    """
    claim: Union[ExtractedClaim, str] = Field(..., description="Target claim assertion")
    validated_evidence: List[Union[EvidenceItem, LockedEvidenceItem, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Validated evidence citations grounded in statutory sources",
    )
    evidence_judgments: Optional[List[EvidenceJudgeAssessment]] = Field(
        None,
        description="Stance assessments produced by the sandboxed evidence judge",
    )
    temporal_status: Optional[TemporalStatus] = Field(
        None,
        description="Chronological status: CURRENT, HISTORICAL_TRUE, EXPIRED, CONTRADICTED_BY_NEWER_EVIDENCE, DATE_UNKNOWN",
    )
    source_tiers: Optional[List[int]] = Field(
        None,
        description="Precedence tiers of participating sources (1=Primary Statutory, 2=Regulatory, 3=Reputable)",
    )
    contradiction_strength: Optional[str] = Field(
        None,
        description="Strength of contradiction if present: HIGH, MEDIUM, LOW, NONE",
    )
    agreement: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Proportion of agreeing sources (0.0 = total disagreement, 1.0 = total consensus)",
    )
    recency: Optional[Union[str, float, bool]] = Field(
        None,
        description="Recency marker ('CURRENT', 'RECENT', True, or days)",
    )
    retrieval_quality: Optional[Union[str, float]] = Field(
        None,
        description="Quality rating of retrieval pipeline ('HIGH', 'MEDIUM', 'LOW', 'POOR' or score 0.0-1.0)",
    )
