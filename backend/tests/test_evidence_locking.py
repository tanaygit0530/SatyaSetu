import pytest
from app.schemas.enums import SourceTier, Verdict
from app.schemas.claim import ExtractedClaim
from app.schemas.evidence import (
    EvidenceCandidate,
    EvidenceItem,
    EvidenceInterpretation,
    GroundingValidationResult,
    LockedEvidenceItem,
)
from app.services.evidence_locking import (
    EvidenceLockingService,
    evidence_locking_service,
)
from app.services.rule_engine import DeterministicRuleEngine


# ==============================================================================
# Specification Example & 5 Required Tests
# ==============================================================================

def test_1_exact_quote_accepted():
    """
    Test 1: Exact quote -> accepted.
    Example:
    Fetched source: 'The Ministry announced the scheme on June 4.'
    Quote: 'The Ministry announced the scheme on June 4.'
    """
    source_text = "The Ministry announced the scheme on June 4."
    quote = "The Ministry announced the scheme on June 4."

    result = evidence_locking_service.verify_quote_grounding(
        exact_quote=quote,
        source_text=source_text,
    )

    assert result.valid is True
    assert result.reason is None
    assert result.source_text_reference is not None
    assert "offset:" in result.source_text_reference


def test_2_minor_whitespace_difference_normalized_and_accepted():
    """
    Test 2: Minor whitespace difference -> normalized and accepted.
    Source has regular spacing, quote has extra spaces, tabs, and newlines.
    """
    source_text = "The Ministry announced the scheme on June 4."
    # Quote with irregular spaces, tabs, and newlines
    quote = "The   Ministry \n announced  the\tscheme on   June 4."

    result = evidence_locking_service.verify_quote_grounding(
        exact_quote=quote,
        source_text=source_text,
    )

    assert result.valid is True
    assert result.reason is None
    assert result.source_text_reference is not None


def test_3_changed_number_rejected():
    """
    Test 3: Changed number -> rejected.
    Source states ₹10,000, quote states ₹50,000.
    Must return valid=False, reason="QUOTE_NOT_FOUND".
    """
    source_text = "The Ministry announced ₹10,000 grant for eligible undergraduate students."
    # LLM hallucinated ₹50,000 instead of ₹10,000
    fabricated_quote = "The Ministry announced ₹50,000 grant for eligible undergraduate students."

    result = evidence_locking_service.verify_quote_grounding(
        exact_quote=fabricated_quote,
        source_text=source_text,
    )

    assert result.valid is False
    assert result.reason == "QUOTE_NOT_FOUND"


def test_4_changed_date_rejected():
    """
    Test 4: Changed date -> rejected.
    SPECIFICATION EXAMPLE:
    Fetched source: 'The Ministry announced the scheme on June 4.'
    LLM returns: 'The Ministry announced the scheme on June 5.'
    Reject it.
    Return:
    {
      "valid": false,
      "reason": "QUOTE_NOT_FOUND"
    }
    """
    source_text = "The Ministry announced the scheme on June 4."
    # LLM returned June 5 instead of June 4
    fabricated_quote = "The Ministry announced the scheme on June 5."

    result = evidence_locking_service.verify_quote_grounding(
        exact_quote=fabricated_quote,
        source_text=source_text,
    )

    assert result.valid is False
    assert result.reason == "QUOTE_NOT_FOUND"


def test_5_completely_invented_quote_rejected():
    """
    Test 5: Completely invented quote -> rejected.
    Source is about June 4 scheme announcement.
    Quote is completely fabricated: 'All banks will halt operations immediately.'
    Must return valid=False, reason="QUOTE_NOT_FOUND".
    """
    source_text = "The Ministry announced the scheme on June 4."
    invented_quote = "All banks will halt operations immediately."

    result = evidence_locking_service.verify_quote_grounding(
        exact_quote=invented_quote,
        source_text=source_text,
    )

    assert result.valid is False
    assert result.reason == "QUOTE_NOT_FOUND"


