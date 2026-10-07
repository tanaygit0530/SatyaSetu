from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SourceTierLevel(IntEnum):
    """
    Evidentiary precedence tiers for the SachCheck Source Registry:
    - Tier 1: Official government sources, official agencies, and official organizations.
    - Tier 2: Reputable fact-checking organizations and high-quality established news sources.
    - Tier 3: Other useful sources.
    """
    TIER_1_OFFICIAL = 1
    TIER_2_REPUTABLE = 2
    TIER_3_USEFUL = 3


class SourceRecord(BaseModel):
    """
    Authoritative Source Registry entry representing an indexed evidence domain.
    """
    domain: str = Field(..., min_length=2, description="Canonical FQDN domain (e.g. example.gov.in)")
    publisher: str = Field(..., min_length=2, description="Issuing authority or publication organization")
    tier: int = Field(..., ge=1, le=3, description="Evidentiary precedence tier (1, 2, or 3)")
    allowed: bool = Field(default=True, description="Whether this source is authorized for evidentiary citation")
    notes: Optional[str] = Field(default=None, description="Administrative provenance notes or blacklist advisory")
    country: Optional[str] = Field(default="IN", description="Country code (ISO alpha-2)")
    language: Optional[str] = Field(default="all", description="Primary publication language or 'all'")
    last_verified: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of registry verification",
    )

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError(f"Invalid tier: {v}. Must be 1 (Official), 2 (Reputable), or 3 (Useful).")
        return v

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        domain = v.strip().lower()
        # Strip scheme if present
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        # Strip paths / query
        domain = domain.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        # Strip port
        if ":" in domain:
            domain = domain.split(":", 1)[0]
        # Strip leading www.
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.strip(".")


class SourceRankResult(BaseModel):
    """
    Evaluation ranking returned for a given domain/URL to enforce strict evidence precedence.
    Unknown/untrusted sources are flagged with allowed=False and credibility_score=0.0.
    """
    domain: str = Field(..., description="Normalized domain evaluated")
    publisher: Optional[str] = Field(None, description="Identified publisher")
    tier: Optional[int] = Field(None, description="Precedence tier (1, 2, 3, or None if unknown/untrusted)")
    allowed: bool = Field(default=False, description="Whether source is allowed in evidence citations")
    is_trusted: bool = Field(default=False, description="Whether source meets baseline evidentiary credibility")
    is_authoritative: bool = Field(default=False, description="True only for Tier 1 official statutory sources")
    credibility_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Evidentiary weight from 0.0 to 1.0")
    evidence_strength: str = Field(
        default="UNTRUSTED",
        description="Categorical evidence strength: STRONG, MODERATE, WEAK, or UNTRUSTED",
    )
    tier_description: str = Field(..., description="Descriptive tier categorization")
    notes: Optional[str] = Field(None, description="Provenance notes or safety alert")
