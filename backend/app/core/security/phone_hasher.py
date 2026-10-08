import hashlib
import hmac
import re
from typing import Optional

from app.core.config import settings


class PhoneHasher:
    """
    Cryptographic phone number protection:
    - Normalizes phone numbers to standard E.164 representation
    - Hashes phone numbers using HMAC-SHA256 with a secret salt
    - Ensures raw phone numbers are NEVER persisted to database or memory stores
    - Guarantees deterministic hashing for lookups and rate limiting
    """

    def __init__(self, salt: Optional[str] = None):
        self.salt = salt or settings.SECURITY_PHONE_SALT

    def normalize(self, phone: str) -> str:
        """
        Normalizes a phone number to standard E.164 representation:
        - Strips 'whatsapp:' prefix
        - Removes all spaces, dashes, dots, and parentheses
        - Adds Indian '+91' country code if missing for 10-digit Indian numbers
        """
        if not phone:
            return ""

        clean = phone.strip()
        if clean.lower().startswith("whatsapp:"):
            clean = clean[9:].strip()

        # Remove formatting symbols except leading +
        has_plus = clean.startswith("+")
        digits_only = re.sub(r"\D", "", clean)

        if not digits_only:
            return ""

        if has_plus:
            return f"+{digits_only}"

        # Indian phone normalization heuristics
        if len(digits_only) == 10 and digits_only[0] in "6789":
            return f"+91{digits_only}"
        if len(digits_only) == 11 and digits_only.startswith("0") and digits_only[1] in "6789":
            return f"+91{digits_only[1:]}"
        if len(digits_only) == 12 and digits_only.startswith("91"):
            return f"+{digits_only}"

        return f"+{digits_only}"

    def hash_phone(self, phone: str, salt: Optional[str] = None) -> str:
        """
        Computes deterministic HMAC-SHA256 fingerprint of the normalized phone number.
        Returns a 64-character hexadecimal digest.
        """
        normalized = self.normalize(phone)
        if not normalized:
            return ""

        active_salt = (salt or self.salt).encode("utf-8")
        return hmac.new(
            active_salt,
            normalized.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def mask_phone_for_display(self, phone: str) -> str:
        """
        Returns a partially masked representation safe for display (e.g. +91 ****** 43210).
        """
        normalized = self.normalize(phone)
        if len(normalized) < 8:
            return "[PROTECTED_NUMBER]"

        prefix = normalized[:3]
        suffix = normalized[-4:]
        masked_length = len(normalized) - 7
        return f"{prefix}{'*' * max(masked_length, 4)}{suffix}"


phone_hasher = PhoneHasher()


def hash_phone_number(phone: str, salt: Optional[str] = None) -> str:
    """Convenience functional wrapper for phone hashing."""
    return phone_hasher.hash_phone(phone, salt)
