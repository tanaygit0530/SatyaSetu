from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.claim_memory_repository import ClaimMemoryRepository
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.enums import Verdict
from app.schemas.claim_memory import (
    ClaimMemoryLookupInput,
    ClaimMemoryLookupResult,
    ClaimMemoryRecord,
    ClaimMemoryStoreInput,
)
from app.services.claim_memory import SharedClaimMemoryService

client = TestClient(app)


@pytest.fixture
def clean_memory_service():
    """Provides an isolated SharedClaimMemoryService with fresh repositories."""
    mem_repo = ClaimMemoryRepository()
    mem_repo._local_records.clear()
    met_repo = MetricsRepository()
    return SharedClaimMemoryService(memory_repo=mem_repo, metrics_repo=met_repo)


# ==============================================================================
# 1. STORED FIELDS IN SHARED CLAIM MEMORY
# ==============================================================================

def test_store_preserves_all_required_specification_fields(clean_memory_service):
    """
    User Spec Requirement:
    Store:
    claim_hash, normalized_claim, embedding, verdict, evidence_ids,
    verified_at, expires_at, source_versions.
    """
    rec = clean_memory_service.store_claim(
        claim_text="UPI has been banned from tomorrow.",
        verdict=Verdict.FALSE,
        evidence_ids=["ev_npci_01", "ev_pib_02"],
        ttl_hours=48,
        source_versions={"npci.org.in": "v2026.04", "pib.gov.in": "2026-09-12"},
        rule_trace=["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION"],
        explanation="No official announcement of UPI ban.",
        confidence="HIGH",
    )

    assert rec.claim_hash is not None and len(rec.claim_hash) == 64
    assert rec.normalized_claim == "upi has been banned from tomorrow"
    assert rec.embedding is not None and len(rec.embedding) == 256
    assert rec.verdict == Verdict.FALSE
    assert rec.evidence_ids == ["ev_npci_01", "ev_pib_02"]
    assert rec.verified_at is not None
    assert rec.expires_at is not None
    assert rec.expires_at > rec.verified_at
    assert rec.source_versions == {"npci.org.in": "v2026.04", "pib.gov.in": "2026-09-12"}


# ==============================================================================
# 2. LEVEL 0 (L0): EXACT NORMALIZED CLAIM HASH MATCH
# ==============================================================================

def test_l0_exact_match_hit(clean_memory_service):
    """
    L0 exact match:
    Normalizes and hashes claim. If exact hash matches and unexpired -> L0 hit!
    """
    # 1. Store
    clean_memory_service.store_claim(
        claim_text="UPI has been banned from tomorrow.",
        verdict=Verdict.FALSE,
        evidence_ids=["ev_001"],
    )

    # 2. Lookup exact string (with minor formatting difference e.g. uppercase, extra space, punctuation)
    result = clean_memory_service.lookup_claim("  UPI has been banned from tomorrow!  ")
    assert result.hit is True
    assert result.level == "L0"
    assert result.reason == "L0_EXACT_MATCH"
    assert result.similarity == 1.0
    assert result.record is not None
    assert result.record.verdict == Verdict.FALSE
    assert result.record.hit_count == 2


# ==============================================================================
# 3. LEVEL 1 (L1): SEMANTIC SIMILARITY PARAPHRASE MATCH
# ==============================================================================

def test_l1_paraphrase_match_hit(clean_memory_service):
    """
    L1 paraphrase match:
    Cached: 'UPI services are shut down nationwide starting tomorrow.'
    Lookup: 'Nationwide shutdown of UPI has been announced for tomorrow.'
    Semantic embedding similarity >= threshold -> safe L1 hit!
    """
    clean_memory_service.store_claim(
        claim_text="UPI services are shut down nationwide starting tomorrow.",
        verdict=Verdict.FALSE,
        evidence_ids=["ev_001"],
    )

    # Lookup paraphrased wording
    result = clean_memory_service.lookup_claim(
        "Nationwide shutdown of UPI services starting tomorrow.",
        similarity_threshold=0.80,
    )
    assert result.hit is True
    assert result.level == "L1"
    assert result.reason == "L1_SEMANTIC_MATCH"
    assert result.similarity is not None and result.similarity >= 0.80
    assert result.record is not None
    assert result.record.verdict == Verdict.FALSE
    assert result.numbers_matched is True
    assert result.dates_matched is True


# ==============================================================================
# 4. UNRELATED CLAIM (CACHE MISS)
# ==============================================================================

def test_unrelated_claim_results_in_cache_miss(clean_memory_service):
    """
    Unrelated claim:
    Stored: 'UPI is banned from tomorrow.'
    Lookup: 'Chemicals leaked into municipal water tanker in Ward 14.'
    Semantic similarity is low -> Cache miss!
    """
    clean_memory_service.store_claim(
        claim_text="UPI is banned from tomorrow.",
        verdict=Verdict.FALSE,
    )

    result = clean_memory_service.lookup_claim(
        "Chemicals leaked into municipal water tanker in Ward 14.",
    )
    assert result.hit is False
    assert result.level is None
    assert result.reason in ("SIMILARITY_BELOW_THRESHOLD", "CACHE_MISS")


# ==============================================================================
# 5. STALE CACHE (EVIDENCE EXPIRY PASSED)
# ==============================================================================

