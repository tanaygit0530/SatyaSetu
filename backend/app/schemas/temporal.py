from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.enums import TemporalStatus, Verdict


class ExtractedTemporalDates(BaseModel):
    """
    Extracted temporal points of reference:
    - claim_date: Date or temporal anchor expressed in the claim (e.g. '2024', 'currently', 'tomorrow')
    - evidence_date: Date of the primary or latest supporting evidence document
    - effective_date: Date when policy/order became operational
    - expiry_date: Date when policy/order lapsed, discontinued, or superseded
    - current_date: System reference date (never assume every date is current)
    """
    claim_date: Optional[str] = Field(None, description="Temporal anchor expressed in the claim (e.g. '2024')")
    evidence_date: Optional[str] = Field(None, description="Publication or issuance date of evidence document")
    effective_date: Optional[str] = Field(None, description="Operational start date of scheme or order")
    expiry_date: Optional[str] = Field(None, description="Discontinuation, sunset, or expiry date")
    current_date: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Reference system date (e.g. '2026-10-07')",
    )
    is_historical_claim: bool = Field(
        default=False,
        description="True if claim explicitly scopes itself to a past date/event (e.g. 'Government announced X in 2024')",
    )
    is_present_claim: bool = Field(
        default=False,
        description="True if claim asserts current ongoing reality (e.g. 'currently gives', 'active now')",
    )


class TemporalEvidenceItem(BaseModel):
    """
    Evidence item with date information for chronological timeline analysis.
    """
    evidence_id: Optional[str] = Field(None, description="Unique evidence identifier")
    text: str = Field(..., description="Quotation or summary of the evidence")
    date: Optional[str] = Field(None, description="Publication or issuance date (e.g. '2024', '2026')")
    effective_date: Optional[str] = Field(None, description="Effective commencement date if mentioned")
    expiry_date: Optional[str] = Field(None, description="Lapse or discontinuation date if mentioned")


class TemporalVerificationInput(BaseModel):
    """Payload for temporal verification."""
    claim_text: str = Field(..., min_length=3, description="Target claim statement to verify temporally")
    evidence_items: List[TemporalEvidenceItem] = Field(
        default_factory=list,
        description="Chronological evidence items to compare",
    )
    current_date: Optional[str] = Field(
        None,
        description="Optional override for current reference date (default: today's date)",
    )


class TemporalVerificationResult(BaseModel):
    """
    Outcome of temporal verification:
    Explicitly distinguishes TRUE THEN from TRUE NOW.
    """
    temporal_status: TemporalStatus = Field(
        ...,
        description="CURRENT, HISTORICAL_TRUE, EXPIRED, CONTRADICTED_BY_NEWER_EVIDENCE, DATE_UNKNOWN",
    )
    verdict: Verdict = Field(
        ...,
        description="Evidentiary verdict: VERIFIED, OUTDATED, FALSE, CANNOT_BE_CONFIRMED",
    )
    true_then: bool = Field(..., description="Whether the claim assertion was factually true at the past date")
    true_now: bool = Field(..., description="Whether the claim assertion is currently factually true now")
    dates: ExtractedTemporalDates = Field(..., description="Structured extracted dates")
    explanation: str = Field(..., description="Detailed timeline rationale explaining the verdict")
