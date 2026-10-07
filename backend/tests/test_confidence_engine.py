import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import (
    ConfidenceLevel,
    ContradictionStrength,
    Language,
    SourceTier,
    TemporalStatus,
    Verdict,
)
from app.schemas.claim import ClaimResult, ExtractedClaim
from app.schemas.confidence import (
    ClaimConfidenceItem,
    ConfidenceInput,
    ConfidenceOutput,
    MessageConfidenceInput,
)
from app.schemas.evidence import EvidenceItem, LockedEvidenceItem
from app.schemas.judge import (
    EvidenceAssessmentLevel,
    EvidenceJudgeAssessment,
    EvidenceStance,
)
from app.services.confidence_engine import ConfidenceEngine, confidence_engine

client = TestClient(app)


# ==============================================================================
# 1. SPECIFICATION EXAMPLES DIRECTLY FROM USER PROMPT
# ==============================================================================

def test_prompt_spec_example_1_high_confidence():
    """
    User Spec Example 1:
    Tier 1 official source
    + strong quote
    + current
    + independent confirmation
    → HIGH
    """
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_1_PRIMARY,
        source_relevance="HIGH",
        recency=TemporalStatus.CURRENT,
        source_agreement=1.0,
        evidence_quantity=2,  # independent confirmation
        retrieval_quality="HIGH",
        ambiguity="LOW",
    )
    assert conf == ConfidenceLevel.HIGH
    assert conf in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)


def test_prompt_spec_example_2_low_confidence():
    """
    User Spec Example 2:
    Weak sources
    + old evidence
    + conflicting evidence
    → LOW
    """
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_3_REPUTABLE,
        recency=TemporalStatus.EXPIRED,
        source_agreement=0.35,  # conflicting evidence
        contradiction_strength=ContradictionStrength.STRONG,
        evidence_quantity=2,
    )
    assert conf == ConfidenceLevel.LOW
    assert conf in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)


# ==============================================================================
# 2. OUTPUT DOMAIN & NO FAKE PRECISION EXPOSURE
# ==============================================================================

def test_confidence_output_domain_strictly_high_medium_low():
    """Primary output MUST be strictly HIGH, MEDIUM, or LOW without fake floats like 0.9738421."""
    res: ConfidenceOutput = confidence_engine.calculate_confidence_detailed(
        source_credibility=1.0,
        source_agreement=1.0,
        source_relevance=1.0,
        recency=1.0,
        retrieval_quality=1.0,
        evidence_quantity=3,
    )
    assert isinstance(res.confidence, ConfidenceLevel)
    assert res.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
    assert res.confidence == ConfidenceLevel.HIGH

    # The string representation must be strictly 'HIGH'
    assert str(res.confidence) == "HIGH"
    # Ensure internal continuous score is within [0.0, 1.0]
    assert res.internal_score is not None
    assert 0.0 <= res.internal_score <= 1.0


# ==============================================================================
# 3. HIGH CONFIDENCE TEST SUITE
# ==============================================================================

def test_high_confidence_tier1_gazette_with_exact_quote():
    """Tier 1 gazette citation with exact quote and current recency."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=1.0,
        source_relevance=1.0,
        recency=TemporalStatus.CURRENT,
        source_agreement=1.0,
        evidence_quantity=1,
    )
    assert conf == ConfidenceLevel.HIGH


def test_high_confidence_two_concurring_official_sources():
    """Two concurring government portals (PIB and RBI circular)."""
    ev1 = EvidenceItem(
        id="E1", publisher="PIB Fact Check", domain="pib.gov.in",
        title="Clarification", tier=SourceTier.TIER_1_PRIMARY,
        url="https://pib.gov.in/1", exact_quote="Claim is authentic.",
    )
    ev2 = EvidenceItem(
        id="E2", publisher="Reserve Bank of India", domain="rbi.org.in",
        title="Notification", tier=SourceTier.TIER_1_PRIMARY,
        url="https://rbi.org.in/2", exact_quote="Directive issued under Section 10.",
    )
    conf = confidence_engine.calculate_confidence(
        evidence_list=[ev1, ev2],
        source_agreement=1.0,
        recency="CURRENT",
        retrieval_quality="HIGH",
    )
    assert conf == ConfidenceLevel.HIGH


def test_high_confidence_historical_true_decree():
    """Court judgment historically establishing factual occurrence."""
    conf = confidence_engine.calculate_confidence(
        source_credibility="TIER_1",
        source_relevance="HIGH",
        recency=TemporalStatus.HISTORICAL_TRUE,
        source_agreement=1.0,
        evidence_quantity=2,
    )
    assert conf == ConfidenceLevel.HIGH


def test_high_confidence_multi_source_fact_checker_corroboration():
    """Multiple Tier 2 reputable fact-checkers concurring unanimously."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_2_SECONDARY,
        source_relevance="HIGH",
        recency="CURRENT",
        source_agreement=1.0,
        evidence_quantity=3,
        retrieval_quality=0.95,
        ambiguity=0.0,
    )
    assert conf == ConfidenceLevel.HIGH


