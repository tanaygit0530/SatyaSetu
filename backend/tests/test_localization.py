import json
from pathlib import Path
import pytest

from app.schemas.core import ClaimVerificationResult, VerificationResult
from app.schemas.enums import ConfidenceLevel, Verdict
from app.schemas.evidence import LockedEvidenceItem
from app.services.explanation_generator import explanation_generator_service
from app.services.localization import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    LocalizationService,
    localization_service,
)
from app.services.query_generator import evidence_query_generator_service
from app.services.verification_orchestrator import verification_orchestrator
from app.services.whatsapp import whatsapp_webhook_service


def test_locale_files_exist_and_are_valid_json():
    """Verifies that app/locales/en.json, hi.json, and mr.json exist and are well-formed JSON."""
    locales_dir = Path(__file__).resolve().parent.parent / "app" / "locales"
    assert locales_dir.exists(), "app/locales directory must exist"

    for lang in ["en", "hi", "mr"]:
        file_path = locales_dir / f"{lang}.json"
        assert file_path.exists(), f"app/locales/{lang}.json must exist"

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "labels" in data
        assert "verdicts" in data
        assert "explanations" in data
        assert "messages" in data

        # Verify all 5 canonical verdicts have explanation strings
        for verdict in ["FALSE", "VERIFIED", "OUTDATED", "PARTLY_SUPPORTED", "CANNOT_BE_CONFIRMED"]:
            assert verdict in data["explanations"], f"Missing explanation for {verdict} in {lang}.json"
            assert len(data["explanations"][verdict]) > 0


def test_verdict_headers_remain_language_neutral():
    """
    Verifies that the verdict itself remains language-neutral across all languages:
    🔴 FALSE, 🟢 VERIFIED, 🟠 OUTDATED, 🟡 PARTLY SUPPORTED, ⚪ CANNOT BE CONFIRMED.
    """
    for lang in ["en", "hi", "mr"]:
        assert localization_service.get_verdict_header(Verdict.FALSE, lang) == "🔴 FALSE"
        assert localization_service.get_verdict_header(Verdict.VERIFIED, lang) == "🟢 VERIFIED"
        assert localization_service.get_verdict_header(Verdict.OUTDATED, lang) == "🟠 OUTDATED"
        assert localization_service.get_verdict_header(Verdict.PARTLY_SUPPORTED, lang) == "🟡 PARTLY SUPPORTED"
        assert localization_service.get_verdict_header(Verdict.CANNOT_BE_CONFIRMED, lang) == "⚪ CANNOT BE CONFIRMED"


def test_localized_explanations_exact_spec_match():
    """
    Verifies exact spec examples:
    Hindi:
    🔴 FALSE
    यह दावा सही नहीं है। हमें इसे समर्थन देने वाला कोई विश्वसनीय आधिकारिक प्रमाण नहीं मिला।

    English:
    🔴 FALSE
    This claim is not supported by reliable evidence.
    """
    # Hindi explanation
    hi_false_expl = localization_service.get_explanation(Verdict.FALSE, "hi")
    assert hi_false_expl == "यह दावा सही नहीं है। हमें इसे समर्थन देने वाला कोई विश्वसनीय आधिकारिक प्रमाण नहीं मिला।"

    # English explanation
    en_false_expl = localization_service.get_explanation(Verdict.FALSE, "en")
    assert "This claim is not supported by reliable evidence." in en_false_expl

    # Marathi explanation
    mr_false_expl = localization_service.get_explanation(Verdict.FALSE, "mr")
    assert "हा दावा योग्य नाही" in mr_false_expl


