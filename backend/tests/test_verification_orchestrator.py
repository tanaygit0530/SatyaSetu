import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.claim import AtomicClaim
from app.schemas.enums import ConfidenceLevel, TemporalStatus, Verdict
from app.schemas.evidence import (
    EvidenceCandidate,
    LockedEvidenceItem,
    RetrievedSource,
)
from app.schemas.temporal import TemporalVerificationResult
from app.schemas.verification import (
    VerificationInput,
    VerificationResult,
)
from app.services.verification_orchestrator import (
    VerificationOrchestrator,
    verification_orchestrator,
)

client = TestClient(app)


@pytest.fixture
def clean_orchestrator():
    """Provides a fresh VerificationOrchestrator with isolated memory and metrics."""
    orch = VerificationOrchestrator()
    orch.claim_memory.memory_repo._local_records.clear()
    orch.metrics_repo._local_metrics.clear()
    return orch


# ==============================================================================
# 1. ORCHESTRATOR INITIALIZATION & INDEPENDENT STAGE TESTS
# ==============================================================================

def test_orchestrator_initialization(clean_orchestrator):
    """Ensures VerificationOrchestrator initializes all 21 modular stage services."""
    assert clean_orchestrator.text_ingestion is not None
    assert clean_orchestrator.language_detector is not None
    assert clean_orchestrator.claim_extractor is not None
    assert clean_orchestrator.claim_dependency is not None
    assert clean_orchestrator.claim_memory is not None
    assert clean_orchestrator.query_generator is not None
    assert clean_orchestrator.retrieval_pipeline is not None
    assert clean_orchestrator.source_registry is not None
    assert clean_orchestrator.evidence_extractor is not None
    assert clean_orchestrator.evidence_locking is not None
    assert clean_orchestrator.evidence_judge is not None
    assert clean_orchestrator.temporal_verifier is not None
    assert clean_orchestrator.rule_engine is not None
    assert clean_orchestrator.confidence_calculator is not None
    assert clean_orchestrator.explanation_generator is not None
    assert clean_orchestrator.verification_repo is not None
    assert clean_orchestrator.metrics_repo is not None


def test_stage_1_input(clean_orchestrator):
    """Stage 1: Input validation and normalization."""
    inp = clean_orchestrator.stage_input("UPI is banned tomorrow.", "whatsapp")
    assert inp["content"] == "UPI is banned tomorrow."
    assert inp["input_type"] == "WHATSAPP"

    with pytest.raises(Exception):
        clean_orchestrator.stage_input("   ", "TEXT")


def test_stage_2_ingestion(clean_orchestrator):
    """Stage 2: Ingestion cleans and canonicalizes input text."""
    raw = "  RBI announces   new guidelines for   UPI transactions.  "
    ingested = clean_orchestrator.stage_ingestion(raw, "TEXT")
    assert "RBI announces new guidelines for UPI transactions" in ingested


def test_stage_3_language_detection(clean_orchestrator):
    """Stage 3: Vernacular and script detection."""
    res_en = clean_orchestrator.stage_language_detection("UPI services will remain operational.")
    assert res_en.language in ("en", "hi")

    res_hi = clean_orchestrator.stage_language_detection("सरकार ने सभी नागरिकों को ₹10,000 देने की घोषणा की है।")
    assert res_hi.language == "hi"
    assert res_hi.script == "Devanagari"


def test_stage_4_claim_extraction(clean_orchestrator):
    """Stage 4: Decomposes message into check-worthy atomic propositions."""
    text = "UPI is banned from tomorrow and all users must pay 5% transaction fee."
    claims = clean_orchestrator.stage_claim_extraction(text)
    assert len(claims) >= 1
    assert all(isinstance(c, AtomicClaim) for c in claims)
    assert claims[0].claim_id.startswith("clm_")


def test_stage_5_claim_normalization(clean_orchestrator):
    """Stage 5: Normalizes claim proposition for cryptographic memory."""
    claim = AtomicClaim(
        claim_id="clm_001",
        original_text="  UPI Has Been Banned From Tomorrow!  ",
        normalized_claim="upi has been banned from tomorrow",
    )
    norm = clean_orchestrator.stage_claim_normalization(claim)
    assert norm == "upi has been banned from tomorrow"


def test_stage_6_dependency_analysis(clean_orchestrator):
    """Stage 6: Dependency graph and topological ordering."""
    c1 = AtomicClaim(
        claim_id="clm_001",
        original_text="Govt launched new scheme X.",
        normalized_claim="govt launched new scheme x",
    )
    c2 = AtomicClaim(
        claim_id="clm_002",
        original_text="Scheme X provides ₹10,000 monthly grant.",
        normalized_claim="scheme x provides 10000 monthly grant",
    )
    dep_graph = clean_orchestrator.stage_dependency_analysis([c1, c2])
    assert dep_graph.execution_order is not None
    assert len(dep_graph.execution_order) == 2


