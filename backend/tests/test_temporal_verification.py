import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import TemporalStatus, Verdict
from app.schemas.temporal import (
    ExtractedTemporalDates,
    TemporalEvidenceItem,
    TemporalVerificationInput,
    TemporalVerificationResult,
)
from app.services.temporal_verification import (
    TemporalVerificationService,
    temporal_verification_service,
)


client = TestClient(app)


# ==============================================================================
# 1. Specification Example 1: True Then vs False Now (OUTDATED)
# ==============================================================================

def test_specification_example_1_discontinued_scheme():
    """
    SPECIFICATION EXAMPLE 1:
    Claim:
    "Scheme X currently gives ₹10,000."

    Evidence 2024:
    "Scheme X gives ₹10,000."

    Evidence 2026:
    "Scheme X was discontinued in 2025."

    Result:
    OUTDATED
    Not VERIFIED.
    """
    claim = "Scheme X currently gives ₹10,000."
    evidence_items = [
        TemporalEvidenceItem(
            evidence_id="ev_2024",
            text="Scheme X gives ₹10,000.",
            date="2024",
        ),
        TemporalEvidenceItem(
            evidence_id="ev_2026",
            text="Scheme X was discontinued in 2025.",
            date="2026",
        ),
    ]

    result = temporal_verification_service.verify_temporality(
        claim_text=claim,
        evidence_items=evidence_items,
        current_date_str="2026-10-07",
    )

    # Core requirements
    assert result.verdict == Verdict.OUTDATED
    assert result.verdict != Verdict.VERIFIED
    assert result.temporal_status == TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE

    # Distinction between TRUE THEN and TRUE NOW
    assert result.true_then is True
    assert result.true_now is False

    # Date extraction validation
    assert result.dates.current_date == "2026-10-07"
    assert result.dates.evidence_date == "2026"
    assert result.dates.expiry_date == "2025"
    assert result.dates.is_present_claim is True
    assert "OUTDATED" in result.explanation


# ==============================================================================
# 2. Specification Example 2: Historical Claim (VERIFIED)
# ==============================================================================

def test_specification_example_2_historical_announcement():
    """
    SPECIFICATION EXAMPLE 2:
    Claim:
    "Government announced X in 2024."

    Evidence confirms announcement in 2024.

    Result:
    VERIFIED
    because the claim itself is historical.
    """
    claim = "Government announced X in 2024."
    evidence_items = [
        TemporalEvidenceItem(
            evidence_id="ev_announcement",
            text="Government announced Scheme X on June 4, 2024 in the official gazette.",
            date="2024",
        )
    ]

    result = temporal_verification_service.verify_temporality(
        claim_text=claim,
        evidence_items=evidence_items,
        current_date_str="2026-10-07",
    )

    # Core requirements
    assert result.verdict == Verdict.VERIFIED
    assert result.temporal_status == TemporalStatus.HISTORICAL_TRUE

    # Historical truth remains true
    assert result.true_then is True
    assert result.true_now is True

    # Date extraction validation
    assert result.dates.claim_date == "2024"
    assert result.dates.is_historical_claim is True
    assert result.dates.evidence_date == "2024"
    assert "historical" in result.explanation.lower()


# ==============================================================================
# 3. Expired Validity / Historical Recirculation
# ==============================================================================

def test_expired_order_recirculated_as_current():
    """
    Claim asserts a present disruption based on an expired historical order:
    Claim: "Railways suspended all passenger trains starting tomorrow."
    Evidence: 2020 circular with "Passenger train services suspended till 31st March 2020."
    """
    claim = "Railways suspended all passenger trains starting tomorrow."
    evidence_items = [
        TemporalEvidenceItem(
            evidence_id="ev_railway_2020",
            text="Passenger train services suspended till 31st March 2020.",
            date="2020-03-22",
            expiry_date="2020-03-31",
        )
    ]

    result = temporal_verification_service.verify_temporality(
        claim_text=claim,
        evidence_items=evidence_items,
        current_date_str="2026-10-07",
    )

    assert result.verdict == Verdict.OUTDATED
    assert result.temporal_status == TemporalStatus.EXPIRED
    assert result.true_then is True
    assert result.true_now is False
    assert result.dates.expiry_date == "2020-03-31"