# ==============================================================================
# Evidence Locking Model & Field Verifications
# ==============================================================================

def test_lock_evidence_fields_and_provenance():
    """
    Verifies that a validly locked evidence item captures all required fields:
    - source_url
    - source_title
    - publisher
    - published_date
    - retrieved_at
    - source_tier
    - exact_quote
    - source_text_reference
    - claim_relation
    """
    source_text = (
        "National Payments Corporation of India (NPCI) has issued an official statement. "
        "NPCI has not announced any nationwide shutdown of UPI. Services remain fully operational."
    )
    quote = "NPCI has not announced any nationwide shutdown of UPI."

    candidate = EvidenceCandidate(
        candidate_id="cand_001",
        claim_id="clm_001",
        claim_text="UPI is banned tomorrow.",
        source_id="src_npci",
        title="NPCI Clarification on UPI",
        publisher="NPCI",
        url="https://www.npci.org.in/press-releases/clarification",
        published_date="2026-10-06",
        retrieved_date="2026-10-07T10:00:00Z",
        relevant_text="NPCI has not announced any nationwide shutdown of UPI.",
        candidate_quotes=[quote],
        relevance_score=0.95,
        stance_hint="REFUTES",
        is_validated=False,
    )

    result = evidence_locking_service.lock_evidence(
        evidence=candidate,
        source_text=source_text,
        claim_relation="REFUTES",
    )

    assert result.valid is True
    assert result.reason is None
    locked = result.locked_evidence
    assert isinstance(locked, LockedEvidenceItem)

    # Check all required fields
    assert locked.source_url == "https://www.npci.org.in/press-releases/clarification"
    assert locked.source_title == "NPCI Clarification on UPI"
    assert locked.publisher == "NPCI"
    assert locked.published_date == "2026-10-06"
    assert locked.retrieved_at == "2026-10-07T10:00:00Z"
    assert locked.source_tier == 1
    assert locked.exact_quote == quote
    assert locked.source_text_reference is not None
    assert "offset:" in locked.source_text_reference
    assert locked.claim_relation == "REFUTES"


# ==============================================================================
# Integration: Validator Runs BEFORE Verdict Calculation
# ==============================================================================

def test_evidence_locking_runs_before_verdict_calculation():
    """
    CRITICAL REQUIREMENT:
    This validator runs BEFORE verdict calculation.
    The system must NEVER display fabricated quotes.
    If an evidence quote was altered by the LLM (e.g. June 4 -> June 5),
    it is rejected BEFORE the verdict engine can use it to corroborate or refute the claim.
    """
    claim = ExtractedClaim(
        claim_number=1,
        claim_text="Ministry launched scheme on June 5.",
        language="en",
    )

    # The actual official document stored
    source_texts = {
        "https://egazette.gov.in/circ/2026/moe-14": "The Ministry announced the scheme on June 4.",
    }

    # An LLM hallucinated / altered citation claiming it was announced June 5
    fabricated_evidence = [
        EvidenceItem(
            id="CIT-FABRICATED",
            publisher="The Gazette of India",
            domain="egazette.gov.in",
            title="Scheme Notification",
            publish_date="2026-06-05",
            tier=SourceTier.TIER_1_PRIMARY,
            url="https://egazette.gov.in/circ/2026/moe-14",
            exact_quote="The Ministry announced the scheme on June 5.",  # Fabricated date!
            confidence_score=0.99,
        )
    ]

    interpretation = EvidenceInterpretation(
        supports_claim=True,
        refutes_claim=False,
    )

    # When evaluated with stored source texts, Evidence Locking must run BEFORE verdict calculation
    result = DeterministicRuleEngine.evaluate_claim(
        claim=claim,
        evidence_list=fabricated_evidence,
        interpretation=interpretation,
        source_texts=source_texts,
    )

    # Verdict cannot be VERIFIED because the quote was rejected
    assert result.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert result.rule_matched == "RULE-EVIDENCE-LOCKING-REJECTED"
    # Never display fabricated quotes in source citations
    assert len(result.source_citations) == 0