def test_stale_cache_expiry_passed_requires_rerunning_verification(clean_memory_service):
    """
    User Spec Example:
    Yesterday: 'UPI is banned tomorrow.' Cached: FALSE.
    Today: same exact claim.
    If evidence expiry has passed -> rerun verification (Do NOT reuse blindly!).
    """
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(hours=2)  # Expired 2 hours ago

    # Store with already-expired timestamp
    clean_memory_service.store_claim(
        claim_text="UPI is banned tomorrow.",
        verdict=Verdict.FALSE,
        verified_at=now - timedelta(days=3),
        expires_at=expired_time,
    )

    # Lookup now
    result = clean_memory_service.lookup_claim("UPI is banned tomorrow.", current_time=now)
    assert result.hit is False
    assert result.reason == "STALE_CACHE_EXPIRED"
    assert result.record is not None
    assert result.record.expires_at < now


# ==============================================================================
# 6. CRITICAL FACT SAFETY GUARDRAIL: CHANGED NUMBER
# ==============================================================================

def test_changed_number_rejects_l1_reuse(clean_memory_service):
    """
    Safety Guardrail:
    Cached: 'All UPI users will have to pay a 5% transaction fee.' (FALSE)
    Lookup: 'All UPI users will have to pay a 10% transaction fee.'
    Even if embedding similarity is high, the number changed (5% vs 10%).
    MUST NOT reuse cached result blindly!
    """
    clean_memory_service.store_claim(
        claim_text="All UPI users will have to pay a 5% transaction fee.",
        verdict=Verdict.FALSE,
    )

    # Lookup with changed number (10% instead of 5%)
    result = clean_memory_service.lookup_claim(
        "All UPI users will have to pay a 10% transaction fee.",
        similarity_threshold=0.75,
    )
    assert result.hit is False
    assert result.reason == "CRITICAL_NUMBER_MISMATCH"
    assert result.numbers_matched is False


# ==============================================================================
# 7. CRITICAL FACT SAFETY GUARDRAIL: CHANGED DATE
# ==============================================================================

def test_changed_date_rejects_l1_reuse(clean_memory_service):
    """
    Safety Guardrail:
    Cached: 'Nationwide curfew order issued in 2024.' (OUTDATED)
    Lookup: 'Nationwide curfew order issued in 2026.'
    Dates changed (2024 vs 2026).
    MUST NOT reuse cached result blindly!
    """
    clean_memory_service.store_claim(
        claim_text="Nationwide curfew order issued in 2024.",
        verdict=Verdict.OUTDATED,
    )

    # Lookup with changed year (2026)
    result = clean_memory_service.lookup_claim(
        "Nationwide curfew order issued in 2026.",
        similarity_threshold=0.75,
    )
    assert result.hit is False
    assert result.reason == "CRITICAL_DATE_MISMATCH"
    assert result.dates_matched is False


def test_changed_month_date_rejects_l1_reuse(clean_memory_service):
    """
    Cached: 'Scheme announced on June 4.'
    Lookup: 'Scheme announced on June 5.'
    Day changed from 4 to 5 -> MUST NOT reuse!
    """
    clean_memory_service.store_claim(
        claim_text="Scheme announced on June 4.",
        verdict=Verdict.VERIFIED,
    )

    result = clean_memory_service.lookup_claim(
        "Scheme announced on June 5.",
        similarity_threshold=0.75,
    )
    assert result.hit is False
    assert result.reason in ("CRITICAL_DATE_MISMATCH", "CRITICAL_NUMBER_MISMATCH")


# ==============================================================================
# 8. METRIC TELEMETRY: ADD CACHE_HIT TO METRICS
# ==============================================================================

def test_cache_hit_recorded_in_metrics_telemetry(clean_memory_service):
    """
    User Spec Requirement:
    'Add cache_hit to metrics.'
    """
    clean_memory_service.store_claim(
        claim_text="UPI is banned from tomorrow.",
        verdict=Verdict.FALSE,
    )

    # Execute L0 hit
    res = clean_memory_service.lookup_claim("UPI is banned from tomorrow.")
    assert res.hit is True

    # Verify metrics repository logged cache_hit
    all_metrics = clean_memory_service.metrics_repo.get_metrics(metric_name="cache_hit")
    assert len(all_metrics) >= 1
    hit_metric = all_metrics[-1]
    assert hit_metric.metric_name == "cache_hit"
    assert hit_metric.value == 1.0
    assert hit_metric.dimensions.get("level") == "L0"
    assert hit_metric.dimensions.get("verdict") == "FALSE"


# ==============================================================================
# 9. FASTAPI REST API ENDPOINTS
# ==============================================================================

def test_api_memory_store_endpoint():
    """Validates POST /api/v1/claims/memory/store endpoint."""
    payload = {
        "claim_text": "Government announced ₹10,000 grant for every citizen.",
        "verdict": "FALSE",
        "evidence_ids": ["ev_01"],
        "ttl_hours": 24,
        "source_versions": {"pib.gov.in": "v2026"},
    }
    resp = client.post("/api/v1/claims/memory/store", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["claim_hash"] is not None
    assert data["normalized_claim"] == "government announced ₹10,000 grant for every citizen"
    assert data["verdict"] == "FALSE"
    assert data["evidence_ids"] == ["ev_01"]


def test_api_memory_lookup_endpoint_hit():
    """Validates POST /api/v1/claims/memory/lookup endpoint on exact hit."""
    # 1. Store
    store_payload = {
        "claim_text": "API Test Scheme Claim for 2026.",
        "verdict": "VERIFIED",
        "evidence_ids": ["ev_gazette"],
    }
    client.post("/api/v1/claims/memory/store", json=store_payload)

    # 2. Lookup
    lookup_payload = {
        "claim_text": "API Test Scheme Claim for 2026.",
    }
    resp = client.post("/api/v1/claims/memory/lookup", json=lookup_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["hit"] is True
    assert data["level"] == "L0"
    assert data["record"]["verdict"] == "VERIFIED"
