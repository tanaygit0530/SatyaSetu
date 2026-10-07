import pytest
import httpx
from app.main import app
from app.schemas.claim import AtomicClaim, AtomicClaimsOutput
from app.services.claim_extractor import ClaimExtractorService, claim_extractor_service


# ==============================================================================
# 1. Specification Example: Compound Claim Decomposition
# ==============================================================================

def test_specification_example_compound_upi_claim():
    """
    Verifies the user's primary specification example:
    Input: "UPI has been banned in India from tomorrow and all users will have to pay a 5% fee."
    System must NOT treat this as one giant claim.
    Extracts:
      Claim 1: "UPI has been banned in India from tomorrow."
      Claim 2: "All UPI users will have to pay a 5% fee."
    """
    message = "UPI has been banned in India from tomorrow and all users will have to pay a 5% fee."
    output = claim_extractor_service.extract_claims(message)

    # Must extract exactly 2 atomic claims
    assert len(output.claims) == 2, f"Expected 2 claims, got {len(output.claims)}"

    # Claim 1 assertions
    c1 = output.claims[0]
    assert c1.claim_id == "clm_001"
    assert "UPI has been banned in India from tomorrow" in c1.original_text
    assert "UPI" in c1.entities
    assert "India" in c1.locations
    assert "tomorrow" in c1.dates
    assert c1.temporal_expression == "from tomorrow"
    assert c1.claim_type == "policy"
    assert c1.check_worthiness is True

    # Claim 2 assertions
    c2 = output.claims[1]
    assert c2.claim_id == "clm_002"
    assert "pay a 5% fee" in c2.original_text
    assert "5%" in c2.numbers
    assert c2.claim_type in ("financial", "policy")
    assert c2.check_worthiness is True


# ==============================================================================
# 2. Compound Claims: Public Administration, Railways, Education
# ==============================================================================

def test_railway_suspension_and_refund_compound_claim():
    """Splits nationwide railway suspension from ticket refund proposition."""
    message = "Indian Railways has ordered complete suspension of passenger train operations nationwide starting tomorrow and tickets will be refunded automatically."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 2
    assert "suspension of passenger train operations" in output.claims[0].original_text
    assert "Indian Railways" in output.claims[0].entities
    assert "tomorrow" in output.claims[0].dates
    assert "tickets will be refunded" in output.claims[1].original_text
    assert output.claims[1].check_worthiness is True


def test_education_merit_scholarship_and_portal_compound_claim():
    """Splits scholarship notification from registration deadline claim."""
    message = "Ministry of Education launched the PMSSY merit scholarship for 2026-27 and citizens should register on domain pmssy-gov.in before 15th October."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 2
    assert "Ministry of Education" in output.claims[0].entities
    assert any("2026" in d for d in output.claims[0].dates)
    assert "15th October" in output.claims[1].dates
    assert output.claims[0].check_worthiness is True
    assert output.claims[1].check_worthiness is True


# ==============================================================================
# 3. Inseparable Factual Claims (Do not split unnecessarily)
# ==============================================================================

def test_inseparable_fact_joint_ministry_meeting():
    """Ensures conjunction joining subjects does NOT get split into two fragments."""
    message = "The Ministry of Education and Ministry of Finance held a joint meeting."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert "Ministry of Education" in output.claims[0].entities
    assert output.claims[0].check_worthiness is True


def test_inseparable_fact_repo_rate_hike():
    """Ensures single unified economic announcement is kept as one claim."""
    message = "The Reserve Bank of India has increased the repo rate by 25 basis points."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert "RBI" in output.claims[0].entities
    assert 25 in output.claims[0].numbers
    assert output.claims[0].check_worthiness is True


def test_inseparable_fact_gdp_growth_statistic():
    """Ensures complex statistic remains a single atomic proposition."""
    message = "India's GDP grew by 7.8% in the first quarter of 2025-26."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert "7.8%" in output.claims[0].numbers
    assert "India" in output.claims[0].locations
    assert output.claims[0].check_worthiness is True


# ==============================================================================
# 4. Opinion Statements (Marked non-verifiable: check_worthiness = False)
# ==============================================================================

def test_opinion_taxation_law_marked_non_verifiable():
    """Identifies subjective opinions and sets check_worthiness=False."""
    message = "In my opinion, the new taxation law is the worst decision ever made."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "opinion"
    assert output.claims[0].check_worthiness is False


def test_opinion_subjective_criticism():
    """Identifies personal evaluation phrases as opinions."""
    message = "I think the traffic police are completely useless and unfair."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "opinion"
    assert output.claims[0].check_worthiness is False


# ==============================================================================
# 5. Predictions (Not treated as facts: check_worthiness = False)
# ==============================================================================

def test_prediction_astrology_gold_crash():
    """Identifies astrology / speculative forecast as prediction."""
    message = "According to astrologer, gold rates will crash to zero by December 2026."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "prediction"
    assert output.claims[0].check_worthiness is False


def test_prediction_speculative_currency_replacement():
    """Identifies futuristic speculation as non-checkworthy prediction."""
    message = "Crypto will replace the US dollar in 2030."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "prediction"
    assert output.claims[0].check_worthiness is False


# ==============================================================================
# 6. Questions (Not automatically treated as claims)
# ==============================================================================

def test_question_bank_holiday_inquiry():
    """Identifies questions and marks check_worthiness=False."""
    message = "Is it true that tomorrow all banks in India are closed?"
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "question"
    assert output.claims[0].check_worthiness is False


