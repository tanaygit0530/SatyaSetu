from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.enums import SourceTier


class RetrievedSource(BaseModel):
    """
    Stage 1: Retrieved Evidence.
    A document, page, or statutory bulletin fetched from the web, fact-check tool, or official portal.
    """
    source_id: Optional[str] = Field(None, description="Authoritative registry source identifier (e.g. src_npci)")
    url: str = Field(..., description="Canonical source URL (strictly verified, never invented)")
    title: Optional[str] = Field(None, description="Document or article headline")
    publisher: Optional[str] = Field(None, description="Issuing authority or news publication")
    domain: Optional[str] = Field(None, description="Domain name (e.g. npci.org.in)")
    published_date: Optional[str] = Field(None, description="Publication date string (ISO or YYYY-MM-DD)")
    retrieved_date: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when the source was retrieved",
    )
    text: str = Field(..., description="Full text or extracted article body")
    tier: Optional[int] = Field(None, description="Optional precedence tier (1, 2, or 3)")
    is_suspicious: bool = Field(default=False, description="Whether prompt injection or hidden text was detected")
    suspicious_flags: List[str] = Field(default_factory=list, description="Security flags detected in source text/HTML")

    @field_validator("url")
    @classmethod
    def validate_url_present(cls, v: str) -> str:
        clean = v.strip()
        if not clean.startswith("http://") and not clean.startswith("https://"):
            raise ValueError(f"Invalid source URL '{v}'. Must be a valid HTTP/HTTPS URL.")
        return clean


class EvidenceCandidate(BaseModel):
    """
    Stage 2: Candidate Evidence.
    Relevant passages, quotes, and metadata extracted from a retrieved source for a claim.
    CRITICAL: This is candidate evidence and has NOT yet been validated against statutory rules.
    """
    candidate_id: str = Field(..., description="Unique candidate identifier (e.g. cand_001)")
    claim_id: Optional[str] = Field(None, description="Atomic claim identifier")
    claim_text: str = Field(..., description="Target claim statement being evaluated")
    source_id: str = Field(..., description="Stored source identifier (e.g. src_npci, src_pib_gov_in)")
    title: str = Field(..., description="Extracted document title")
    publisher: str = Field(..., description="Extracted publisher name")
    url: str = Field(..., description="Source URL strictly bound to the retrieved document (never invented)")
    published_date: Optional[str] = Field(None, description="Document publication date")
    retrieved_date: str = Field(..., description="Timestamp when original document was fetched")
    relevant_text: str = Field(..., description="Contextual passage or paragraph identified as relevant to the claim")
    candidate_quotes: List[str] = Field(
        default_factory=list,
        description="Candidate quote(s) identified in the passage that directly relate to the claim",
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Semantic or lexical relevance score of the passage to the claim",
    )
    stance_hint: Optional[str] = Field(
        None,
        description="Preliminary stance hint: REFUTES (supports FALSE verdict), SUPPORTS, or NEUTRAL",
    )
    is_validated: bool = Field(
        default=False,
        description="Explicit guarantee: candidate evidence is NOT yet marked as validated evidence",
    )
    validation_notes: Optional[str] = Field(
        default="Candidate evidence pending statutory and temporal rule engine validation.",
        description="Status notes regarding validation stage",
    )
    is_suspicious: bool = Field(default=False, description="Whether prompt injection or hidden text was detected")
    suspicious_flags: List[str] = Field(default_factory=list, description="Security flags detected in candidate text/HTML")


class EvidenceExtractionInput(BaseModel):
    """Input payload for extracting candidate evidence from retrieved sources."""
    claim_text: str = Field(..., min_length=3, description="Claim statement")
    claim_id: Optional[str] = Field("clm_001", description="Claim identifier")
    retrieved_sources: List[RetrievedSource] = Field(
        ...,
        description="List of retrieved documents to extract candidates from",
    )


