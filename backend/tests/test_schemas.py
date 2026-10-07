from datetime import date, datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas import (
    CacheRecord,
    Check,
    Claim,
    ClaimResult,
    ConfidenceLevel,
    Evidence,
    Feedback,
    FeedbackType,
    Input,
    InputType,
    ProcessingStage,
    ProcessingStatus,
    RuleTrace,
    Source,
    User,
    UserRole,
    Verdict,
    VerificationResult,
)


# ==============================================================================
# 1. VALID SCHEMA TESTS
# ==============================================================================

def test_valid_claim_schema():
    """Validates Claim model using the exact example from specification."""
    claim_data = {
        "claim_id": "clm_001",
        "text": "The government launched scheme X in 2025.",
        "language": "en",
        "normalized_claim": "The government launched scheme X in 2025.",
        "entities": ["government", "scheme X"],
        "dates": ["2025"],
        "numbers": [2025],
    }
    claim = Claim(**claim_data)
    assert claim.claim_id == "clm_001"
    assert claim.text == "The government launched scheme X in 2025."
    assert claim.language == "en"
    assert claim.numbers == [2025]


def test_valid_evidence_schema():
    """Validates Evidence model using the exact example from specification."""
    evidence_data = {
        "evidence_id": "ev_001",
        "source_url": "https://example.gov.in/page",
        "title": "Official announcement",
        "publisher": "Government Department",
        "source_tier": 1,
        "published_date": "2025-06-01",
        "retrieved_at": "2026-10-07T12:00:00Z",
        "exact_quote": "The Department of Higher Education hereby announces Scheme X.",
    }
    evidence = Evidence(**evidence_data)
    assert evidence.evidence_id == "ev_001"
    assert evidence.source_url == "https://example.gov.in/page"
    assert evidence.source_tier == 1
    assert evidence.published_date == "2025-06-01"


def test_valid_claim_result_schema():
    """Validates ClaimResult model using the exact example from specification."""
    result_data = {
        "claim_id": "clm_001",
        "verdict": "VERIFIED",
        "confidence": "HIGH",
        "explanation": "Corroborated by Gazette of India.",
        "evidence_ids": ["ev_001"],
        "rule_trace": [],
    }
    result = ClaimResult(**result_data)
    assert result.claim_id == "clm_001"
    assert result.verdict == Verdict.VERIFIED
    assert result.confidence == "HIGH"
    assert result.evidence_ids == ["ev_001"]


def test_valid_all_core_models():
    """Validates User, Input, RuleTrace, ProcessingStage, VerificationResult, Check, Feedback, Source, CacheRecord."""
    user = User(user_id="usr_101", phone_number="+919820112345", role=UserRole.CITIZEN)
    assert user.user_id == "usr_101"

    inp = Input(input_id="inp_01", input_type=InputType.TEXT, raw_content="Viral forward text")
    assert inp.input_type == InputType.TEXT

    rule = RuleTrace(rule_id="RULE-01", rule_name="Gazette Match", passed=True, details="Matched notice")
    assert rule.passed is True

    stage = ProcessingStage(stage=ProcessingStatus.VALIDATING, status="COMPLETED")
    assert stage.stage == ProcessingStatus.VALIDATING

    claim_res = ClaimResult(
        claim_id="clm_001",
        verdict=Verdict.FALSE,
        confidence=ConfidenceLevel.HIGH,
        explanation="Directly contradicted by official rates.",
        evidence_ids=["ev_001"],
        rule_trace=[rule],
    )

    verif_res = VerificationResult(
        result_id="res_01",
        check_id="chk_01",
        overall_verdict=Verdict.FALSE,
        summary="Claim is false.",
        claim_results=[claim_res],
    )
    assert verif_res.overall_verdict == Verdict.FALSE

    chk = Check(
        check_id="chk_01",
        user_id="usr_101",
        input=inp,
        status=ProcessingStatus.COMPLETED,
        claims=[
            Claim(
                claim_id="clm_001",
                text="Scheme grants ₹50,000.",
                normalized_claim="Scheme grants ₹50,000.",
            )
        ],
        stages=[stage],
        result=verif_res,
    )
    assert chk.check_id == "chk_01"

    fb = Feedback(
        feedback_id="fb_01",
        check_id="chk_01",
        feedback_type=FeedbackType.DISPUTE,
        comments="Local university announced separate grant.",
        counter_evidence_urls=["https://example.gov.in/order"],
    )
    assert fb.feedback_type == FeedbackType.DISPUTE

    src = Source(
        source_id="src_01",
        name="The Gazette of India",
        domain="egazette.gov.in",
        source_tier=1,
        category="STATE_GAZETTE",
        records_indexed=1420500,
    )
    assert src.source_tier == 1

    cache = CacheRecord(
        cache_id="cch_01",
        content_hash="a1b2c3d4e5f67890abcdef1234567890",
        canonical_claim="Scheme grants ₹50,000.",
        verdict=Verdict.FALSE,
        verification_result_id="res_01",
    )
    assert cache.verdict == Verdict.FALSE


# ==============================================================================
# 2. INVALID VERDICT TESTS
# ==============================================================================

@pytest.mark.parametrize("invalid_verdict", ["TRUE", "UNVERIFIED", "MAYBE", "FAKE", "PLAUSIBLE", ""])
def test_invalid_verdict_raises_validation_error(invalid_verdict):
    """Ensures arbitrary or non-canonical verdicts are strictly rejected."""
    with pytest.raises(ValidationError) as exc_info:
        ClaimResult(
            claim_id="clm_001",
            verdict=invalid_verdict,
            confidence="HIGH",
            explanation="Test explanation",
        )
    assert "verdict" in str(exc_info.value)


