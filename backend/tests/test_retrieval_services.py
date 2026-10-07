import pytest
import httpx
from unittest.mock import MagicMock, patch

from app.main import app
from app.schemas.enums import SourceTier
from app.schemas.retrieval import CandidateEvidence
from app.services.retrieval.base import FactCheckProvider, WebSearchProvider
from app.services.retrieval.google_factcheck import GoogleFactCheckProvider
from app.services.retrieval.tavily_search import TavilySearchProvider
from app.services.retrieval.composite_search import CompositeWebSearchProvider, DuckDuckGoSearchProvider
from app.services.retrieval.pipeline import EvidenceRetrievalPipeline


# ==============================================================================
# Mock Providers for Deterministic Testing
# ==============================================================================

class MockFactCheckProvider(FactCheckProvider):
    @property
    def provider_name(self) -> str:
        return "mock_fact_check"

    def search_claims(self, query: str, language_code=None, max_results=5):
        if "upi" in query.lower() or "banned" in query.lower():
            return [
                CandidateEvidence(
                    url="https://pib.gov.in/PressReleasePage.aspx?PRID=99102",
                    title="PIB Fact Check: Viral claim about UPI shutdown is fake",
                    snippet="PIB Fact Check clarifies that UPI is not being banned. Digital payments continue uninterrupted.",
                    publisher="PIB Fact Check",
                    domain="pib.gov.in",
                    source_type="FACT_CHECK",
                    publish_date="2026-10-06",
                    rating="Fake",
                    credibility_score=1.0,
                ),
                CandidateEvidence(
                    url="https://boomlive.in/fact-check/upi-banned-tomorrow-viral-claim",
                    title="BOOM Live: No, UPI is not getting banned from tomorrow",
                    snippet="BOOM found no official circular regarding UPI ban. The viral message is completely baseless.",
                    publisher="BOOM Live",
                    domain="boomlive.in",
                    source_type="FACT_CHECK",
                    publish_date="2026-10-06",
                    rating="False",
                    credibility_score=0.85,
                ),
            ]
        return []


class MockSearchProvider(WebSearchProvider):
    @property
    def provider_name(self) -> str:
        return "mock_web_search"

    def search(self, query: str, max_results=5):
        q = query.lower()
        if "npci" in q or "upi" in q:
            return [
                # Official NPCI Information
                CandidateEvidence(
                    url="https://www.npci.org.in/press-releases/clarification-upi-services",
                    title="NPCI Official Release: UPI services operate smoothly across all banks",
                    snippet="National Payments Corporation of India (NPCI) advises users to ignore false rumours regarding UPI closure.",
                    publisher="NPCI",
                    domain="npci.org.in",
                    source_type="SEARCH",
                    publish_date="2026-10-06",
                    credibility_score=0.98,
                    raw_content="National Payments Corporation of India (NPCI) advises users to ignore false rumours regarding UPI closure. All UPI transactions remain fully functional.",
                ),
                # Reputable News Article
                CandidateEvidence(
                    url="https://www.thehindu.com/business/upi-ban-rumours-rejected-by-npci/article12345.ece",
                    title="The Hindu: UPI ban rumours rejected by NPCI and Ministry of Finance",
                    snippet="The government and NPCI have categorically denied reports that UPI services will be halted tomorrow.",
                    publisher="The Hindu",
                    domain="thehindu.com",
                    source_type="SEARCH",
                    publish_date="2026-10-06",
                    credibility_score=0.85,
                    raw_content="The government and NPCI have categorically denied reports that UPI services will be halted tomorrow.",
                ),
            ]
        return []


# ==============================================================================
# 1. FactCheckProvider & GoogleFactCheckProvider Tests
# ==============================================================================

def test_google_fact_check_tools_parsing():
    """Validates parsing of Google Fact Check Tools API ClaimReview responses."""
    mock_response = {
        "claims": [
            {
                "text": "UPI will be banned from tomorrow across India",
                "claimant": "WhatsApp Forward",
                "claimDate": "2026-10-06T10:00:00Z",
                "claimReview": [
                    {
                        "publisher": {"name": "PIB Fact Check", "site": "pib.gov.in"},
                        "url": "https://pib.gov.in/PressReleasePage.aspx?PRID=99102",
                        "title": "Viral message on UPI ban is false",
                        "reviewDate": "2026-10-06",
                        "textualRating": "Fake",
                        "languageCode": "en",
                    }
                ],
            }
        ]
    }

    provider = GoogleFactCheckProvider(api_key="test-key")
    candidates = provider._parse_claims_response(mock_response)
    assert len(candidates) == 1
    assert candidates[0].domain == "pib.gov.in"
    assert candidates[0].publisher == "PIB Fact Check"
    assert candidates[0].rating == "Fake"
    assert candidates[0].source_type == "FACT_CHECK"


