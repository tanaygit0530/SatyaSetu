import pytest
import httpx

from app.main import app
from app.schemas.claim import AtomicClaim
from app.schemas.query import ClaimSearchQueries, SearchQueryGenerationOutput
from app.services.query_generator import (
    EvidenceQueryGeneratorService,
    evidence_query_generator_service,
)


# ==============================================================================
# 1. Specification Example: UPI Ban Query Generation
# ==============================================================================

def test_specification_example_upi_ban_queries():
    """
    Verifies the user's exact specification example:
    Claim: "UPI will be banned from tomorrow."
    Queries:
      Original:      "UPI बंद होने वाला है"
      English:       "UPI banned India tomorrow"
      Entity:        "NPCI UPI ban announcement"
      Contradiction: "NPCI UPI not banned official"
    """
    claim = AtomicClaim(
        claim_id="clm_001",
        original_text="UPI will be banned from tomorrow.",
        text="UPI will be banned from tomorrow.",
        normalized_claim="UPI will be banned from tomorrow.",
        entities=["UPI"],
        locations=["India"],
        dates=["tomorrow"],
        claim_type="policy",
        check_worthiness=True,
    )

    result = evidence_query_generator_service.generate_queries_for_claim(claim)

    # 1. Original-language query
    assert "UPI बंद होने वाला है" in result.original_query

    # 2. English query
    assert "UPI banned India tomorrow" in result.english_query

    # 3. Entity-focused query
    assert "NPCI" in result.entity_query
    assert "UPI ban announcement" in result.entity_query

    # 4. Number/date-aware query
    assert "UPI" in result.number_date_query
    assert "tomorrow" in result.number_date_query or "2026" in result.number_date_query

    # 5. Contradiction query
    assert "NPCI" in result.contradiction_query
    assert "UPI not banned official" in result.contradiction_query

    # Deduplicated list assertions
    assert len(result.all_queries) >= 3
    assert len(result.all_queries) <= 6


# ==============================================================================
# 2. Financial 5% Fee Query Generation
# ==============================================================================

def test_financial_fee_query_generation():
    """
    Validates queries generated for second half of compound prompt:
    'All users will have to pay a 5% fee.'
    """
    claim = AtomicClaim(
        claim_id="clm_002",
        original_text="All UPI users will have to pay a 5% fee.",
        text="All UPI users will have to pay a 5% fee.",
        normalized_claim="All UPI users will have to pay a 5% fee.",
        entities=["UPI"],
        numbers=["5%"],
        claim_type="financial",
        check_worthiness=True,
    )

    result = evidence_query_generator_service.generate_queries_for_claim(claim)

    assert "NPCI" in result.entity_query
    assert "5%" in result.number_date_query
    assert "NPCI" in result.contradiction_query
    assert "no fee" in result.contradiction_query or "clarification" in result.contradiction_query


# ==============================================================================
# 3. Railway Passenger Train Suspension Query Generation
# ==============================================================================

def test_railway_train_suspension_query_generation():
    """Validates authority (Indian Railways) and denial queries for railway rumor."""
    claim = AtomicClaim(
        claim_id="clm_003",
        original_text="Indian Railways has ordered complete suspension of passenger trains starting tomorrow.",
        text="Indian Railways has ordered complete suspension of passenger trains starting tomorrow.",
        normalized_claim="Indian Railways has ordered complete suspension of passenger trains starting tomorrow.",
        entities=["Indian Railways"],
        dates=["tomorrow"],
        claim_type="policy",
        check_worthiness=True,
    )

    result = evidence_query_generator_service.generate_queries_for_claim(claim)

    assert "Indian Railways" in result.entity_query
    assert "Indian Railways" in result.english_query
    assert "not suspended" in result.contradiction_query or "clarification" in result.contradiction_query


# ==============================================================================
# 4. Education PMSSY Merit Scholarship Query Generation
# ==============================================================================

def test_education_scholarship_query_generation():
    """Validates authority (Ministry of Education) and amount queries."""
    claim = AtomicClaim(
        claim_id="clm_004",
        original_text="Ministry of Education launched the PMSSY scholarship with ₹50,000 DBT grant.",
        text="Ministry of Education launched the PMSSY scholarship with ₹50,000 DBT grant.",
        normalized_claim="Ministry of Education launched the PMSSY scholarship with ₹50,000 DBT grant.",
        entities=["Ministry of Education", "PMSSY"],
        numbers=[50000],
        claim_type="financial",
        check_worthiness=True,
    )

    result = evidence_query_generator_service.generate_queries_for_claim(claim)

    assert "Ministry of Education" in result.entity_query
    assert "50000" in result.number_date_query
    assert len(result.all_queries) <= 6


