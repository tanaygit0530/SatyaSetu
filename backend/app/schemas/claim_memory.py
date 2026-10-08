from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.enums import Verdict


class ClaimMemoryRecord(BaseModel):
    """
    Persistent record stored in Shared Claim Memory (Cloud Firestore).
    Guarantees storage of:
    - claim_hash
    - normalized_claim
    - embedding
    - verdict
    - evidence_ids
    - verified_at
    - expires_at
    - source_versions
    """
    claim_hash: str = Field(..., description="Cryptographic SHA-256 hash of normalized claim")
    normalized_claim: str = Field(..., description="Canonical lowercased stripped claim string")
    embedding: List[float] = Field(..., description="Dense semantic vector embedding")
    verdict: Verdict = Field(..., description="Canonical verdict (VERIFIED, FALSE, etc.)")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of supporting/refuting evidence")
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Cache expiration timestamp for temporal freshness")
    source_versions: Dict[str, str] = Field(default_factory=dict, description="Versions or publication timestamps of cited sources")

    # Optional metadata
    cache_id: str = Field(default="", description="Unique Firestore document identifier")
    hit_count: int = Field(default=1, ge=1, description="Number of times reused")
    last_accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rule_trace: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    confidence: Optional[str] = None


class ClaimMemoryLookupInput(BaseModel):
    """Input payload for querying Shared Claim Memory."""
    claim_text: str = Field(..., min_length=3, description="Incoming claim statement to check")
    current_time: Optional[datetime] = Field(None, description="Optional timestamp for freshness evaluation")
    similarity_threshold: Optional[float] = Field(0.85, ge=0.0, le=1.0, description="L1 semantic threshold")


class ClaimMemoryLookupResult(BaseModel):
    """
    Two-level lookup outcome:
    - L0: Exact normalized claim hash
    - L1: Semantic similarity with temporal & factual safety checks
    """
    hit: bool = Field(..., description="Whether a valid, safe cached result was found")
    level: Optional[str] = Field(None, description="Cache level hit: 'L0', 'L1', or None")
    record: Optional[ClaimMemoryRecord] = None
    similarity: Optional[float] = Field(None, description="Cosine similarity score for L1 lookups")
    reason: str = Field(..., description="Reason for hit or miss (e.g. L0_EXACT_MATCH, STALE_CACHE_EXPIRED)")
    numbers_matched: bool = Field(default=True, description="Whether critical numbers matched")
    dates_matched: bool = Field(default=True, description="Whether critical dates matched")


class ClaimMemoryStoreInput(BaseModel):
    """Input payload for caching verified claims into Shared Claim Memory."""
    claim_text: str = Field(..., min_length=3)
    verdict: Verdict
    evidence_ids: List[str] = Field(default_factory=list)
    ttl_hours: int = Field(default=48, ge=1, description="Time-to-live in hours before cache becomes stale")
    source_versions: Dict[str, str] = Field(default_factory=dict)
    rule_trace: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    confidence: Optional[str] = None
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