def test_google_fact_check_graceful_degradation_without_key():
    """Unconfigured API key must safely return empty list without crashing."""
    provider = GoogleFactCheckProvider(api_key=None)
    results = provider.search_claims("UPI banned tomorrow")
    assert results == []


# ==============================================================================
# 2. WebSearchProvider & Tavily / Composite Provider Tests
# ==============================================================================

def test_tavily_search_parsing():
    """Validates parsing of Tavily search response JSON."""
    mock_response = {
        "results": [
            {
                "title": "NPCI clarifies UPI is not banned",
                "url": "https://www.npci.org.in/press-releases/clarification",
                "content": "NPCI has issued a clarification dismissing claims of UPI ban...",
                "score": 0.95,
                "published_date": "2026-10-06",
            }
        ]
    }

    provider = TavilySearchProvider(api_key="tvly-mock-key")
    candidates = provider._parse_results(mock_response)
    assert len(candidates) == 1
    assert candidates[0].domain == "npci.org.in"
    assert candidates[0].source_type == "SEARCH"
    assert candidates[0].publish_date == "2026-10-06"


def test_composite_provider_multi_provider_resilience():
    """
    CRITICAL REQUIREMENT:
    Do not make the entire system depend on one provider.
    Fails over from primary to secondary provider seamlessly.
    """
    # Primary provider fails / returns empty
    failing_primary = MagicMock(spec=WebSearchProvider)
    failing_primary.provider_name = "failing_primary"
    failing_primary.search.side_effect = Exception("Rate limit exceeded")

    # Secondary provider succeeds
    healthy_secondary = MagicMock(spec=WebSearchProvider)
    healthy_secondary.provider_name = "healthy_secondary"
    healthy_secondary.search.return_value = [
        CandidateEvidence(
            url="https://thehindu.com/news/123",
            title="News Article",
            snippet="Report on official clarification",
            domain="thehindu.com",
            source_type="SEARCH",
        )
    ]

    composite = CompositeWebSearchProvider(providers=[failing_primary, healthy_secondary])
    results = composite.search("test query")
    assert len(results) == 1
    assert results[0].domain == "thehindu.com"


# ==============================================================================
# 3. Specification Pipeline Example: "UPI is banned from tomorrow."
# ==============================================================================

def test_specification_example_upi_ban_retrieval_pipeline():
    """
    SPECIFICATION EXAMPLE:
    Claim: "UPI is banned from tomorrow."
    Pipeline retrieves:
    - fact-check article (e.g. PIB Fact Check / BOOM Live)
    - official NPCI information (npci.org.in)
    - reputable news article (e.g. The Hindu)
    Returns structured candidates.
    """
    pipeline = EvidenceRetrievalPipeline(
        fact_check_provider=MockFactCheckProvider(),
        search_provider=MockSearchProvider(),
    )

    result = pipeline.retrieve_evidence_for_claim(
        claim_text="UPI is banned from tomorrow.",
        fetch_pages=False,  # Use mock snippets
    )

    assert result.status == "SUCCESS"
    assert result.total_candidates >= 3
    assert result.fact_check_count >= 1
    assert result.search_count >= 1

    domains = [c.domain for c in result.candidates]
    # 1. Fact-check article retrieved
    assert "pib.gov.in" in domains or "boomlive.in" in domains
    # 2. Official NPCI information retrieved
    assert "npci.org.in" in domains
    # 3. Reputable news article retrieved
    assert "thehindu.com" in domains

    # Verify candidate source types
    source_types = [c.source_type for c in result.candidates]
    assert "FACT_CHECK" in source_types
    assert "SEARCH" in source_types

    # Verify synthesized EvidenceItem citations
    assert len(result.evidence_items) >= 2
    # NPCI must be categorized as Tier 1 official
    npci_evidence = next((e for e in result.evidence_items if e.domain == "npci.org.in"), None)
    assert npci_evidence is not None
    assert npci_evidence.tier == SourceTier.TIER_1_PRIMARY
    assert npci_evidence.is_authoritative is True


