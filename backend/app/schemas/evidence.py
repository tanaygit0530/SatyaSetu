from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from app.schemas.enums import SourceTier


class EvidenceItem(BaseModel):
    """A documentary or statutory citation retrieved from official registries."""
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


class EvidenceInterpretation(BaseModel):
    """Normalized evidence interpretation generated for the deterministic rule engine."""
    supports_claim: bool = Field(default=False, description="Whether the evidence corroborates the statement")
    refutes_claim: bool = Field(default=False, description="Whether the evidence directly contradicts the statement")
    is_temporal_mismatch: bool = Field(default=False, description="Whether document timestamp precedes claim context")
    claimed_amount: Optional[float] = Field(None, description="Extracted numerical or financial figure in claim")
    actual_amount: Optional[float] = Field(None, description="Verified numerical or financial figure in record")
    domain_flagged_malicious: bool = Field(default=False, description="Whether URL/domain is on CERT-In blacklist")
    discrepancy_explanation: Optional[str] = Field(None, description="Detailed explanation of discrepancy")
