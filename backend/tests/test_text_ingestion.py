import hashlib
import pytest
import httpx
from app.main import app
from app.core.exceptions import InvalidInputException
from app.schemas.ingestion import TextInput
from app.services.text_ingestion import TextIngestionService, text_ingestion_service


# ==============================================================================
# 1. Example and Core Ingestion Tests
# ==============================================================================

def test_ingestion_example_from_specification():
    """
    Validates exact example from specification:
    Input: "BREAKING!!! Government has banned UPI from tomorrow!!!"
    Preserves original text, generates normalized text, calculates content hash.
    """
    raw_message = "BREAKING!!! Government has banned UPI from tomorrow!!!"
    result = text_ingestion_service.ingest({"text": raw_message})

    assert result.input_type == "TEXT"
    assert result.original_text == raw_message
    assert result.normalized_text == raw_message
    expected_hash = hashlib.sha256(raw_message.encode("utf-8")).hexdigest()
    assert result.content_hash == expected_hash
    assert result.language_hint is None


def test_preserves_original_text_while_normalizing():
    """
    Ensures messy original text (multiple tabs, newlines, extra spaces) is kept
    completely untouched in original_text, while normalized_text is neatly collapsed.
    """
    messy_text = "  \n\nBREAKING   NEWS:\t\nGovt has   launched   scheme X.   \n\t"
    result = text_ingestion_service.ingest(messy_text)

    # original_text MUST be preserved verbatim
    assert result.original_text == messy_text

    # normalized_text MUST have collapsed whitespace and be trimmed
    assert result.normalized_text == "BREAKING NEWS: Govt has launched scheme X."

    # content_hash is based on the normalized text
    expected_hash = hashlib.sha256(b"BREAKING NEWS: Govt has launched scheme X.").hexdigest()
    assert result.content_hash == expected_hash


# ==============================================================================
# 2. Validation Rule Tests
# ==============================================================================

@pytest.mark.parametrize("empty_input", ["", "   ", "\t\t", "\n\n\r", "   \n\t  "])
def test_non_empty_validation_raises_error(empty_input):
    """Ensures empty or whitespace-only text raises InvalidInputException."""
    with pytest.raises(InvalidInputException) as exc_info:
        text_ingestion_service.ingest(empty_input)
    assert "cannot be empty" in str(exc_info.value)


def test_maximum_length_validation_raises_error():
    """Ensures text exceeding max_length raises InvalidInputException."""
    service_with_small_limit = TextIngestionService(max_length=50)
    oversized_text = "A" * 51

    with pytest.raises(InvalidInputException) as exc_info:
        service_with_small_limit.ingest(oversized_text)
    assert "exceeds maximum allowed length" in str(exc_info.value)


def test_missing_text_key_in_dict_raises_error():
    """Ensures dictionary without 'text' key raises InvalidInputException."""
    with pytest.raises(InvalidInputException) as exc_info:
        text_ingestion_service.ingest({"invalid_key": "some text"})
    assert "Missing required 'text' field" in str(exc_info.value)


# ==============================================================================
# 3. Unicode Safety and Sanitization Tests
# ==============================================================================

def test_unicode_safety_null_bytes_and_invisible_chars():
    """
    Ensures null bytes and invisible zero-width characters are safely removed
    from normalized text while original text preserves raw input.
    """
    raw_with_null_and_zero_width = "Alert:\x00 Govt \u200border\ufeff is issued."
    result = text_ingestion_service.ingest(raw_with_null_and_zero_width)

    assert result.original_text == raw_with_null_and_zero_width
    assert result.normalized_text == "Alert: Govt order is issued."
    assert "\x00" not in result.normalized_text
    assert "\u200b" not in result.normalized_text
    assert "\ufeff" not in result.normalized_text


def test_unicode_safety_vernacular_hindi_marathi():
    """
    Ensures vernacular Indian scripts (Devanagari) are safely handled and preserved.
    """
    hindi_claim = "भारत सरकार ने 2026 में नई छात्रवृत्ति योजना शुरू की है।"
    result = text_ingestion_service.ingest(hindi_claim)

    assert result.original_text == hindi_claim
    assert result.normalized_text == hindi_claim
    assert result.language_hint == "hi"


def test_unicode_safety_compatibility_normalization():
    """
    Ensures full-width characters (e.g. ＵＰＩ) are normalized to standard ASCII (UPI).
    """
    full_width = "Government has banned ＵＰＩ today."
    result = text_ingestion_service.ingest(full_width)

    assert result.normalized_text == "Government has banned UPI today."


# ==============================================================================
# 4. Deterministic Hashing Tests
# ==============================================================================

def test_identical_normalized_text_produces_identical_hash():
    """
    Ensures two different formatted forwards that mean the same thing
    generate identical content_hash values.
    """
    msg1 = "Government has launched Scheme X in 2026."
    msg2 = "  Government   has launched \nScheme X in 2026.  \t"

    res1 = text_ingestion_service.ingest(msg1)
    res2 = text_ingestion_service.ingest(msg2)

    assert res1.content_hash == res2.content_hash
    assert len(res1.content_hash) == 64


# ==============================================================================
# 5. API Route Integration Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_api_text_ingest_endpoint_success():
    """Tests POST /api/v1/ingest/text with valid input."""
    payload = {"text": "BREAKING!!! Government has banned UPI from tomorrow!!!"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest/text", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["input_type"] == "TEXT"
        assert data["original_text"] == payload["text"]
        assert data["normalized_text"] == payload["text"]
        assert len(data["content_hash"]) == 64
        assert data["language_hint"] is None


@pytest.mark.asyncio
async def test_api_text_ingest_endpoint_empty_error():
    """Tests POST /api/v1/ingest/text with whitespace returns 400 Bad Request."""
    payload = {"text": "    "}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest/text", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_INPUT"