# ==============================================================================
# 4. Active Current Policy (CURRENT)
# ==============================================================================

def test_active_current_policy():
    """
    Claim asserts current policy, corroborated by 2026 notification with no discontinuation.
    """
    claim = "Ministry of Education notified PM Higher Merit Scholarship for 2026."
    evidence_items = [
        TemporalEvidenceItem(
            evidence_id="ev_active_2026",
            text="Central Sector Scheme scholarship continuation is officially notified for 2026.",
            date="2026-09-12",
        )
    ]

    result = temporal_verification_service.verify_temporality(
        claim_text=claim,
        evidence_items=evidence_items,
        current_date_str="2026-10-07",
    )

    assert result.verdict == Verdict.VERIFIED
    assert result.temporal_status == TemporalStatus.CURRENT
    assert result.true_then is True
    assert result.true_now is True


# ==============================================================================
# 5. Unknown Dates (DATE_UNKNOWN)
# ==============================================================================

def test_undated_evidence_returns_date_unknown():
    """
    When no temporal anchors are available in evidence or claim,
    status must be DATE_UNKNOWN without assuming currency.
    """
    result = temporal_verification_service.verify_temporality(
        claim_text="General claim without dates.",
        evidence_items=[],
        current_date_str="2026-10-07",
    )

    assert result.temporal_status == TemporalStatus.DATE_UNKNOWN
    assert result.verdict == Verdict.CANNOT_BE_CONFIRMED


# ==============================================================================
# 6. TemporalStatus Enum Completeness
# ==============================================================================

def test_temporal_status_enum_values():
    """
    Verifies all 5 required TemporalStatus enum variants exist:
    - CURRENT
    - HISTORICAL_TRUE
    - EXPIRED
    - CONTRADICTED_BY_NEWER_EVIDENCE
    - DATE_UNKNOWN
    """
    assert TemporalStatus.CURRENT == "CURRENT"
    assert TemporalStatus.HISTORICAL_TRUE == "HISTORICAL_TRUE"
    assert TemporalStatus.EXPIRED == "EXPIRED"
    assert TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE == "CONTRADICTED_BY_NEWER_EVIDENCE"
    assert TemporalStatus.DATE_UNKNOWN == "DATE_UNKNOWN"


# ==============================================================================
# 7. FastAPI Endpoint Tests
# ==============================================================================

def test_api_verify_temporality_example_1():
    """Test POST /api/v1/claims/verify-temporality with Example 1."""
    payload = {
        "claim_text": "Scheme X currently gives ₹10,000.",
        "evidence_items": [
            {
                "evidence_id": "ev_2024",
                "text": "Scheme X gives ₹10,000.",
                "date": "2024",
            },
            {
                "evidence_id": "ev_2026",
                "text": "Scheme X was discontinued in 2025.",
                "date": "2026",
            },
        ],
        "current_date": "2026-10-07",
    }

    response = client.post("/api/v1/claims/verify-temporality", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["verdict"] == "OUTDATED"
    assert data["temporal_status"] == "CONTRADICTED_BY_NEWER_EVIDENCE"
    assert data["true_then"] is True
    assert data["true_now"] is False
    assert data["dates"]["expiry_date"] == "2025"


def test_api_verify_temporality_example_2():
    """Test POST /api/v1/claims/verify-temporality with Example 2."""
    payload = {
        "claim_text": "Government announced X in 2024.",
        "evidence_items": [
            {
                "evidence_id": "ev_2024",
                "text": "Government announced X on June 4, 2024.",
                "date": "2024",
            }
        ],
        "current_date": "2026-10-07",
    }

    response = client.post("/api/v1/claims/verify-temporality", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["verdict"] == "VERIFIED"
    assert data["temporal_status"] == "HISTORICAL_TRUE"
    assert data["true_then"] is True
    assert data["true_now"] is True
    assert data["dates"]["claim_date"] == "2024"
    assert data["dates"]["is_historical_claim"] is True