# ==============================================================================
# 4. MEDIUM CONFIDENCE TEST SUITE
# ==============================================================================

def test_medium_confidence_single_secondary_source():
    """Single Tier 2 source without multi-source independent confirmation."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_2_SECONDARY,
        source_relevance="MEDIUM",
        recency="CURRENT",
        source_agreement=0.8,
        evidence_quantity=1,
        retrieval_quality=0.7,
        ambiguity=0.2,
    )
    assert conf == ConfidenceLevel.MEDIUM


def test_medium_confidence_tier3_reputable_news_only():
    """Mainstream press report without official gazette or court decree."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_3_REPUTABLE,
        source_relevance="HIGH",
        recency="CURRENT",
        source_agreement=0.9,
        evidence_quantity=2,
        retrieval_quality=0.8,
    )
    assert conf == ConfidenceLevel.MEDIUM


def test_medium_confidence_moderate_assertion_ambiguity():
    """Assertion contains minor semantic ambiguity or hedging."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_1_PRIMARY,
        source_relevance="HIGH",
        recency="CURRENT",
        source_agreement=0.85,
        evidence_quantity=2,
        ambiguity=0.8,  # high ambiguity caps confidence
    )
    assert conf == ConfidenceLevel.MEDIUM


def test_medium_confidence_dated_evidence_without_explicit_supersession():
    """Evidence from an unverified timestamp with neutral agreement."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_2_SECONDARY,
        source_relevance="MEDIUM",
        recency=TemporalStatus.DATE_UNKNOWN,
        source_agreement=0.75,
        evidence_quantity=1,
    )
    assert conf == ConfidenceLevel.MEDIUM


# ==============================================================================
# 5. LOW CONFIDENCE TEST SUITE
# ==============================================================================

def test_low_confidence_zero_evidence():
    """Zero evidence citations available strictly yields LOW."""
    conf = confidence_engine.calculate_confidence(
        evidence_quantity=0,
        evidence_list=[],
    )
    assert conf == ConfidenceLevel.LOW


def test_low_confidence_poor_retrieval_quality():
    """Retrieval quality below 0.35 without tier 1 source strictly yields LOW."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_3_REPUTABLE,
        retrieval_quality=0.20,
        evidence_quantity=1,
    )
    assert conf == ConfidenceLevel.LOW


def test_low_confidence_severe_source_conflict():
    """Severe source conflict between non-authoritative sources strictly yields LOW."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=SourceTier.TIER_3_REPUTABLE,
        source_agreement=0.40,  # split / conflicting
        contradiction_strength="STRONG",
        evidence_quantity=2,
    )
    assert conf == ConfidenceLevel.LOW


def test_low_confidence_all_citations_irrelevant():
    """All evidence items evaluated as IRRELEVANT by judge."""
    j1 = EvidenceJudgeAssessment(evidence_id="E1", stance=EvidenceStance.IRRELEVANT, reason="Not related")
    j2 = EvidenceJudgeAssessment(evidence_id="E2", stance=EvidenceStance.IRRELEVANT, reason="Off topic")
    conf = confidence_engine.calculate_confidence(
        evidence_judgments=[j1, j2],
        evidence_quantity=2,
    )
    assert conf == ConfidenceLevel.LOW


def test_low_confidence_weak_source_plus_expired_evidence():
    """Untrusted blog posting expired circular."""
    conf = confidence_engine.calculate_confidence(
        source_credibility=0.20,
        recency=TemporalStatus.EXPIRED,
        evidence_quantity=1,
    )
    assert conf == ConfidenceLevel.LOW


# ==============================================================================
# 6. MESSAGE-LEVEL CONFIDENCE (WEAKEST IMPORTANT CLAIM LIMITATION)
# ==============================================================================

def test_message_confidence_all_high_yields_high():
    """When all important claims are HIGH, message confidence is HIGH."""
    claims = [
        ClaimConfidenceItem(claim_id="CLM-1", confidence=ConfidenceLevel.HIGH, is_important=True),
        ClaimConfidenceItem(claim_id="CLM-2", confidence=ConfidenceLevel.HIGH, is_important=True),
    ]
    assert confidence_engine.calculate_message_confidence(claims) == ConfidenceLevel.HIGH