def test_five_canonical_verdicts_are_valid():
    """Ensures each of the 5 canonical verdicts is accepted."""
    for canonical in [
        Verdict.VERIFIED,
        Verdict.FALSE,
        Verdict.OUTDATED,
        Verdict.PARTLY_SUPPORTED,
        Verdict.CANNOT_BE_CONFIRMED,
    ]:
        cr = ClaimResult(
            claim_id="clm_test",
            verdict=canonical,
            confidence="HIGH",
            explanation="Reason",
        )
        assert cr.verdict == canonical


# ==============================================================================
# 3. MISSING CLAIM TESTS
# ==============================================================================

def test_missing_claim_text_raises_validation_error():
    """Ensures claim cannot be instantiated without text."""
    with pytest.raises(ValidationError) as exc_info:
        Claim(
            claim_id="clm_001",
            # text is missing
            normalized_claim="Normalized statement",
        )
    assert "text" in str(exc_info.value)


@pytest.mark.parametrize("blank_text", ["", "   ", "\n\t "])
def test_empty_or_whitespace_claim_text_raises_validation_error(blank_text):
    """Ensures empty or whitespace claim text is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Claim(
            claim_id="clm_001",
            text=blank_text,
            normalized_claim="Normalized statement",
        )
    assert "text" in str(exc_info.value)


def test_missing_claim_id_raises_validation_error():
    """Ensures claim must have an identifier."""
    with pytest.raises(ValidationError) as exc_info:
        Claim(
            text="The government launched scheme X.",
            normalized_claim="The government launched scheme X.",
        )
    assert "claim_id" in str(exc_info.value)


# ==============================================================================
# 4. INVALID EVIDENCE TESTS
# ==============================================================================

@pytest.mark.parametrize("bad_tier", [0, 4, 10, -1])
def test_invalid_evidence_source_tier_raises_validation_error(bad_tier):
    """Ensures source_tier must be 1, 2, or 3."""
    with pytest.raises(ValidationError) as exc_info:
        Evidence(
            evidence_id="ev_001",
            source_url="https://example.gov.in/page",
            title="Title",
            publisher="Ministry",
            source_tier=bad_tier,
            retrieved_at="2026-10-07T12:00:00Z",
            exact_quote="Quoted text",
        )
    assert "source_tier" in str(exc_info.value)


@pytest.mark.parametrize("bad_url", ["not-a-url", "ftp://invalid-scheme.com", "javascript:alert(1)", ""])
def test_invalid_evidence_url_raises_validation_error(bad_url):
    """Ensures source_url must be a valid HTTP/HTTPS address."""
    with pytest.raises(ValidationError) as exc_info:
        Evidence(
            evidence_id="ev_001",
            source_url=bad_url,
            title="Title",
            publisher="Ministry",
            source_tier=1,
            retrieved_at="2026-10-07T12:00:00Z",
            exact_quote="Quoted text",
        )
    assert "source_url" in str(exc_info.value)


def test_missing_exact_quote_in_evidence_raises_validation_error():
    """Ensures evidence cannot be created without an exact documentary quote."""
    with pytest.raises(ValidationError) as exc_info:
        Evidence(
            evidence_id="ev_001",
            source_url="https://example.gov.in/page",
            title="Title",
            publisher="Ministry",
            source_tier=1,
            retrieved_at="2026-10-07T12:00:00Z",
            # exact_quote is missing
        )
    assert "exact_quote" in str(exc_info.value)


# ==============================================================================
# 5. MALFORMED DATES TESTS
# ==============================================================================

@pytest.mark.parametrize("malformed_date", ["invalid-date", "2025-13-45", "not_a_day", "yesterday", "99/99/9999"])
def test_malformed_evidence_date_raises_validation_error(malformed_date):
    """Ensures malformed published_date strings are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Evidence(
            evidence_id="ev_001",
            source_url="https://example.gov.in/page",
            title="Title",
            publisher="Ministry",
            source_tier=1,
            published_date=malformed_date,
            retrieved_at="2026-10-07T12:00:00Z",
            exact_quote="Quoted text",
        )
    assert "published_date" in str(exc_info.value)


def test_valid_evidence_dates_normalized():
    """Ensures valid date formats are parsed and formatted as YYYY-MM-DD."""
    ev1 = Evidence(
        evidence_id="ev_01",
        source_url="https://example.gov.in/page",
        title="Title",
        publisher="Ministry",
        source_tier=1,
        published_date="2025-06-01",
        retrieved_at="2026-10-07T12:00:00Z",
        exact_quote="Quote",
    )
    assert ev1.published_date == "2025-06-01"

    ev2 = Evidence(
        evidence_id="ev_02",
        source_url="https://example.gov.in/page",
        title="Title",
        publisher="Ministry",
        source_tier=1,
        published_date=date(2025, 6, 1),
        retrieved_at="2026-10-07T12:00:00Z",
        exact_quote="Quote",
    )
    assert ev2.published_date == "2025-06-01"

    ev3 = Evidence(
        evidence_id="ev_03",
        source_url="https://example.gov.in/page",
        title="Title",
        publisher="Ministry",
        source_tier=1,
        published_date=None,
        retrieved_at="2026-10-07T12:00:00Z",
        exact_quote="Quote",
    )
    assert ev3.published_date is None