def test_stage_7_shared_claim_memory_lookup(clean_orchestrator):
    """Stage 7: Two-level Shared Claim Memory lookup."""
    # Initially cache miss
    res = clean_orchestrator.stage_shared_claim_memory_lookup("UPI is banned tomorrow.")
    assert res.hit is False

    # Store verified claim
    clean_orchestrator.claim_memory.store_claim(
        claim_text="UPI is banned tomorrow.",
        verdict=Verdict.FALSE,
        evidence_ids=["ev_001"],
    )

    # Now cache hit!
    res_hit = clean_orchestrator.stage_shared_claim_memory_lookup("UPI is banned tomorrow.")
    assert res_hit.hit is True
    assert res_hit.level in ("L0", "L1")
    assert res_hit.record.verdict == Verdict.FALSE


def test_stage_8_query_generation(clean_orchestrator):
    """Stage 8: Generates search query set."""
    queries = clean_orchestrator.stage_query_generation("UPI is banned tomorrow.")
    assert queries.claim_text is not None
    assert queries.english_query is not None
    assert queries.contradiction_query is not None


def test_stage_13_and_14_evidence_extraction_and_grounding(clean_orchestrator):
    """Stages 13 & 14: Evidence candidate extraction and quote grounding validation."""
    claim_text = "UPI is banned from tomorrow."
    source_body = (
        "National Payments Corporation of India (NPCI) clarified that "
        "UPI services have not been banned and continue to operate smoothly across India."
    )
    retrieved = [
        RetrievedSource(
            url="https://npci.org.in/press/clarification",
            title="NPCI Official Clarification on UPI",
            publisher="NPCI",
            domain="npci.org.in",
            text=source_body,
        )
    ]

    candidates = clean_orchestrator.stage_evidence_extraction(claim_text, retrieved)
    assert len(candidates) >= 1
    assert candidates[0].is_validated is False

    # Stage 14: Grounding validation
    locked = clean_orchestrator.stage_grounding_validation(candidates, retrieved)
    assert len(locked) >= 1
    assert isinstance(locked[0], LockedEvidenceItem)
    assert locked[0].source_tier == 1


def test_stage_15_evidence_judge(clean_orchestrator):
    """Stage 15: Sandboxed evidence judge evaluates contradiction/support stance."""
    claim_text = "UPI is banned from tomorrow."
    locked = [
        LockedEvidenceItem(
            evidence_id="ev_001",
            source_url="https://npci.org.in/press/clarification",
            source_title="NPCI Press Release",
            publisher="NPCI",
            source_tier=1,
            exact_quote="UPI services have not been banned and continue to operate smoothly.",
            source_text_reference="offset:0-65",
            retrieved_at="2026-10-08T00:00:00Z",
            claim_relation="CONTRADICTS",
        )
    ]
    judgments = clean_orchestrator.stage_evidence_judge(claim_text, locked)
    assert len(judgments) == 1
    assert judgments[0].stance.value == "CONTRADICTS"


def test_stage_16_temporal_analysis(clean_orchestrator):
    """Stage 16: Temporal analysis distinguishes TRUE THEN from TRUE NOW."""
    claim_text = "UPI is banned from tomorrow."
    locked = [
        LockedEvidenceItem(
            evidence_id="ev_001",
            source_url="https://npci.org.in/press/clarification",
            source_title="NPCI Press Release",
            publisher="NPCI",
            source_tier=1,
            exact_quote="UPI services have not been banned.",
            source_text_reference="offset:0-35",
            retrieved_at="2026-10-08T00:00:00Z",
            claim_relation="NEUTRAL",
        )
    ]
    temp_res = clean_orchestrator.stage_temporal_analysis(claim_text, locked)
    assert isinstance(temp_res, TemporalVerificationResult)


def test_stage_17_deterministic_verdict(clean_orchestrator):
    """Stage 17: Deterministic rule engine calculates final verdict without LLMs."""
    claim = AtomicClaim(
        claim_id="clm_001",
        original_text="UPI is banned tomorrow.",
        normalized_claim="upi is banned tomorrow",
    )
    locked = [
        LockedEvidenceItem(
            evidence_id="ev_001",
            source_url="https://npci.org.in/press/clarification",
            source_title="NPCI Press Release",
            publisher="NPCI",
            source_tier=1,
            exact_quote="UPI services have not been banned.",
            source_text_reference="offset:0-35",
            retrieved_at="2026-10-08T00:00:00Z",
            claim_relation="CONTRADICTS",
        )
    ]
    judgments = clean_orchestrator.stage_evidence_judge(claim.original_text, locked)
    temp_res = clean_orchestrator.stage_temporal_analysis(claim.original_text, locked)

    verdict, rule_trace = clean_orchestrator.stage_deterministic_verdict(
        claim=claim,
        validated_evidence=locked,
        judgments=judgments,
        temporal_result=temp_res,
    )
    assert verdict == Verdict.FALSE
    assert len(rule_trace) >= 1


