import pytest
import httpx
from app.main import app
from app.schemas.enums import TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem, EvidenceInterpretation
from app.services.language_detection import (
    LanguageDetectorService,
    language_detector_service,
)
from app.services.rule_engine import DeterministicRuleEngine
from app.schemas.claim import ExtractedClaim
from app.schemas.enums import Language


# ==============================================================================
# 1. Primary Language Detection Tests (English, Hindi, Marathi)
# ==============================================================================

def test_detect_english_text():
    """Validates English text returns language='en', script='Latin', is_mixed=False."""
    text = "The Ministry of Railways has suspended all passenger train operations nationwide starting tomorrow."
    result = language_detector_service.detect(text)
    serialized = result.to_dict()

    assert serialized == {
        "language": "en",
        "script": "Latin",
        "is_mixed": False,
    }


def test_detect_hindi_devanagari_text():
    """Validates pure Hindi in Devanagari script returns language='hi', script='Devanagari', is_mixed=False."""
    text = "सरकार ने कल से सभी यूपीआई लेनदेन पर नया सेवा शुल्क लगाने का फैसला किया है।"
    result = language_detector_service.detect(text)
    serialized = result.to_dict()

    assert serialized == {
        "language": "hi",
        "script": "Devanagari",
        "is_mixed": False,
    }


def test_detect_marathi_devanagari_text():
    """
    Validates Marathi text in Devanagari script (featuring Marathi markers and 'ळ')
    returns language='mr', script='Devanagari', is_mixed=False.
    """
    text = "महाराष्ट्र शासनाने सर्व विद्यार्थ्यांसाठी नवीन शिष्यवृत्ती योजना जाहीर केली असून ₹50,000 अनुदान थेट मिळणार आहे."
    result = language_detector_service.detect(text)
    serialized = result.to_dict()

    assert serialized == {
        "language": "mr",
        "script": "Devanagari",
        "is_mixed": False,
    }


# ==============================================================================
# 2. Hinglish Detection Tests (Hindi in Latin script)
# ==============================================================================

def test_detect_hinglish_text_specification_example():
    """
    Validates Hinglish input returns:
    {
      "language": "hi",
      "script": "Latin",
      "is_hinglish": true
    }
    """
    text = "Sarkar ne kal se UPI band kar diya hai"
    result = language_detector_service.detect(text)
    serialized = result.to_dict()

    assert serialized == {
        "language": "hi",
        "script": "Latin",
        "is_hinglish": True,
    }


def test_detect_hinglish_forward_message():
    """Validates typical viral WhatsApp forward written in Hinglish."""
    text = "Bhai ye message sabhi dosto ko forward karo kal se free recharge nahi milega"
    result = language_detector_service.detect(text)
    serialized = result.to_dict()

    assert serialized["language"] == "hi"
    assert serialized["script"] == "Latin"
    assert serialized["is_hinglish"] is True


# ==============================================================================
# 3. Code-Mixing / Mixed Language Tests
# ==============================================================================

def test_detect_mixed_english_and_hindi_devanagari():
    """Validates mixed English + Hindi in Devanagari script sets is_mixed=True."""
    text = "Breaking News: Government ने UPI services ban कर दिया है starting from tomorrow!"
    result = language_detector_service.detect(text)
    serialized = result.to_dict()

    assert serialized["language"] == "hi"
    assert serialized["is_mixed"] is True


def test_detect_mixed_english_and_marathi():
    """Validates mixed English + Marathi sets is_mixed=True and language='mr'."""
    text = "Official Alert: Maharashtra Government ने new circular issue केले आहे for all colleges."
    result = language_detector_service.detect(text)
    serialized = result.to_dict()

    assert serialized["language"] == "mr"
    assert serialized["is_mixed"] is True


# ==============================================================================
# 4. Claim Preservation & Separate Search Query Representation
# ==============================================================================

def test_preserves_original_claim_without_translating():
    """
    Critical requirement:
    - Do not translate the original claim.
    - Preserve original claim text intact.
    - Create an English search-query representation separately.
    """
    original_vernacular = "शिक्षा मंत्रालय ने 2026-27 के लिए छात्रवृत्ति योजना अधिसूचित की है।"
    repr_result = language_detector_service.create_claim_representation(original_vernacular)

    # 1. Original claim text MUST NOT be translated or mutated
    assert repr_result.original_claim == original_vernacular

    # 2. Language metadata must identify vernacular
    assert repr_result.language_info.language == "hi"
    assert repr_result.language_info.script == "Devanagari"

    # 3. English search query representation is generated separately
    assert repr_result.english_search_query != original_vernacular
    assert "scholarship" in repr_result.english_search_query.lower()
    assert "2026" in repr_result.english_search_query


def test_hinglish_search_query_generation_separate_from_claim():
    """Ensures Hinglish original text is preserved while English search query is created."""
    original_hinglish = "Sarkar ne kal se UPI band kar diya hai"
    repr_result = language_detector_service.create_claim_representation(original_hinglish)

    # Original text is preserved exactly
    assert repr_result.original_claim == original_hinglish
    assert repr_result.language_info.is_hinglish is True

    # English search query contains official retrieval keywords
    query = repr_result.english_search_query
    assert "UPI" in query
    assert "Government" in query or "banned" in query.lower()


# ==============================================================================
# 5. Language-Neutral Facts Extraction (Numbers, Dates, Entities, Relationships)
# ==============================================================================

