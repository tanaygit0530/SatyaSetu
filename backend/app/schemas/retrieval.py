from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.evidence import EvidenceItem


class CandidateEvidence(BaseModel):
    """
    Normalized candidate evidence item retrieved from a search or fact-checking provider.
    """
    url: str = Field(..., description="Canonical source URL")
    title: str = Field(..., description="Page or claim review title")
    snippet: str = Field(default="", description="Text snippet or article abstract")
    publisher: Optional[str] = Field(None, description="Identified publisher name")
    domain: str = Field(..., description="Extracted domain of source")
    tier: Optional[int] = Field(None, description="Source precedence tier (1, 2, 3, or None if unranked)")
    source_type: str = Field(
        default="SEARCH",
        description="Origin provider type: FACT_CHECK, OFFICIAL, NEWS, or SEARCH",
    )
    publish_date: Optional[str] = Field(None, description="Publication or review date")
    rating: Optional[str] = Field(None, description="Fact-checker textual rating if available (e.g. Fake, False)")
    credibility_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Source registry credibility rating")
    is_authoritative: bool = Field(default=False, description="True if source is Tier 1 official body")
    exact_quote: Optional[str] = Field(None, description="Verbatim quote extracted from article text")
    raw_content: Optional[str] = Field(None, description="Fetched body text if available")


class RetrievalPipelineOutput(BaseModel):
    """
    Structured response from the end-to-end evidence retrieval pipeline.
    """
    claim_text: str = Field(..., description="Claim text for which retrieval was executed")
    candidates: List[CandidateEvidence] = Field(
        default_factory=list,
        description="Structured candidate evidence citations sorted by evidentiary precedence",
    )
    evidence_items: List[EvidenceItem] = Field(
        default_factory=list,
        description="Synthesized EvidenceItem records ready for deterministic rule evaluation",
    )
    total_candidates: int = Field(default=0, ge=0)
    fact_check_count: int = Field(default=0, ge=0)
    search_count: int = Field(default=0, ge=0)
    status: str = Field(default="SUCCESS", description="Execution status: SUCCESS, EMPTY, or DEGRADED")


class RetrievalInput(BaseModel):
    """
    Input payload for requesting evidence retrieval for a claim.
    """
    claim_text: str = Field(..., min_length=3, description="Claim statement to retrieve evidence for")
    language: Optional[str] = Field(default=None, description="Optional ISO language hint (e.g. en, hi, mr)")
    max_results: int = Field(default=10, ge=1, le=25, description="Maximum total candidates to gather")