def test_message_confidence_limited_by_weakest_important_claim_medium():
    """Message confidence limited by weakest important claim (MEDIUM)."""
    claims = [
        ClaimConfidenceItem(claim_id="CLM-1", confidence=ConfidenceLevel.HIGH, is_important=True),
        ClaimConfidenceItem(claim_id="CLM-2", confidence=ConfidenceLevel.MEDIUM, is_important=True),
        ClaimConfidenceItem(claim_id="CLM-3", confidence=ConfidenceLevel.HIGH, is_important=True),
    ]
    res = confidence_engine.calculate_message_confidence_detailed(claims)
    assert res.overall_confidence == ConfidenceLevel.MEDIUM
    assert res.weakest_claim_id == "CLM-2"
    assert res.important_claims_count == 3


def test_message_confidence_limited_by_weakest_important_claim_low():
    """Message confidence limited by weakest important claim (LOW)."""
    claims = [
        ClaimConfidenceItem(claim_id="CLM-1", confidence=ConfidenceLevel.HIGH, is_important=True),
        ClaimConfidenceItem(claim_id="CLM-2", confidence=ConfidenceLevel.LOW, is_important=True),
        ClaimConfidenceItem(claim_id="CLM-3", confidence=ConfidenceLevel.HIGH, is_important=True),
    ]
    res = confidence_engine.calculate_message_confidence_detailed(claims)
    assert res.overall_confidence == ConfidenceLevel.LOW
    assert res.weakest_claim_id == "CLM-2"


def test_message_confidence_unimportant_claim_does_not_bottleneck():
    """
    CRITICAL RULE:
    If a claim with LOW confidence is NOT important (e.g. greeting or opinion),
    it must NOT drag down the overall message confidence.
    """
    claims = [
        ClaimConfidenceItem(claim_id="CLM-1", confidence=ConfidenceLevel.HIGH, is_important=True),
        ClaimConfidenceItem(claim_id="CLM-2", confidence=ConfidenceLevel.LOW, is_important=False),  # Non-important opinion
        ClaimConfidenceItem(claim_id="CLM-3", confidence=ConfidenceLevel.HIGH, is_important=True),
    ]
    res = confidence_engine.calculate_message_confidence_detailed(claims)
    assert res.overall_confidence == ConfidenceLevel.HIGH
    assert res.important_claims_count == 2


def test_message_confidence_with_claim_result_objects():
    """Accepts domain ClaimResult objects seamlessly."""
    c1 = ClaimResult(
        id="CLM-1", claim_number=1, claim_text="Govt circular.",
        verdict=Verdict.VERIFIED, confidence=99.0, confidence_level=ConfidenceLevel.HIGH,
        summary="Verified", detailed_analysis="Analysis", rule_matched="RULE-1",
    )
    c2 = ClaimResult(
        id="CLM-2", claim_number=2, claim_text="Subsidy grant ₹50,000.",
        verdict=Verdict.PARTLY_SUPPORTED, confidence=78.0, confidence_level=ConfidenceLevel.MEDIUM,
        summary="Partial", detailed_analysis="Analysis", rule_matched="RULE-2",
    )
    overall = confidence_engine.calculate_message_confidence([c1, c2])
    assert overall == ConfidenceLevel.MEDIUM


def test_message_confidence_empty_list_fallback():
    """Empty claims list returns LOW gracefully."""
    res = confidence_engine.calculate_message_confidence_detailed([])
    assert res.overall_confidence == ConfidenceLevel.LOW
    assert res.evaluated_claims_count == 0


# ==============================================================================
# 7. FASTAPI API ROUTE ENDPOINT INTEGRATION
# ==============================================================================

def test_api_calculate_confidence_endpoint():
    """Validates POST /api/v1/claims/calculate-confidence endpoint."""
    payload = {
        "source_credibility": "TIER_1_PRIMARY",
        "source_relevance": "HIGH",
        "recency": "CURRENT",
        "source_agreement": 1.0,
        "retrieval_quality": "HIGH",
        "evidence_quantity": 2,
    }
    resp = client.post("/api/v1/claims/calculate-confidence", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"] == "HIGH"
    assert "factors_breakdown" in data
    assert data["factors_breakdown"]["source_credibility"] == 1.0


def test_api_message_confidence_endpoint():
    """Validates POST /api/v1/claims/message-confidence endpoint."""
    payload = {
        "claims": [
            {"claim_id": "clm_1", "confidence": "HIGH", "is_important": True},
            {"claim_id": "clm_2", "confidence": "MEDIUM", "is_important": True},
            {"claim_id": "clm_3", "confidence": "LOW", "is_important": False},
        ]
    }
    resp = client.post("/api/v1/claims/message-confidence", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_confidence"] == "MEDIUM"
    assert data["weakest_claim_id"] == "clm_2"
    assert data["important_claims_count"] == 2