def test_question_500_note_ban():
    """Ensures rhetorical / inquiry questions are classified as question."""
    message = "Did RBI announce a complete ban on ₹500 notes?"
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "question"
    assert output.claims[0].check_worthiness is False


# ==============================================================================
# 7. Vernacular Languages: Hindi, Marathi, Hinglish
# ==============================================================================

def test_hindi_devanagari_compound_claim():
    """Decomposes compound Hindi assertion into two atomic claims."""
    message = "शिक्षा मंत्रालय ने 2026-27 के लिए छात्रवृत्ति योजना शुरू की है और हर कॉलेज छात्र को ₹50,000 DBT मिलेगा।"
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 2
    assert output.claims[0].language == "hi"
    assert output.claims[1].language == "hi"
    assert 50000 in output.claims[1].numbers
    assert output.claims[0].check_worthiness is True
    assert output.claims[1].check_worthiness is True


def test_hindi_opinion_marked_non_verifiable():
    """Identifies Hindi opinion marker 'मुझे लगता है' as non-verifiable."""
    message = "मुझे लगता है कि सरकार का यह फैसला पूरी तरह से गलत है।"
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "opinion"
    assert output.claims[0].check_worthiness is False


def test_marathi_devanagari_compound_claim():
    """Decomposes compound Marathi assertion into two atomic claims."""
    message = "महाराष्ट्र शासनाने नवीन परिपत्रक जारी केले आहे आणि सर्व शाळा 15 ऑक्टोबरपर्यंत बंद राहतील."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 2
    assert output.claims[0].language == "mr"
    assert output.claims[1].language == "mr"
    assert "Maharashtra" in output.claims[0].locations
    assert output.claims[0].check_worthiness is True
    assert output.claims[1].check_worthiness is True


def test_hinglish_compound_claim():
    """Decomposes compound Hinglish forward into two atomic claims."""
    message = "Sarkar ne kal se UPI band kar diya hai aur sabhi users ko 5% fee deni hogi"
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 2
    assert output.claims[0].language == "hi"
    assert "UPI" in output.claims[0].entities
    assert "5%" in output.claims[1].numbers
    assert output.claims[0].check_worthiness is True
    assert output.claims[1].check_worthiness is True


# ==============================================================================
# 8. Domain Specific: Public Health, Cybersecurity, Traffic Law
# ==============================================================================

def test_health_drinking_water_contamination():
    """Extracts public health contamination assertion."""
    message = "Drinking water pipeline in Ward 14 has been chemically contaminated."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "health"
    assert "Ward 14" in output.claims[0].locations
    assert output.claims[0].check_worthiness is True


def test_cybersecurity_phishing_recharge_link():
    """Extracts cybersecurity / scam recharge claim."""
    message = "Citizens can claim free ₹1000 mobile recharge on domain free-recharge.in."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert 1000 in output.claims[0].numbers
    assert output.claims[0].check_worthiness is True


def test_traffic_fine_penalty_claim():
    """Extracts traffic enforcement fine with date and fine amount."""
    message = "Traffic police announced ₹10,000 fine for driving without HSRP plates from Monday."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 1
    assert 10000 in output.claims[0].numbers
    assert "Traffic Police" in output.claims[0].entities
    assert "monday" in output.claims[0].dates
    assert output.claims[0].check_worthiness is True


# ==============================================================================
# 9. Mixed Opinion + Fact & Multi-Sentence Forwards
# ==============================================================================

def test_mixed_opinion_and_factual_policy():
    """Separates subjective opinion clause from genuine factual announcement."""
    message = "I believe the government is terrible, but all tickets will be refunded by Indian Railways."
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 2
    # Claim 1 is an opinion
    assert output.claims[0].claim_type == "opinion"
    assert output.claims[0].check_worthiness is False
    # Claim 2 is a factual announcement
    assert output.claims[1].check_worthiness is True
    assert "tickets will be refunded" in output.claims[1].original_text


def test_multi_sentence_forward_three_claims():
    """Extracts three sequential atomic claims from a multi-sentence message."""
    message = (
        "Indian Railways suspended all train services. "
        "The Ministry of Health issued a red alert in Delhi. "
        "Citizens should remain indoors until Monday."
    )
    output = claim_extractor_service.extract_claims(message)

    assert len(output.claims) == 3
    assert output.claims[0].claim_id == "clm_001"
    assert output.claims[1].claim_id == "clm_002"
    assert output.claims[2].claim_id == "clm_003"
    assert "Delhi" in output.claims[1].locations
    assert "monday" in output.claims[2].dates


# ==============================================================================
# 10. API Endpoint Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_api_claims_extract_endpoint():
    """Tests POST /api/v1/claims/extract endpoint returns valid structured JSON."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "text": "UPI has been banned in India from tomorrow and all users will have to pay a 5% fee."
        }
        response = await client.post("/api/v1/claims/extract", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "claims" in data
        assert len(data["claims"]) == 2
        assert data["claims"][0]["claim_id"] == "clm_001"
        assert data["claims"][0]["entities"] == ["UPI"]
        assert data["claims"][0]["locations"] == ["India"]
        assert data["claims"][0]["temporal_expression"] == "from tomorrow"
        assert data["claims"][0]["check_worthiness"] is True

        assert data["claims"][1]["claim_id"] == "clm_002"
        assert "5%" in data["claims"][1]["numbers"]
        assert data["claims"][1]["check_worthiness"] is True
