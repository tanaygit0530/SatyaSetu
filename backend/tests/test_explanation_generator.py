import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import SourceTier, TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import ExplanationInput, ExplanationOutput
from app.services.explanation_generator import (
    ExplanationGeneratorService,
    explanation_generator_service,
)

client = TestClient(app)


# ==============================================================================
# 1. SPECIFICATION EXAMPLE FROM USER PROMPT
# ==============================================================================

def test_prompt_spec_example_upi_banned_tomorrow():
    """
    User Spec Example:
    Claim: "UPI has been banned from tomorrow."
    Verdict: FALSE
    Explanation: Under 80 words, factually grounded, no invented numbers/dates.
    """
    output = explanation_generator_service.generate_explanation(
        claim="UPI has been banned from tomorrow.",
        verdict=Verdict.FALSE,
        validated_evidence=[],
        rule_trace=["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION", "CURRENT_EVIDENCE"],
        temporal_status=TemporalStatus.CURRENT,
    )
    assert output.verdict == Verdict.FALSE
    assert output.word_count < 80
    assert output.is_grounded is True
    assert "No." in output.explanation or "no official announcement" in output.explanation.lower()
    assert "UPI" in output.explanation


# ==============================================================================
# 2. FACTUAL GROUNDING: NUMBERS AND DATES IN CLAIM / EVIDENCE ACCEPTED
# ==============================================================================

def test_grounded_numbers_present_in_claim_accepted():
    """Numbers and dates present in the original claim are valid."""
    claim = "All users will have to pay a 5% fee from tomorrow."
    grounded = explanation_generator_service.extract_numbers_and_dates(claim)
    assert "5" in grounded or "5%" in grounded
    assert "tomorrow" in grounded


def test_grounded_numbers_present_in_evidence_accepted():
    """Numbers and dates present in the validated evidence quote are valid."""
    ev = EvidenceItem(
        id="E1",
        publisher="Ministry of Finance",
        domain="finmin.gov.in",
        title="Circular 2026",
        tier=SourceTier.TIER_1_PRIMARY,
        publish_date="2026-06-04",
        url="https://finmin.gov.in/circ",
        exact_quote="The sanctioned DBT scholarship rate is ₹12,000 per student announced on June 4.",
    )
    harvested = explanation_generator_service._harvest_grounded_numbers_and_dates(
        "Student gets scholarship.",
        [ev],
    )
    assert "12000" in harvested or "₹12,000" in harvested
    assert "june" in harvested or "4" in harvested
    assert "2026" in harvested


def test_validation_passes_when_explanation_uses_grounded_numbers():
    """An explanation using numbers from claim or evidence passes grounding validation."""
    grounded_facts = {"12000", "₹12,000", "june", "4", "2026"}
    candidate = "The official gazette confirms the sanctioned grant is ₹12,000 notified on June 4."
    is_valid, unauthorized = explanation_generator_service.validate_factual_grounding(
        candidate,
        grounded_facts,
    )
    assert is_valid is True
    assert len(unauthorized) == 0


# ==============================================================================
# 3. UNGROUNDED FACT DETECTION & ANTI-HALLUCINATION
# ==============================================================================

def test_ungrounded_number_detected_and_rejected():
    """An explanation introducing an invented number (e.g. ₹75,000) is rejected."""
    grounded_facts = {"12000", "2026"}  # No 75000 in claim or evidence
    hallucinated_candidate = "The department actually sanctioned ₹75,000 to every beneficiary."
    is_valid, unauthorized = explanation_generator_service.validate_factual_grounding(
        hallucinated_candidate,
        grounded_facts,
    )
    assert is_valid is False
    assert any("75000" in u for u in unauthorized)


def test_ungrounded_date_detected_and_rejected():
    """An explanation introducing an invented date (e.g. June 5 instead of June 4) is rejected."""
    grounded_facts = {"june", "4", "2026"}
    hallucinated_candidate = "The notification was released on June 5, 2026."
    is_valid, unauthorized = explanation_generator_service.validate_factual_grounding(
        hallucinated_candidate,
        grounded_facts,
    )
    assert is_valid is False
    assert any("5" in u for u in unauthorized)


# ==============================================================================
# 4. REGENERATION ONCE AND SAFE TEMPLATE FALLBACK
# ==============================================================================

def test_regeneration_once_when_first_candidate_hallucinates():
    """
    If Attempt 1 introduces ungrounded facts, the system regenerates once.
    If Attempt 2 succeeds, it returns Attempt 2 with regeneration_count=1.
    """
    with patch.object(
        explanation_generator_service,
        "_generate_candidate",
        side_effect=[
            "No. The department imposed a fee of ₹99,999 yesterday.",  # Attempt 1: ungrounded ₹99,999
            "No. Official records refute this assertion and confirm services continue normally.",  # Attempt 2: valid
        ],
    ):
        output = explanation_generator_service.generate_explanation(
            claim="UPI has a new fee.",
            verdict=Verdict.FALSE,
            validated_evidence=[],
            rule_trace=["TIER_1_SOURCE_PRESENT"],
        )
        assert output.is_grounded is True
        assert output.used_safe_template is False
        assert output.regeneration_count == 1
        assert output.word_count < 80
        assert "services continue normally" in output.explanation


