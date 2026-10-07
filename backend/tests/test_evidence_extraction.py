import pytest
import httpx
from datetime import datetime, timezone

from app.main import app
from app.schemas.evidence import (
    EvidenceCandidate,
    EvidenceExtractionInput,
    RetrievedSource,
)
from app.services.evidence_extractor import (
    EvidenceExtractorService,
    evidence_extractor_service,
)


def test_specification_example_upi_candidate_extraction():
    """
    SPECIFICATION EXAMPLE:
    Claim: "UPI is banned tomorrow."
    Candidate quote: "NPCI has not announced any nationwide shutdown of UPI."
    This candidate may support a FALSE verdict, but it must still pass validation.
    Store source IDs.
    Do not allow the LLM to invent URLs.
    """
    claim = "UPI is banned tomorrow."
    retrieved_source = RetrievedSource(
        source_id="src_npci_official",
        url="https://www.npci.org.in/press-releases/clarification-upi-operational-status",
        title="NPCI Clarification on UPI Operational Status",
        publisher="National Payments Corporation of India (NPCI)",
        domain="npci.org.in",
        published_date="2026-10-06",
        retrieved_date="2026-10-07T12:00:00Z",
        text=(
            "The National Payments Corporation of India (NPCI) has taken note of unverified messages circulating on social media. "
            "NPCI has not announced any nationwide shutdown of UPI. "
            "All unified payments interface rails, IMPS, and RuPay services remain fully operational without disruption."
        ),
        tier=1,
    )

    candidate = evidence_extractor_service.extract_from_source(
        claim_text=claim,
        source=retrieved_source,
        claim_id="clm_upi_001",
    )

    assert candidate is not None
    assert isinstance(candidate, EvidenceCandidate)

    # 1. Extracted fields verification
    assert candidate.title == "NPCI Clarification on UPI Operational Status"
    assert candidate.publisher == "National Payments Corporation of India (NPCI)"
    assert candidate.published_date == "2026-10-06"
    assert candidate.retrieved_date == "2026-10-07T12:00:00Z"

    # 2. Candidate quote matching specification
    expected_quote_fragment = "NPCI has not announced any nationwide shutdown of UPI."
    assert any(expected_quote_fragment in q for q in candidate.candidate_quotes)

    # 3. Relevant text passage extracted
    assert expected_quote_fragment in candidate.relevant_text

    # 4. Stored source ID
    assert candidate.source_id == "src_npci_official"

    # 5. Strict URL binding: Never invent URLs
    assert candidate.url == "https://www.npci.org.in/press-releases/clarification-upi-operational-status"

    # 6. Lifecycle guarantee: Do NOT call something validated evidence yet
    assert candidate.is_validated is False
    assert "pending" in candidate.validation_notes.lower()

    # 7. Stance hint supports a FALSE verdict
    assert candidate.stance_hint == "REFUTES"


def test_url_anti_hallucination_guarantee():
    """
    CRITICAL REQUIREMENT:
    Do not allow the LLM to invent URLs.
    URLs on EvidenceCandidate must strictly match the retrieved source's URL.
    """
    source_url = "https://pib.gov.in/PressReleasePage.aspx?PRID=209841"
    retrieved = RetrievedSource(
        url=source_url,
        title="PIB Fact Check Press Release",
        text="PIB Fact Check confirms the claim that Indian Railways will suspend trains is completely fake.",
    )

    candidate = evidence_extractor_service.extract_from_source(
        claim_text="Railways will suspend all passenger trains.",
        source=retrieved,
    )

    assert candidate is not None
    # URL must strictly be the retrieved source's URL without mutation or hallucination
    assert candidate.url == source_url
    assert candidate.url.startswith("https://pib.gov.in/")


def test_source_id_resolution_and_storage():
    """
    CRITICAL REQUIREMENT:
    Store source IDs.
    Derives canonical source IDs from registry or domain if omitted in retrieved document.
    """
    retrieved_no_id = RetrievedSource(
        url="https://scholarships.gov.in/guidelines/dbt-2026.pdf",
        title="National Scholarship Guidelines",
        text="The Central Sector Scheme continuation is notified for college students with ₹12,000 per annum rate.",
    )

    candidate = evidence_extractor_service.extract_from_source(
        claim_text="College students will receive ₹50,000 scholarship grant.",
        source=retrieved_no_id,
    )

    assert candidate is not None
    # Source ID must be stored
    assert candidate.source_id != ""
    assert "scholarships_gov_in" in candidate.source_id


def test_lifecycle_separation_candidate_not_validated():
    """
    CRITICAL REQUIREMENT:
    Stages:
    Retrieved Evidence -> Candidate Evidence -> Validated Evidence.
    Do NOT call something validated evidence yet.
    """
    retrieved = RetrievedSource(
        source_id="src_thehindu",
        url="https://www.thehindu.com/business/economy/rbi-repo-rate-decision/article123.ece",
        title="RBI Monetary Policy Statement",
        text="The Reserve Bank of India has maintained the repo rate unchanged at 6.5 percent.",
    )

    candidate = evidence_extractor_service.extract_from_source(
        claim_text="RBI increased repo rate by 50 basis points.",
        source=retrieved,
    )

    assert candidate is not None
    # Must be candidate evidence, NOT validated evidence
    assert candidate.is_validated is False
    assert candidate.candidate_id.startswith("cand_")


def test_irrelevant_source_returns_none_and_never_invents_evidence():
    """
    CRITICAL REQUIREMENT:
    If no useful evidence: return empty evidence set.
    Never invent evidence.
    """
    retrieved_irrelevant = RetrievedSource(
        source_id="src_recipes",
        url="https://cooking-blog.example.com/paneer-butter-masala",
        title="Authentic Paneer Butter Masala Recipe",
        text="Heat 2 tablespoons of butter in a pan. Add cumin seeds, finely chopped onions, and ginger garlic paste.",
    )

    # Claim is about financial policy / UPI ban
    candidate = evidence_extractor_service.extract_from_source(
        claim_text="UPI will be banned from tomorrow across India.",
        source=retrieved_irrelevant,
    )

    # No evidence should be invented from an irrelevant document
    assert candidate is None

    # Batch extraction returns empty list
    batch_candidates = evidence_extractor_service.extract_candidates(
        claim_text="UPI will be banned from tomorrow across India.",
        sources=[retrieved_irrelevant],
    )
    assert batch_candidates == []


@pytest.mark.asyncio
async def test_api_extract_evidence_endpoint():
    """Validates the POST /api/v1/claims/extract-evidence endpoint."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "claim_text": "UPI is banned from tomorrow.",
            "claim_id": "clm_001",
            "retrieved_sources": [
                {
                    "source_id": "src_npci",
                    "url": "https://www.npci.org.in/clarification",
                    "title": "NPCI Press Release",
                    "publisher": "NPCI",
                    "text": "NPCI has not announced any nationwide shutdown of UPI. Services are fully active.",
                }
            ],
        }

        res = await client.post("/api/v1/claims/extract-evidence", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["claim_text"] == "UPI is banned from tomorrow."
        assert data["total_candidates"] == 1
        cand = data["candidates"][0]
        assert cand["source_id"] == "src_npci"
        assert cand["url"] == "https://www.npci.org.in/clarification"
        assert cand["is_validated"] is False
        assert any("not announced" in q for q in cand["candidate_quotes"])
