import os
import re
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.logging import logger

KNOWN_SECRET_NAMES = [
    "SECRET_KEY",
    "TWILIO_AUTH_TOKEN",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "SARVAM_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_FACT_CHECK_API_KEY",
    "GOOGLE_VISION_API_KEY",
    "SECURITY_PHONE_SALT",
]

DEFAULT_INSECURE_VALUES = {
    "sachcheck-foundation-secret-key-change-in-production",
    "sachcheck_salt_v1",
    "changeme",
    "secret",
    "default",
}

# Regex to detect leaked API keys and bearer tokens
API_KEY_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),               # OpenAI / Tavily keys
    re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE),              # Google API keys
    re.compile(r"AC[a-f0-9]{32}", re.IGNORECASE),                     # Twilio Account SID
    re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE),                # GitHub tokens
    re.compile(r"(Bearer\s+)[a-zA-Z0-9\._\-]{20,}", re.IGNORECASE),    # Bearer tokens
]


class SecretsValidator:
    """
    Secrets Security Policy:
    1. Secrets must be supplied strictly via environment variables.
    2. Zero hardcoded secrets in source files.
    3. Detects if configured secrets appear in application logs or API responses.
    4. Enforces production checks against default placeholder values.
    """

    def get_configured_secret_values(self) -> Set[str]:
        """Collects non-empty active secret values for redaction."""
        secret_values = set()
        for name in KNOWN_SECRET_NAMES:
            val = getattr(settings, name, None)
            if val and isinstance(val, str) and len(val) >= 6:
                secret_values.add(val)
        return secret_values

    def validate_production_secrets(self) -> Dict[str, Any]:
        """
        Validates that secrets are set and not using default placeholders in production.
        """
        results = {
            "is_secure": True,
            "issues": [],
            "checked_keys": KNOWN_SECRET_NAMES,
        }

        # Check for default insecure keys
        if settings.SECRET_KEY in DEFAULT_INSECURE_VALUES:
            results["issues"].append("SECRET_KEY is using a default insecure fallback.")
            if settings.ENVIRONMENT == "production":
                results["is_secure"] = False

        if settings.SECURITY_PHONE_SALT in DEFAULT_INSECURE_VALUES:
            results["issues"].append("SECURITY_PHONE_SALT is using a default insecure fallback.")
            if settings.ENVIRONMENT == "production":
                results["is_secure"] = False

        return results

    def redact_secrets(self, text: str) -> str:
        """
        Redacts active configuration secrets and API key signatures from text.
        """
        if not text:
            return ""

        clean = text

        # 1. Redact known active secret values
        for val in self.get_configured_secret_values():
            if val in clean:
                clean = clean.replace(val, "[REDACTED_SECRET]")

        # 2. Redact recognized API key patterns
        for pat in API_KEY_PATTERNS:
            clean = pat.sub("[REDACTED_KEY]", clean)

        return clean


secrets_validator = SecretsValidator()