# ==============================================================================
# 5. Vernacular (Marathi) Query Generation
# ==============================================================================

def test_marathi_vernacular_query_generation():
    """Validates queries generated for Marathi vernacular claim."""
    claim = AtomicClaim(
        claim_id="clm_005",
        original_text="महाराष्ट्र शासनाने सर्व शाळा 15 ऑक्टोबरपर्यंत बंद ठेवण्याचा निर्णय घेतला आहे.",
        text="महाराष्ट्र शासनाने सर्व शाळा 15 ऑक्टोबरपर्यंत बंद ठेवण्याचा निर्णय घेतला आहे.",
        normalized_claim="महाराष्ट्र शासनाने सर्व शाळा 15 ऑक्टोबरपर्यंत बंद ठेवण्याचा निर्णय घेतला आहे.",
        language="mr",
        locations=["Maharashtra"],
        dates=["15 ऑक्टोबर"],
        claim_type="policy",
        check_worthiness=True,
    )

    result = evidence_query_generator_service.generate_queries_for_claim(claim)

    # Original query must preserve Marathi terms
    assert any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in result.original_query)
    # English query formulated with English keywords
    assert "Maharashtra" in result.english_query or "school" in result.english_query.lower()


# ==============================================================================
# 6. Deduplication and Volume Capping Rules
# ==============================================================================

def test_query_deduplication_and_capping():
    """
    Ensures that queries within all_queries are strictly unique
    (case-insensitive and whitespace normalized) and capped reasonably (<= 6).
    """
    claim = AtomicClaim(
        claim_id="clm_006",
        original_text="Drinking water pipeline in Ward 14 has been chemically contaminated.",
        text="Drinking water pipeline in Ward 14 has been chemically contaminated.",
        normalized_claim="Drinking water pipeline in Ward 14 has been chemically contaminated.",
        locations=["Ward 14"],
        claim_type="health",
        check_worthiness=True,
    )

    result = evidence_query_generator_service.generate_queries_for_claim(claim)

    # Check for strict uniqueness
    normalized_keys = [q.lower().strip() for q in result.all_queries]
    assert len(normalized_keys) == len(set(normalized_keys)), "Duplicate queries found in all_queries!"

    # Check reasonable volume constraint (<= 6)
    assert len(result.all_queries) <= 6


def test_batch_query_generation_total_unique_count():
    """Verifies batch query generation returns accurate total unique queries."""
    claim_1 = AtomicClaim(
        claim_id="clm_001",
        original_text="UPI will be banned from tomorrow.",
        text="UPI will be banned from tomorrow.",
        normalized_claim="UPI will be banned from tomorrow.",
        entities=["UPI"],
    )
    claim_2 = AtomicClaim(
        claim_id="clm_002",
        original_text="All UPI users will have to pay a 5% fee.",
        text="All UPI users will have to pay a 5% fee.",
        normalized_claim="All UPI users will have to pay a 5% fee.",
        entities=["UPI"],
        numbers=["5%"],
    )

    batch_output = evidence_query_generator_service.generate_queries_batch([claim_1, claim_2])

    assert len(batch_output.claim_queries) == 2
    assert batch_output.total_unique_queries >= 5
    assert batch_output.total_unique_queries <= 12


# ==============================================================================
# 7. FastAPI Endpoint Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_api_generate_queries_endpoint():
    """Tests POST /api/v1/claims/generate-queries endpoint."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "claim_text": "UPI will be banned from tomorrow.",
            "claim_id": "clm_001",
        }
        response = await client.post("/api/v1/claims/generate-queries", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "claim_queries" in data
        assert len(data["claim_queries"]) == 1
        q_item = data["claim_queries"][0]
        assert "UPI बंद होने वाला है" in q_item["original_query"]
        assert "UPI banned India tomorrow" in q_item["english_query"]
        assert "NPCI" in q_item["entity_query"]
        assert "NPCI UPI not banned official" in q_item["contradiction_query"]
        assert len(q_item["all_queries"]) <= 6