def test_stage_18_confidence(clean_orchestrator):
    """Stage 18: Deterministic confidence engine computes categorical rating."""
    locked = [
        LockedEvidenceItem(
            evidence_id="ev_001",
            source_url="https://npci.org.in/press/clarification",
            source_title="NPCI Press Release",
            publisher="NPCI",
            source_tier=1,
            exact_quote="UPI services have not been banned.",
            source_text_reference="offset:0-35",
            retrieved_at="2026-10-08T00:00:00Z",
            claim_relation="CONTRADICTS",
        )
    ]
    judgments = clean_orchestrator.stage_evidence_judge("UPI is banned tomorrow.", locked)
    temp_res = clean_orchestrator.stage_temporal_analysis("UPI is banned tomorrow.", locked)

    conf = clean_orchestrator.stage_confidence(
        validated_evidence=locked,
        judgments=judgments,
        temporal_result=temp_res,
        verdict=Verdict.FALSE,
    )
    assert conf in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)


def test_stage_19_explanation(clean_orchestrator):
    """Stage 19: Forensic explanation strictly under 80 words."""
    locked = [
        LockedEvidenceItem(
            evidence_id="ev_001",
            source_url="https://npci.org.in/press/clarification",
            source_title="NPCI Press Release",
            publisher="NPCI",
            source_tier=1,
            exact_quote="NPCI has not announced any ban on UPI services.",
            source_text_reference="offset:0-46",
            retrieved_at="2026-10-08T00:00:00Z",
            claim_relation="CONTRADICTS",
        )
    ]
    expl = clean_orchestrator.stage_explanation(
        claim_text="UPI is banned tomorrow.",
        verdict=Verdict.FALSE,
        validated_evidence=locked,
        rule_trace=["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION"],
        temporal_status=TemporalStatus.CURRENT,
    )
    assert expl is not None
    assert len(expl.split()) < 80


# ==============================================================================
# 2. END-TO-END VERIFICATION PIPELINE & SPECIFICATION CONFORMANCE
# ==============================================================================

def test_end_to_end_verification_pipeline(clean_orchestrator):
    """
    Validates complete end-to-end execution of VerificationOrchestrator.
    Conforms to user required output structure:
    {
      "check_id": "chk_001",
      "claims": [
        {
          "claim_id": "clm_001",
          "verdict": "FALSE",
          "confidence": "HIGH",
          "explanation": "...",
          "evidence": [],
          "rule_trace": []
        }
      ],
      "cache_hit": false,
      "processing_time_ms": 4210
    }
    """
    result = clean_orchestrator.verify(
        content="UPI is banned from tomorrow.",
        input_type="TEXT",
        check_id="chk_001",
        is_demo=True,
    )

    assert isinstance(result, VerificationResult)
    assert result.check_id == "chk_001"
    assert len(result.claims) >= 1
    assert result.cache_hit is False
    assert result.processing_time_ms >= 0

    first_claim = result.claims[0]
    assert first_claim.claim_id.startswith("clm_")
    assert first_claim.verdict in Verdict
    assert first_claim.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)
    assert isinstance(first_claim.explanation, str)
    assert len(first_claim.explanation.split()) <= 80
    assert isinstance(first_claim.evidence, list)
    assert isinstance(first_claim.rule_trace, list)


def test_end_to_end_shared_claim_memory_cache_hit_reuse(clean_orchestrator):
    """
    Validates that a previously verified claim in Shared Claim Memory
    is immediately reused on subsequent execution without rerun, setting cache_hit=True.
    """
    # 1. First run: Cache miss -> Verifies and stores in memory
    res_1 = clean_orchestrator.verify(
        content="UPI is banned from tomorrow.",
        check_id="chk_first_run",
        is_demo=True,
    )
    assert res_1.cache_hit is False

    # 2. Second run: Exact same claim -> Cache hit!
    res_2 = clean_orchestrator.verify(
        content="UPI is banned from tomorrow.",
        check_id="chk_second_run",
        is_demo=True,
    )
    assert res_2.cache_hit is True
    assert len(res_2.claims) >= 1
    assert res_2.claims[0].cache_hit is True
    assert res_2.claims[0].verdict == res_1.claims[0].verdict


def test_fastapi_claims_verify_endpoint():
    """Validates FastAPI POST /api/v1/claims/verify endpoint conforms to schema."""
    payload = {
        "content": "Government announced ₹10,000 grant for every citizen.",
        "input_type": "TEXT",
        "check_id": "chk_api_01",
        "is_demo": True,
    }
    resp = client.post("/api/v1/claims/verify", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["check_id"] == "chk_api_01"
    assert "claims" in data
    assert len(data["claims"]) >= 1
    assert "cache_hit" in data
    assert "processing_time_ms" in data

    claim_0 = data["claims"][0]
    assert "claim_id" in claim_0
    assert "verdict" in claim_0
    assert "confidence" in claim_0
    assert "explanation" in claim_0
    assert "evidence" in claim_0
    assert "rule_trace" in claim_0
