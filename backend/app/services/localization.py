import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from app.core.logging import logger
from app.schemas.enums import Verdict

SUPPORTED_LANGUAGES = {"en", "hi", "mr"}
DEFAULT_LANGUAGE = "en"


class LocalizationService:
    """
    Centralized localization and translation resource manager.
    Loads and serves localized bot/UI strings from app/locales/*.json.
    Ensures that strings are not hardcoded in business logic and guarantees
    language fallbacks (hi/mr -> en).
    """

    def __init__(self, locales_dir: Optional[Union[str, Path]] = None):
        if locales_dir:
            self.locales_dir = Path(locales_dir)
        else:
            # Default: locate app/locales relative to this file
            base_app = Path(__file__).resolve().parent.parent
            self.locales_dir = base_app / "locales"

        self._locales: Dict[str, Dict[str, Any]] = {}
        self._load_locales()

    def _load_locales(self) -> None:
        """Loads all supported language JSON files into memory."""
        for lang in SUPPORTED_LANGUAGES:
            file_path = self.locales_dir / f"{lang}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self._locales[lang] = json.load(f)
                    logger.debug("Loaded locale file for '%s' from %s", lang, file_path)
                except Exception as e:
                    logger.error("Failed to load locale file %s: %s", file_path, e)
                    self._locales[lang] = {}
            else:
                logger.warning("Locale file not found at %s", file_path)
                self._locales[lang] = {}

    def normalize_language(self, lang: Optional[str]) -> str:
        """Normalizes input language codes to supported ISO codes (en, hi, mr)."""
        if not lang:
            return DEFAULT_LANGUAGE

        clean = lang.lower().strip()
        if clean.startswith("hi") or "hinglish" in clean:
            return "hi"
        elif clean.startswith("mr") or "marathi" in clean:
            return "mr"
        elif clean.startswith("en"):
            return "en"
        return DEFAULT_LANGUAGE

    def get_locale_data(self, lang: Optional[str] = None) -> Dict[str, Any]:
        """Returns the full locale dictionary for the requested language."""
        code = self.normalize_language(lang)
        return self._locales.get(code, self._locales.get(DEFAULT_LANGUAGE, {}))

    def get_label(self, key: str, lang: Optional[str] = None, default: Optional[str] = None) -> str:
        """Retrieves a localized UI/bot label (e.g. why, claim, proof, correction)."""
        code = self.normalize_language(lang)
        labels = self._locales.get(code, {}).get("labels", {})
        val = labels.get(key)
        if val is not None:
            return str(val)

        # Fallback to English
        en_labels = self._locales.get(DEFAULT_LANGUAGE, {}).get("labels", {})
        return str(en_labels.get(key, default if default is not None else key))

    def get_verdict_header(self, verdict: Union[Verdict, str], lang: Optional[str] = None) -> str:
        """
        Retrieves the canonical emoji verdict header.
        Per specification, the verdict itself remains language-neutral:
        🟢 VERIFIED, 🔴 FALSE, 🟠 OUTDATED, 🟡 PARTLY SUPPORTED, ⚪ CANNOT BE CONFIRMED
        """
        code = self.normalize_language(lang)
        verdict_key = verdict.value if isinstance(verdict, Verdict) else str(verdict).upper()
        verdict_headers = self._locales.get(code, {}).get("verdicts", {})
        val = verdict_headers.get(verdict_key)
        if val:
            return str(val)

        en_headers = self._locales.get(DEFAULT_LANGUAGE, {}).get("verdicts", {})
        return str(en_headers.get(verdict_key, f"⚪ {verdict_key}"))

    def get_explanation(self, verdict: Union[Verdict, str], lang: Optional[str] = None) -> str:
        """
        Retrieves the standard citizen-facing safe template explanation in the user's language.
        Example:
        Hindi: 'यह दावा सही नहीं है। हमें इसे समर्थन देने वाला कोई विश्वसनीय आधिकारिक प्रमाण नहीं मिला।'
        English: 'This claim is not supported by reliable evidence.'
        Marathi: 'हा दावा योग्य नाही. याला समर्थन देणारा कोणताही विश्वसनीय अधिकृत पुरावा आम्हाला आढळला नाही.'
        """
        code = self.normalize_language(lang)
        verdict_key = verdict.value if isinstance(verdict, Verdict) else str(verdict).upper()
        explanations = self._locales.get(code, {}).get("explanations", {})
        val = explanations.get(verdict_key)
        if val:
            return str(val)

        en_explanations = self._locales.get(DEFAULT_LANGUAGE, {}).get("explanations", {})
        return str(en_explanations.get(verdict_key, "This claim is not supported by reliable evidence."))

    def get_message(self, key: str, lang: Optional[str] = None, default: Optional[str] = None) -> str:
        """Retrieves a localized informational message (e.g. empty submission, errors)."""
        code = self.normalize_language(lang)
        messages = self._locales.get(code, {}).get("messages", {})
        val = messages.get(key)
        if val is not None:
            return str(val)

        en_messages = self._locales.get(DEFAULT_LANGUAGE, {}).get("messages", {})
        return str(en_messages.get(key, default if default is not None else key))


# Global singleton instance
localization_service = LocalizationService()