def test_fallback_to_safe_template_when_second_attempt_also_hallucinates():
    """
    If Attempt 1 AND Attempt 2 both fail grounding validation,
    the system strictly falls back to the safe template.
    """
    with patch.object(
        explanation_generator_service,
        "_generate_candidate",
        side_effect=[
            "No. A fine of ₹55,000 applies.",  # Attempt 1 fails
            "No. Actually the fine is ₹77,000 on December 12.",  # Attempt 2 also fails
        ],
    ):
        output = explanation_generator_service.generate_explanation(
            claim="UPI ban order issued.",
            verdict=Verdict.FALSE,
            validated_evidence=[],
            rule_trace=["TIER_1_SOURCE_PRESENT"],
        )
        assert output.is_grounded is True
        assert output.used_safe_template is True
        assert output.regeneration_count == 1
        assert output.word_count < 80
        # Safe template for FALSE contains no numbers or dates
        assert "No." in output.explanation
        assert "not genuine" in output.explanation.lower() or "directly contradicts" in output.explanation.lower()


# ==============================================================================
# 5. ALL 5 CANONICAL VERDICTS PRODUCE EXPLANATIONS UNDER 80 WORDS
# ==============================================================================

def test_explanation_for_verified_verdict():
    """VERIFIED produces an explanation strictly under 80 words."""
    ev = EvidenceItem(
        id="E1", publisher="The Gazette of India", domain="egazette.gov.in",
        title="Scholarship 2026", tier=SourceTier.TIER_1_PRIMARY,
        url="https://egazette.gov.in/1", exact_quote="Scheme continuation is officially notified.",
    )
    output = explanation_generator_service.generate_explanation(
        claim="Government notified PM Merit Scholarship for 2026.",
        verdict=Verdict.VERIFIED,
        validated_evidence=[ev],
        rule_trace=["TIER_1_SOURCE_PRESENT", "CREDIBLE_CORROBORATION"],
    )
    assert output.verdict == Verdict.VERIFIED
    assert output.word_count < 80
    assert output.is_grounded is True
    assert "Gazette" in output.explanation or "official" in output.explanation.lower()


def test_explanation_for_false_verdict():
    """FALSE produces an explanation strictly under 80 words."""
    output = explanation_generator_service.generate_explanation(
        claim="Govt announced free gold coins for all citizens.",
        verdict=Verdict.FALSE,
        validated_evidence=[],
        rule_trace=["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION"],
    )
    assert output.verdict == Verdict.FALSE
    assert output.word_count < 80
    assert output.is_grounded is True


def test_explanation_for_outdated_verdict():
    """OUTDATED produces an explanation strictly under 80 words."""
    output = explanation_generator_service.generate_explanation(
        claim="Nationwide curfew order in effect tomorrow.",
        verdict=Verdict.OUTDATED,
        validated_evidence=[],
        rule_trace=["HISTORICAL_MISMATCH"],
        temporal_status=TemporalStatus.OUTDATED,
    )
    assert output.verdict == Verdict.OUTDATED
    assert output.word_count < 80
    assert output.is_grounded is True
    assert "outdated" in output.explanation.lower() or "no longer in effect" in output.explanation.lower()


def test_explanation_for_partly_supported_verdict():
    """PARTLY_SUPPORTED produces an explanation strictly under 80 words."""
    output = explanation_generator_service.generate_explanation(
        claim="All citizens get ₹50,000 grant under youth scheme.",
        verdict=Verdict.PARTLY_SUPPORTED,
        validated_evidence=[],
        rule_trace=["PARTIAL_SUPPORT", "CONDITIONAL_TERMS"],
    )
    assert output.verdict == Verdict.PARTLY_SUPPORTED
    assert output.word_count < 80
    assert output.is_grounded is True
    assert "partly supported" in output.explanation.lower() or "partial" in output.explanation.lower()


def test_explanation_for_cannot_be_confirmed_verdict():
    """CANNOT_BE_CONFIRMED produces an explanation strictly under 80 words."""
    output = explanation_generator_service.generate_explanation(
        claim="Chemicals leaked into municipal tanker in Ward 14.",
        verdict=Verdict.CANNOT_BE_CONFIRMED,
        validated_evidence=[],
        rule_trace=["INSUFFICIENT_EVIDENCE", "BELOW_EVIDENCE_THRESHOLD"],
    )
    assert output.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert output.word_count < 80
    assert output.is_grounded is True
    assert "cannot be confirmed" in output.explanation.lower()


# ==============================================================================
# 6. SAFE TEMPLATES PROPERTIES
# ==============================================================================

@pytest.mark.parametrize("verdict", [
    Verdict.VERIFIED,
    Verdict.FALSE,
    Verdict.OUTDATED,
    Verdict.PARTLY_SUPPORTED,
    Verdict.CANNOT_BE_CONFIRMED,
])
def test_all_safe_templates_strictly_under_80_words_and_zero_numbers(verdict: Verdict):
    """Every safe template must be strictly under 80 words with zero numbers or dates."""
    template = explanation_generator_service.get_safe_template(
        verdict=verdict,
        claim_text="General claim assertion",
        evidence_items=[],
        temporal_status=TemporalStatus.CURRENT,
    )
    words = template.split()
    assert len(words) < 80
    assert len(words) >= 10
    # Safe templates must contain zero numbers or dates to guarantee immunity
    numbers_dates = explanation_generator_service.extract_numbers_and_dates(template)
    assert len(numbers_dates) == 0


# ==============================================================================
# 7. FASTAPI API ROUTE ENDPOINT INTEGRATION
# ==============================================================================

def test_api_generate_explanation_endpoint():
    """Tests POST /api/v1/claims/generate-explanation endpoint."""
    payload = {
        "claim": "UPI has been banned from tomorrow.",
        "verdict": "FALSE",
        "validated_evidence": [],
        "rule_trace": ["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION"],
        "temporal_status": "CURRENT",
    }
    resp = client.post("/api/v1/claims/generate-explanation", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "FALSE"
    assert data["word_count"] < 80
    assert data["is_grounded"] is True
    assert "explanation" in data
    assert len(data["explanation"]) > 10