def test_extract_language_neutral_facts_scholarship_claim():
    """
    Validates factual extraction of numbers, dates, entities, relationships,
    and temporal status regardless of language prose.
    """
    text = "हर कॉलेज छात्र को बिना किसी परीक्षा के ₹50,000 DBT मिलेगा 2026-27 सत्र के लिए।"
    facts = language_detector_service.extract_language_neutral_facts(text)

    # 1. Numbers: ₹50,000
    assert 50000 in facts.numbers

    # 2. Dates: 2026-27
    assert any("2026" in d for d in facts.dates)

    # 3. Entities: DBT
    assert "DBT" in facts.entities

    # 4. Relationships: SANCTIONED_GRANT
    assert "SANCTIONED_GRANT" in facts.relationships

    # 5. Temporal Status: CURRENT
    assert facts.temporal_status == TemporalStatus.CURRENT


def test_extract_language_neutral_facts_outdated_claim():
    """Detects historical temporal status when older dates (e.g. 2020) are present."""
    text = "Complete nationwide lockdown and train suspension ordered from 24th March 2020."
    facts = language_detector_service.extract_language_neutral_facts(text)

    assert 2020 in [int(d) for d in facts.dates if d.isdigit()] or any("2020" in d for d in facts.dates)
    assert facts.temporal_status == TemporalStatus.OUTDATED


# ==============================================================================
# 6. Verdict Logic Operates on Language-Neutral Facts, NOT Translated Prose
# ==============================================================================

def test_verdict_logic_operates_identically_on_neutral_facts_across_languages():
    """
    Demonstrates the architectural principle:
    The deterministic rule engine evaluates language-neutral facts (financial amounts,
    temporal mismatch flags, entity records) producing identical verdicts
    regardless of whether the input is Hindi Devanagari or Hinglish or English prose.
    """
    # Fact 1: Claimed amount is ₹50,000, but official gazette specifies ₹10,000
    interpretation = EvidenceInterpretation(
        supports_claim=False,
        refutes_claim=True,
        claimed_amount=50000.0,
        actual_amount=10000.0,
        discrepancy_explanation="Gazette notification approves ₹10,000, refuting ₹50,000.",
    )

    evidence_item = EvidenceItem(
        id="CIT-01",
        publisher="Ministry of Education",
        domain="education.gov.in",
        title="Official Notification",
        publish_date="2026-06-01",
        tier="TIER_1_PRIMARY",
        url="https://education.gov.in/notice",
        exact_quote="Sanctioned amount is ₹10,000 per student.",
    )

    # Case A: Hindi Devanagari Claim
    claim_hi = ExtractedClaim(
        claim_number=1,
        claim_text="हर छात्र को ₹50,000 मिलेगा।",
        language=Language.HI,
    )
    result_hi = DeterministicRuleEngine.evaluate_claim(claim_hi, [evidence_item], interpretation)

    # Case B: Hinglish Claim
    claim_hinglish = ExtractedClaim(
        claim_number=1,
        claim_text="Sabhi students ko 50000 rupaye milenge.",
        language=Language.HI,
    )
    result_hinglish = DeterministicRuleEngine.evaluate_claim(claim_hinglish, [evidence_item], interpretation)

    # Case C: English Claim
    claim_en = ExtractedClaim(
        claim_number=1,
        claim_text="Every student will receive ₹50,000.",
        language=Language.EN,
    )
    result_en = DeterministicRuleEngine.evaluate_claim(claim_en, [evidence_item], interpretation)

    # All three produce the identical FALSE verdict driven by the numerical discrepancy rule
    assert result_hi.verdict == Verdict.FALSE
    assert result_hinglish.verdict == Verdict.FALSE
    assert result_en.verdict == Verdict.FALSE
    assert result_hi.rule_matched == "RULE-FINANCIAL-DISCREPANCY"
    assert result_hinglish.rule_matched == "RULE-FINANCIAL-DISCREPANCY"
    assert result_en.rule_matched == "RULE-FINANCIAL-DISCREPANCY"


# ==============================================================================
# 7. FastAPI Endpoint Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_api_detect_language_endpoint_hindi():
    """Tests POST /api/v1/language/detect returns specification JSON format."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/language/detect",
            json={"text": "सरकार ने कल से सभी यूपीआई लेनदेन पर नया आदेश दिया है।"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "hi"
        assert data["script"] == "Devanagari"
        assert data["is_mixed"] is False


@pytest.mark.asyncio
async def test_api_detect_language_endpoint_hinglish():
    """Tests POST /api/v1/language/detect returns specification Hinglish JSON format."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/language/detect",
            json={"text": "Sarkar ne kal se UPI band kar diya hai"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "hi"
        assert data["script"] == "Latin"
        assert data.get("is_hinglish") is True


@pytest.mark.asyncio
async def test_api_represent_claim_endpoint():
    """Tests POST /api/v1/language/represent-claim preserves claim and extracts facts."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        claim_input = "Maharashtra Government ने Ward 14 साठी ₹50,000 निधी मंजूर केला आहे."
        response = await client.post(
            "/api/v1/language/represent-claim",
            json={"text": claim_input},
        )
        assert response.status_code == 200
        data = response.json()

        # Original claim preserved verbatim
        assert data["original_claim"] == claim_input

        # Language identified
        assert data["language_info"]["language"] == "mr"

        # Search query generated separately
        assert "english_search_query" in data
        assert len(data["english_search_query"]) > 0

        # Structured neutral facts extracted
        assert 50000 in data["neutral_facts"]["numbers"]