class EvidenceExtractionOutput(BaseModel):
    """Structured output containing extracted candidate evidence."""
    claim_text: str = Field(..., description="Claim statement")
    candidates: List[EvidenceCandidate] = Field(
        default_factory=list,
        description="Extracted candidate evidence items",
    )
    total_candidates: int = Field(default=0, ge=0)


class EvidenceItem(BaseModel):
    """
    Stage 3: Validated Evidence.
    A statutory citation that has passed validation against government registries.
    """
    id: str = Field(..., description="Unique evidence citation ID (e.g. CIT-01)")
    publisher: str = Field(..., description="Issuing body (e.g. The Gazette of India, PIB Fact Check)")
    domain: str = Field(..., description="Official registrar domain (e.g. egazette.gov.in)")
    title: str = Field(..., description="Document or order title")
    publish_date: Optional[str] = Field(None, description="Document issuance date string (e.g. 2026-09-12)")
    tier: SourceTier = Field(..., description="Precedence tier of source")
    url: str = Field(..., description="Public link to statutory publication")
    archive_url: Optional[str] = Field(None, description="Cryptographic permanent archive URL")
    exact_quote: str = Field(..., description="Verbatim extracted quotation from official record")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Semantic / lexical match score")
    is_authoritative: bool = Field(default=True, description="Whether domain is verified in Government registry")
    is_suspicious: bool = Field(default=False, description="Whether prompt injection or hidden text was detected")
    suspicious_flags: List[str] = Field(default_factory=list, description="Security flags detected in evidence citation")


class EvidenceInterpretation(BaseModel):
    """Normalized evidence interpretation generated for the deterministic rule engine."""
    supports_claim: bool = Field(default=False, description="Whether the evidence corroborates the statement")
    refutes_claim: bool = Field(default=False, description="Whether the evidence directly contradicts the statement")
    is_temporal_mismatch: bool = Field(default=False, description="Whether document timestamp precedes claim context")
    claimed_amount: Optional[float] = Field(None, description="Extracted numerical or financial figure in claim")
    actual_amount: Optional[float] = Field(None, description="Verified numerical or financial figure in record")
    domain_flagged_malicious: bool = Field(default=False, description="Whether URL/domain is on CERT-In blacklist")
    discrepancy_explanation: Optional[str] = Field(None, description="Detailed explanation of discrepancy")
    direct_support: bool = Field(default=False, description="Whether evidence directly substantiates the core relationship/fact")



class LockedEvidenceItem(BaseModel):
    """
    Locked / Grounded Evidence Item.
    Guarantees that exact_quote is verbatim grounded in the stored source text.
    """
    source_url: str = Field(..., description="Canonical source URL")
    evidence_id: Optional[str] = Field(default=None, description="Optional evidence item identifier")
    source_title: str = Field(..., description="Document or article headline")
    publisher: str = Field(..., description="Issuing authority or publisher")
    published_date: Optional[str] = Field(None, description="Publication date string")
    retrieved_at: str = Field(..., description="Timestamp when original document was retrieved")
    source_tier: int = Field(..., description="Precedence tier of source (1, 2, or 3)")
    exact_quote: str = Field(..., description="Verbatim quote strictly grounded in source text")
    source_text_reference: str = Field(..., description="Reference pointer / offset location in the source text")
    claim_relation: str = Field(..., description="Stance or relation to the claim: SUPPORTS, REFUTES, or NEUTRAL")


class GroundingValidationResult(BaseModel):
    """
    Result returned by the Grounding Validator.
    If quote does not exist in stored source text:
    valid is False and reason is 'QUOTE_NOT_FOUND'.
    """
    valid: bool = Field(..., description="Whether quote is strictly grounded in stored source text")
    reason: Optional[str] = Field(None, description="Failure reason (e.g. 'QUOTE_NOT_FOUND') if invalid")
    source_text_reference: Optional[str] = Field(None, description="Reference pointer in source text if grounded")
    locked_evidence: Optional[LockedEvidenceItem] = Field(None, description="Locked evidence item if valid")