# ==============================================================================
# 4. Candidate Deduplication & Source Ranking Tests
# ==============================================================================

def test_candidate_deduplication():
    """Ensures duplicate URLs and duplicate domain+title combinations are deduplicated."""
    pipeline = EvidenceRetrievalPipeline(
        fact_check_provider=MockFactCheckProvider(),
        search_provider=MockSearchProvider(),
    )

    raw_candidates = [
        CandidateEvidence(
            url="https://pib.gov.in/press/101",
            title="Fact Check on UPI",
            domain="pib.gov.in",
            snippet="First snippet",
        ),
        CandidateEvidence(
            url="https://pib.gov.in/press/101/",  # Duplicate with trailing slash
            title="Fact Check on UPI",
            domain="pib.gov.in",
            snippet="Second snippet",
        ),
        CandidateEvidence(
            url="https://different.gov.in/press/102",
            title="Fact Check on UPI",
            domain="different.gov.in",
            snippet="Distinct domain",
        ),
    ]

    deduped = pipeline._deduplicate_candidates(raw_candidates)
    assert len(deduped) == 2


def test_source_ranking_enforces_tier_precedence_and_filters_untrusted():
    """
    CRITICAL REQUIREMENT:
    Unknown/untrusted sources must NOT automatically become strong evidence.
    Official Tier 1 sources must be ranked ahead of Tier 2 and untrusted.
    """
    pipeline = EvidenceRetrievalPipeline()

    candidates = [
        CandidateEvidence(
            url="https://random-scam-blog.xyz/post",
            title="Viral Leak",
            domain="random-scam-blog.xyz",
            snippet="Conspiracy theory",
        ),
        CandidateEvidence(
            url="https://thehindu.com/article",
            title="News Report",
            domain="thehindu.com",
            snippet="Journalistic investigation",
        ),
        CandidateEvidence(
            url="https://npci.org.in/notice",
            title="Official Directive",
            domain="npci.org.in",
            snippet="Regulatory order",
        ),
    ]

    ranked = pipeline._rank_and_filter_candidates(candidates)

    # 1. Tier 1 official body (NPCI) must be ranked #1
    assert ranked[0].domain == "npci.org.in"
    assert ranked[0].tier == 1
    assert ranked[0].is_authoritative is True

    # 2. Tier 2 reputable news (The Hindu) must be ranked #2
    assert ranked[1].domain == "thehindu.com"
    assert ranked[1].tier == 2

    # 3. Untrusted blog gets credibility_score=0.0 and cannot become strong evidence
    untrusted = next(c for c in ranked if c.domain == "random-scam-blog.xyz")
    assert untrusted.tier is None
    assert untrusted.credibility_score == 0.0


# ==============================================================================
# 5. Empty Evidence & Never Invent Evidence Guarantee
# ==============================================================================

def test_empty_evidence_when_no_useful_sources_found():
    """
    CRITICAL REQUIREMENT:
    If no useful evidence: return empty evidence set.
    Never invent evidence.
    """
    empty_fact_check = MagicMock(spec=FactCheckProvider)
    empty_fact_check.search_claims.return_value = []

    empty_search = MagicMock(spec=WebSearchProvider)
    empty_search.search.return_value = []

    pipeline = EvidenceRetrievalPipeline(
        fact_check_provider=empty_fact_check,
        search_provider=empty_search,
    )

    result = pipeline.retrieve_evidence_for_claim("Completely obscure non-existent claim assertion.")
    assert result.status == "EMPTY"
    assert result.candidates == []
    assert result.evidence_items == []
    assert result.total_candidates == 0


# ==============================================================================
# 6. FastAPI Endpoint Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_api_retrieve_evidence_endpoint():
    """Validates POST /api/v1/claims/retrieve-evidence endpoint."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "claim_text": "UPI is banned from tomorrow in India",
            "language": "en",
            "max_results": 5,
        }
        res = await client.post("/api/v1/claims/retrieve-evidence", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "claim_text" in data
        assert "candidates" in data
        assert "evidence_items" in data
        assert "status" in data
