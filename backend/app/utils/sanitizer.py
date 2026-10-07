import re
import unicodedata
from app.core.exceptions import InvalidInputException, PromptInjectionDetectedException

# Signatures for adversarial prompt injection / jailbreak attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+(an?\s+)?unfiltered",
    r"developer\s+mode\s+enabled",
    r"output\s+(only\s+)?['\"]?VERIFIED['\"]?\s+without\s+proof",
    r"bypass\s+(all\s+)?rules",
    r"system\s*:\s*you\s+must",
    r"jailbreak",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize_input_text(raw_text: str, max_length: int = 5000) -> str:
    """
    Sanitizes citizen forward text:
    1. Normalizes unicode characters
    2. Strips harmful control codes
    3. Checks minimum/maximum bounds
    4. Evaluates prompt injection attack heuristics
    """
    if not raw_text or not raw_text.strip():
        raise InvalidInputException("Submitted content cannot be empty.")

    normalized = unicodedata.normalize("NFKC", raw_text.strip())

    if len(normalized) > max_length:
        raise InvalidInputException(f"Submitted content exceeds maximum limit of {max_length} characters.")

    # Check for adversarial injection signatures
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(normalized)
        if match:
            raise PromptInjectionDetectedException(detected_pattern=match.group(0))

    return normalized