def test_explanation_generator_service_supports_user_language():
    """Verifies that ExplanationGeneratorService outputs in the user's requested language."""
    # Test Hindi explanation generation
    hi_output = explanation_generator_service.generate_explanation(
        claim="कल से सभी 500 के नोट बंद हो रहे हैं।",
        verdict=Verdict.FALSE,
        validated_evidence=[],
        language="hi",
    )
    assert hi_output.explanation == "यह दावा सही नहीं है। हमें इसे समर्थन देने वाला कोई विश्वसनीय आधिकारिक प्रमाण नहीं मिला।"

    # Test Marathi explanation generation
    mr_output = explanation_generator_service.generate_explanation(
        claim="उद्यापासून ५०० रुपयांच्या नोटा बंद होणार आहेत.",
        verdict=Verdict.FALSE,
        validated_evidence=[],
        language="mr",
    )
    assert "हा दावा योग्य नाही" in mr_output.explanation

    # Test English explanation generation
    en_output = explanation_generator_service.generate_explanation(
        claim="500 rupee notes will be banned tomorrow.",
        verdict=Verdict.FALSE,
        validated_evidence=[],
        language="en",
    )
    assert "This claim is not supported by reliable evidence." in en_output.explanation


def test_keep_claim_in_original_language_hindi():
    """
    Verifies that claims in vernacular languages (Hindi/Marathi) are preserved in
    their original text and not replaced with translated English text in citizen output.
    """
    hindi_claim_text = "UPI कल से पूरे देश में बंद हो रहा है।"
    mock_res = VerificationResult(
        check_id="chk_hi_01",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_hi_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="यह दावा सही नहीं है। हमें इसे समर्थन देने वाला कोई विश्वसनीय आधिकारिक प्रमाण नहीं मिला।",
                evidence=[],
                normalized_claim=hindi_claim_text,
                language="hi",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    formatted = whatsapp_webhook_service.format_whatsapp_response(mock_res, "chk_hi_01", language="hi")

    # 1. Verdict is language-neutral
    assert "🔴 FALSE" in formatted.formatted_body

    # 2. Claim is kept in original Hindi language
    assert f'"{hindi_claim_text}"' in formatted.formatted_body

    # 3. Explanation is in user's Hindi language
    assert "यह दावा सही नहीं है। हमें इसे समर्थन देने वाला कोई विश्वसनीय आधिकारिक प्रमाण नहीं मिला।" in formatted.formatted_body


def test_keep_claim_in_original_language_marathi():
    """Verifies that Marathi claims are preserved in original Marathi script."""
    marathi_claim_text = "उद्यापासून सर्व UPI व्यवहार पूर्णपणे बंद होणार आहेत."
    mock_res = VerificationResult(
        check_id="chk_mr_01",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_mr_01",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="हा दावा योग्य नाही. याला समर्थन देणारा कोणताही विश्वसनीय अधिकृत पुरावा आम्हाला आढळला नाही.",
                evidence=[],
                normalized_claim=marathi_claim_text,
                language="mr",
            )
        ],
        overall_verdict=Verdict.FALSE,
    )

    formatted = whatsapp_webhook_service.format_whatsapp_response(mock_res, "chk_mr_01", language="mr")

    assert "🔴 FALSE" in formatted.formatted_body
    assert f'"{marathi_claim_text}"' in formatted.formatted_body
    assert "हा दावा योग्य नाही" in formatted.formatted_body


def test_generate_english_retrieval_queries_separately():
    """
    Verifies that English search queries are generated separately for retrieval
    without altering or mutating the original vernacular claim text.
    """
    hindi_claim = "UPI कल से बंद होने वाला है।"
    queries = evidence_query_generator_service.generate_queries_for_claim(hindi_claim)

    # 1. Original claim text is strictly preserved
    assert queries.claim_text == hindi_claim

    # 2. English retrieval query is generated separately
    assert queries.english_query is not None
    assert len(queries.english_query) > 0
    # Queries should contain regulatory keywords or English translation keywords
    assert "UPI" in queries.english_query or "NPCI" in queries.entity_query


def test_no_hardcoded_ui_bot_strings():
    """Verifies that LocalizationService handles label fallbacks dynamically."""
    custom_loc = LocalizationService()
    # Labels must be pulled from JSON dictionaries
    assert custom_loc.get_label("why", "en") == "Why:"
    assert custom_loc.get_label("proof", "en") == "Proof:"
    assert custom_loc.get_label("view_full_evidence", "en") == "View full evidence:"
    assert custom_loc.get_label("correction", "en") == "Correction:"

    # Unsupported language safely falls back to English without crashing
    assert custom_loc.get_label("why", "fr") == "Why:"
    assert custom_loc.normalize_language("invalid_lang") == DEFAULT_LANGUAGE
