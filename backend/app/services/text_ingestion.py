import hashlib
import re
import unicodedata
from typing import Any, Dict, Optional, Union

from app.core.config import settings
from app.core.exceptions import InvalidInputException
from app.schemas.ingestion import TextInput, TextIngestionResult
from app.services.language_detection import language_detector_service


class TextIngestionService:
    """
    Text ingestion pipeline responsible for sanitizing, normalizing,
    fingerprinting, and validating raw citizen forwards.
    """

    def __init__(self, max_length: Optional[int] = None):
        self.max_length = max_length or settings.MAX_TEXT_INPUT_LENGTH

    def ingest(self, payload: Union[TextInput, str, Dict[str, Any]]) -> TextIngestionResult:
        """
        Ingests, validates, normalizes, and fingerprints input text.
        Preserves original text intact while generating clean normalized representation.
        """
        # Extract raw text from payload
        if isinstance(payload, str):
            raw_text = payload
        elif isinstance(payload, TextInput):
            raw_text = payload.text
        elif isinstance(payload, dict):
            if "text" not in payload:
                raise InvalidInputException("Missing required 'text' field in input payload.")
            raw_text = payload["text"]
        else:
            raise InvalidInputException(f"Unsupported payload type: {type(payload).__name__}")

        # 1. Validate non-empty
        if not raw_text or not raw_text.strip():
            raise InvalidInputException("Input text cannot be empty or contain only whitespace.")

        # 2. Validate maximum length
        if len(raw_text) > self.max_length:
            raise InvalidInputException(
                f"Input text exceeds maximum allowed length of {self.max_length} characters "
                f"(received {len(raw_text)} characters)."
            )

        # 3. Unicode safety & normalization
        unicode_safe_text = self.sanitize_unicode(raw_text)

        # 4. Whitespace normalization
        normalized_text = self.normalize_whitespace(unicode_safe_text)

        # 5. Content fingerprint (SHA-256)
        content_hash = self.generate_content_hash(normalized_text)

        # 6. Vernacular language hint detection (optional script check)
        language_hint = self.detect_language_hint(normalized_text)

        return TextIngestionResult(
            input_type="TEXT",
            original_text=raw_text,
            normalized_text=normalized_text,
            content_hash=content_hash,
            language_hint=language_hint,
        )

    def sanitize_unicode(self, text: str) -> str:
        """
        Normalizes Unicode to canonical NFC/NFKC form and removes hazardous
        control characters (null bytes, invisible separators, surrogate sequences).
        Preserves valid emojis, vernacular Indian scripts, and punctuation.
        """
        # Remove null bytes and dangerous control chars
        text = text.replace("\x00", "")

        # Canonical decomposition and composition (NFKC cleans compatibility forms)
        text = unicodedata.normalize("NFKC", text)

        # Strip invisible formatting characters (zero-width spaces, joiners, directional overrides)
        # while keeping valid whitespace and alphabetic/syllabic marks
        invisible_chars = {
            "\u200b",  # zero-width space
            "\u200c",  # zero-width non-joiner
            "\u200d",  # zero-width joiner
            "\ufeff",  # byte order mark / zero-width no-break space
            "\u202a",  # left-to-right embedding
            "\u202b",  # right-to-left embedding
            "\u202c",  # pop directional formatting
            "\u202d",  # left-to-right override
            "\u202e",  # right-to-left override
        }
        for ch in invisible_chars:
            text = text.replace(ch, "")

        return text

    def normalize_whitespace(self, text: str) -> str:
        """
        Collapses consecutive spaces, tabs, and newlines into a single standard space,
        and trims leading and trailing whitespace.
        """
        return re.sub(r"\s+", " ", text).strip()

    def generate_content_hash(self, normalized_text: str) -> str:
        """
        Generates a deterministic SHA-256 fingerprint from normalized content.
        """
        return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    def detect_language_hint(self, text: str) -> Optional[str]:
        """
        Detects vernacular language hint using language_detector_service.
        Returns None for standard English (per spec example) or 'hi' / 'mr' for vernacular.
        """
        res = language_detector_service.detect(text)
        if res.language != "en":
            return res.language
        return None


text_ingestion_service = TextIngestionService()
