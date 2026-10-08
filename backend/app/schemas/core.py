import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Union
from dateutil.parser import parse as parse_date
from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.enums import (
    ConfidenceLevel,
    FeedbackType,
    InputType,
    ProcessingStatus,
    TemporalStatus,
    UserRole,
    Verdict,
)


class User(BaseModel):
    """User representation for citizens and audit desk investigators."""
    user_id: str = Field(..., min_length=2, description="Unique user identifier")
    phone_number: Optional[str] = Field(None, description="E.164 formatted phone number")
    email: Optional[str] = Field(None, description="Email address")
    role: UserRole = Field(default=UserRole.CITIZEN, description="Assigned authorization role")
    language: str = Field(default="en", description="Preferred display language (en, hi, mr)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not re.match(r"^\+?[1-9]\d{7,14}$", v):
                raise ValueError(f"Invalid phone number format: '{v}'")
        return v


class Input(BaseModel):
    """Submitted citizen input artifact metadata and raw content."""
    input_id: str = Field(..., min_length=2, description="Unique input identifier")
    input_type: InputType = Field(..., description="Format channel")
    raw_content: str = Field(..., min_length=1, description="Raw forwarded text or media reference")
    media_url: Optional[str] = Field(None, description="Storage location of media file if binary input")
    file_name: Optional[str] = Field(None, description="Original filename")
    file_size_bytes: Optional[int] = Field(None, ge=0, description="Payload size in bytes")
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("raw_content")
    @classmethod
    def validate_content_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Input content cannot be empty or whitespace only.")
        return v.strip()


class Claim(BaseModel):
    """Atomic factual proposition extracted from citizen input."""
    claim_id: str = Field(..., min_length=2, description="Unique claim identifier (e.g. clm_001)")
    text: str = Field(..., min_length=5, description="Exact claim text")
    language: str = Field(default="en", description="Language code (en, hi, mr)")
    normalized_claim: str = Field(..., description="Standardized canonical statement")
    entities: List[str] = Field(default_factory=list, description="Named entities mentioned in claim")
    dates: List[str] = Field(default_factory=list, description="Extracted dates mentioned in claim")
    numbers: List[Union[int, float, str]] = Field(default_factory=list, description="Extracted numerical figures")
    category: Optional[str] = Field(None, description="Domain category (Education, Finance, Railways, etc.)")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Claim text cannot be empty or blank.")
        return v.strip()


class Evidence(BaseModel):
    """Statutory or official record retrieved to audit a claim."""
    evidence_id: str = Field(..., min_length=2, description="Unique evidence identifier (e.g. ev_001)")
    source_url: str = Field(..., description="Official URL of the publishing repository")
    title: str = Field(..., min_length=2, description="Document title or circular heading")
    publisher: str = Field(..., min_length=2, description="Issuing authority or department")
    source_tier: int = Field(..., description="Precedence tier (1=Primary Statutory, 2=Regulatory, 3=Reputable)")
    published_date: Optional[str] = Field(None, description="Document issuance date (YYYY-MM-DD)")
    retrieved_at: str = Field(..., description="ISO timestamp when evidence was fetched")
    exact_quote: str = Field(..., min_length=1, description="Verbatim quote from official document")
    confidence_score: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("source_tier")
    @classmethod
    def validate_tier(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError(f"Invalid source_tier: {v}. Must be 1, 2, or 3.")
        return v

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v, re.IGNORECASE):
            raise ValueError(f"Invalid source_url: '{v}'. Must be a valid HTTP/HTTPS URL.")
        return v

    @field_validator("published_date", mode="before")
    @classmethod
    def validate_published_date(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, (date, datetime)):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                parsed = parse_date(v)
                return parsed.strftime("%Y-%m-%d")
            except Exception:
                raise ValueError(f"Malformed date format: '{v}'. Expected valid date (e.g. YYYY-MM-DD).")
        raise ValueError(f"Invalid date type: {type(v).__name__}")


class RuleTrace(BaseModel):
    """Audit log entry showing deterministic rule evaluation execution."""
    rule_id: str = Field(..., description="Unique rule identifier (e.g. RULE-FINANCIAL-DISCREPANCY)")
    rule_name: str = Field(..., description="Human-readable rule label")
    passed: bool = Field(..., description="Whether assertion satisfied condition")
    details: Optional[str] = Field(None, description="Diagnostic notes from rule engine")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClaimVerificationResult(BaseModel):
    """Verified claim finding conforming to VerificationOrchestrator specification."""
    claim_id: str = Field(..., min_length=1, description="Unique claim identifier, e.g. 'clm_001'")
    verdict: Verdict = Field(..., description="Canonical verdict from the 5 standard states")
    confidence: Union[ConfidenceLevel, str] = Field(..., description="Confidence rating: HIGH, MEDIUM, LOW")
    explanation: str = Field(..., min_length=1, description="Evidentiary explanation for verdict under 80 words")
    evidence: List[Any] = Field(default_factory=list, description="Validated grounding evidence")
    rule_trace: List[Any] = Field(default_factory=list, description="Deterministic rule audit logs")
    evidence_ids: List[str] = Field(default_factory=list, description="Associated evidence IDs")
    claim_text: Optional[str] = None
    normalized_claim: Optional[str] = None
    temporal_status: Optional[TemporalStatus] = None
    cache_hit: bool = Field(default=False)


class ClaimResult(BaseModel):
    """Audit outcome for an individual atomic claim."""
    claim_id: str = Field(..., min_length=2, description="Claim identifier")
    verdict: Verdict = Field(..., description="Canonical verdict from the 5 standard states")
    confidence: Union[ConfidenceLevel, str] = Field(..., description="Confidence rating or score")
    explanation: str = Field(..., min_length=3, description="Evidentiary explanation for verdict")
    evidence_ids: List[str] = Field(default_factory=list, description="Associated evidence IDs")
    rule_trace: List[RuleTrace] = Field(default_factory=list, description="Deterministic rule audit logs")


class ProcessingStage(BaseModel):
    """Progress tracker step for the verification pipeline."""
    stage: ProcessingStatus = Field(..., description="Current processing stage")
    status: str = Field(default="COMPLETED", description="Stage execution status")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = Field(None, ge=0)
    details: Optional[str] = None


class VerificationResult(BaseModel):
    """Overall verification outcome combining claim results."""
    check_id: str = Field(..., min_length=1, description="Parent check ID")
    claims: List[ClaimVerificationResult] = Field(default_factory=list, description="Verified claims in topological order")
    cache_hit: bool = Field(default=False, description="Whether resolved via Shared Claim Memory")
    processing_time_ms: int = Field(default=0, ge=0, description="Processing duration in milliseconds")
    result_id: Optional[str] = Field(default=None, description="Unique verification result dossier ID")
    overall_verdict: Optional[Verdict] = Field(default=None, description="Aggregate verdict computed across all claims")
    summary: Optional[str] = Field(default=None, description="Citizen-facing summary statement")
    claim_results: Optional[List[ClaimResult]] = Field(default=None, description="Atomic claim findings")
    confidence: Union[ConfidenceLevel, str] = Field(default=ConfidenceLevel.HIGH)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_duration_ms: int = Field(default=0, ge=0)
    is_cached: bool = Field(default=False, description="Whether resolved via rumour memory cache")
    input_type: str = Field(default="TEXT")
    original_content: Optional[str] = None
    language: Optional[str] = None

    @model_validator(mode="after")
    def sync_claims_and_results(self) -> "VerificationResult":
        if not self.result_id:
            self.result_id = f"res_{self.check_id}"
        if not self.claims and self.claim_results:
            converted: List[ClaimVerificationResult] = []
            for cr in self.claim_results:
                if isinstance(cr, ClaimVerificationResult):
                    converted.append(cr)
                elif hasattr(cr, "claim_id"):
                    converted.append(
                        ClaimVerificationResult(
                            claim_id=cr.claim_id,
                            verdict=cr.verdict,
                            confidence=cr.confidence,
                            explanation=getattr(cr, "explanation", getattr(cr, "summary", "")),
                            evidence=getattr(cr, "evidence", getattr(cr, "source_citations", [])),
                            rule_trace=getattr(cr, "rule_trace", []),
                            evidence_ids=getattr(cr, "evidence_ids", []),
                        )
                    )
                elif isinstance(cr, dict):
                    converted.append(ClaimVerificationResult.model_validate(cr))
            self.claims = converted
        elif self.claims and not self.claim_results:
            self.claim_results = [
                ClaimResult(
                    claim_id=c.claim_id,
                    verdict=c.verdict,
                    confidence=c.confidence,
                    explanation=c.explanation,
                    evidence_ids=c.evidence_ids or [getattr(e, "id", f"ev_{i}") for i, e in enumerate(c.evidence)],
                    rule_trace=[
                        RuleTrace(rule_name=r if isinstance(r, str) else str(r), rule_id=f"rule_{i}", passed=True)
                        for i, r in enumerate(c.rule_trace)
                    ] if c.rule_trace and isinstance(c.rule_trace[0], str) else (c.rule_trace or []),
                )
                for c in self.claims
            ]
        if self.overall_verdict is None and self.claims:
            self.overall_verdict = self.claims[0].verdict
        if self.summary is None and self.claims:
            self.summary = self.claims[0].explanation
        self.is_cached = self.cache_hit or self.is_cached
        if not self.processing_duration_ms and self.processing_time_ms:
            self.processing_duration_ms = self.processing_time_ms
        elif not self.processing_time_ms and self.processing_duration_ms:
            self.processing_time_ms = self.processing_duration_ms
        return self


class Check(BaseModel):
    """The complete root record representing an ingested citizen check."""
    check_id: str = Field(..., min_length=2, description="Unique check ID (e.g. SC-2026-8941)")
    user_id: Optional[str] = Field(None, description="Submitting citizen user ID if authenticated")
    input: Input = Field(..., description="Original input content and channel")
    status: ProcessingStatus = Field(default=ProcessingStatus.RECEIVED, description="Pipeline state")
    claims: List[Claim] = Field(default_factory=list, description="Extracted atomic claims")
    stages: List[ProcessingStage] = Field(default_factory=list, description="Execution step timeline")
    result: Optional[VerificationResult] = Field(None, description="Final verification finding if completed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Feedback(BaseModel):
    """Citizen or auditor feedback and dispute submission."""
    feedback_id: str = Field(..., min_length=2)
    check_id: str = Field(..., min_length=2)
    claim_id: Optional[str] = None
    user_id: Optional[str] = None
    feedback_type: FeedbackType = Field(..., description="Feedback category")
    comments: Optional[str] = None
    counter_evidence_urls: List[str] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("counter_evidence_urls")
    @classmethod
    def validate_counter_urls(cls, urls: List[str]) -> List[str]:
        valid_urls = []
        for u in urls:
            u = u.strip()
            if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", u, re.IGNORECASE):
                raise ValueError(f"Invalid counter_evidence_url: '{u}'")
            valid_urls.append(u)
        return valid_urls


class Source(BaseModel):
    """Authoritative registry record for an indexed government repository."""
    source_id: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    domain: str = Field(..., min_length=3)
    source_tier: int = Field(..., description="Precedence rank (1, 2, or 3)")
    category: str = Field(..., description="Repository category (MINISTRY, STATE_GAZETTE, etc.)")
    is_active: bool = Field(default=True)
    records_indexed: int = Field(default=0, ge=0)
    last_crawled_at: Optional[datetime] = None

    @field_validator("source_tier")
    @classmethod
    def validate_tier(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError(f"Invalid source_tier: {v}. Must be 1, 2, or 3.")
        return v


class CacheRecord(BaseModel):
    """Vector and lexical cache record for rumour deduplication."""
    cache_id: str = Field(..., min_length=2)
    content_hash: str = Field(..., min_length=16, description="Cryptographic SHA-256 hash")
    canonical_claim: str = Field(..., min_length=5)
    verdict: Verdict = Field(..., description="Cached canonical verdict")
    verification_result_id: str = Field(..., min_length=2)
    hit_count: int = Field(default=1, ge=1)
    first_cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: Optional[int] = Field(default=604800, ge=0)  # Default 7 days


class ReviewQueueItem(BaseModel):
    """Auditor queue entry for claims needing human verification or dispute resolution."""
    review_id: str = Field(..., min_length=2, description="Unique review task identifier")
    check_id: str = Field(..., min_length=2, description="Associated check ID")
    claim_id: Optional[str] = Field(None, description="Associated claim ID if atomic")
    status: str = Field(default="PENDING", description="Review status: PENDING, IN_PROGRESS, RESOLVED, REJECTED")
    priority: str = Field(default="NORMAL", description="Priority: LOW, NORMAL, HIGH, URGENT")
    assigned_to: Optional[str] = Field(None, description="Auditor user ID")
    reason: Optional[str] = Field(None, description="Reason queued (DISPUTE, LOW_CONFIDENCE, AMBIGUOUS)")
    auditor_notes: Optional[str] = Field(None, description="Audit resolution notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricRecord(BaseModel):
    """Operational and verification pipeline telemetry metric."""
    metric_id: str = Field(..., min_length=2, description="Unique metric record ID")
    metric_name: str = Field(..., min_length=1, description="Metric name (e.g. latency_ms, verification_count)")
    value: float = Field(..., description="Numeric metric measurement")
    dimensions: Dict[str, str] = Field(default_factory=dict, description="Metadata dimensions (e.g. input_type, verdict)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationRun(BaseModel):
    """Benchmark test run assessing algorithmic accuracy on verified datasets."""
    run_id: str = Field(..., min_length=2, description="Unique evaluation experiment ID")
    benchmark_name: str = Field(..., min_length=2, description="Dataset name (e.g. pib_benchmark_v1)")
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Overall accuracy ratio [0-1]")
    sample_count: int = Field(..., ge=1, description="Number of claims evaluated")
    status: str = Field(default="COMPLETED", description="Run status: RUNNING, COMPLETED, FAILED")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Precision, recall, confusion matrix")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
