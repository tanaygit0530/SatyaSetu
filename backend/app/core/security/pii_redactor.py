import re
from typing import Dict, List, Set, Tuple

# 1. Email pattern (requires a dot in the domain component)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# 2. UPI ID pattern (Virtual Payment Address - handle usually has NO dot or known bank suffix)
KNOWN_UPI_HANDLES = (
    r"okhdfcbank|okaxis|oksbi|okicici|paytm|upi|ybl|apl|axl|ibl|barodampay|pnb|cnrb|"
    r"sbi|hdfcbank|icici|kotak|axisbank|idfcbank|postbank|federal|indus"
)
UPI_PATTERN_SPECIFIC = re.compile(
    rf"\b[a-zA-Z0-9.\-_]{{2,}}@({KNOWN_UPI_HANDLES})\b",
    re.IGNORECASE,
)
# Generic UPI handle without a period/TLD
UPI_PATTERN_GENERIC = re.compile(
    r"\b[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{3,}\b(?!\.[a-zA-Z])",
    re.IGNORECASE,
)

# 3. Aadhaar patterns (12 digits, formatted as 4-4-4 or 12 continuous digits starting with 2-9)
AADHAAR_FORMATTED_PATTERN = re.compile(
    r"\b[2-9]\d{3}[\s\-]\d{4}[\s\-]\d{4}\b"
)
AADHAAR_CONTINUOUS_PATTERN = re.compile(
    r"(?<!\+)(?<!\d)[2-9]\d{11}(?!\d)"
)

# 4. Phone patterns
# Indian phone numbers (+91, 0, or raw 10 digits starting with 6, 7, 8, 9)
INDIAN_PHONE_PATTERN = re.compile(
    r"(?:\+91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}\b"
)
# International E.164 phone numbers with +
INTERNATIONAL_PHONE_PATTERN = re.compile(
    r"\+[1-9]\d{1,3}[\-\s]?\(?\d{1,4}\)?[\-\s]?\d{3,4}[\-\s]?\d{3,4}\b"
)


class PIIRedactorService:
    """
    Personally Identifiable Information (PII) Redactor.
    Enforces privacy by redacting sensitive citizen details before external logging
    or transmission to external LLMs:
    - Phone numbers -> [REDACTED_PHONE]
    - Email addresses -> [REDACTED_EMAIL]
    - Aadhaar-like numbers -> [REDACTED_AADHAAR]
    - UPI IDs -> [REDACTED_UPI]
    """

    def find_pii(self, text: str) -> Dict[str, List[str]]:
        """
        Scans text and returns all detected PII entities grouped by category.
        """
        if not text:
            return {"emails": [], "upis": [], "aadhaars": [], "phones": []}

        emails = EMAIL_PATTERN.findall(text)

        # Find UPIs that are not emails
        upis = []
        for match in UPI_PATTERN_SPECIFIC.finditer(text):
            upis.append(match.group())
        for match in UPI_PATTERN_GENERIC.finditer(text):
            val = match.group()
            if val not in emails and val not in upis:
                upis.append(val)

        # Aadhaar
        aadhaars = []
        for match in AADHAAR_FORMATTED_PATTERN.finditer(text):
            aadhaars.append(match.group())
        for match in AADHAAR_CONTINUOUS_PATTERN.finditer(text):
            val = match.group()
            if val not in aadhaars:
                aadhaars.append(val)

        # Phones
        phones = []
        for match in INDIAN_PHONE_PATTERN.finditer(text):
            val = match.group()
            # Exclude if it was matched as part of Aadhaar
            if not any(val in a for a in aadhaars):
                phones.append(val)
        for match in INTERNATIONAL_PHONE_PATTERN.finditer(text):
            val = match.group()
            if val not in phones:
                phones.append(val)

        return {
            "emails": emails,
            "upis": upis,
            "aadhaars": aadhaars,
            "phones": phones,
        }

    def has_pii(self, text: str) -> bool:
        """Returns True if any PII pattern is present in the text."""
        pii = self.find_pii(text)
        return any(len(vals) > 0 for vals in pii.values())

    def redact(self, text: str) -> str:
        """
        Replaces all phone numbers, email addresses, Aadhaar numbers, and UPI IDs
        with standardized security tokens.
        """
        if not text:
            return ""

        result = text

        # 1. Redact Emails first (has .TLD)
        result = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", result)

        # 2. Redact Specific and Generic UPI IDs
        result = UPI_PATTERN_SPECIFIC.sub("[REDACTED_UPI]", result)
        result = UPI_PATTERN_GENERIC.sub("[REDACTED_UPI]", result)

        # 3. Redact Formatted Aadhaar (4-4-4 format: e.g. 1234 5678 9012)
        result = AADHAAR_FORMATTED_PATTERN.sub("[REDACTED_AADHAAR]", result)

        # 4. Redact Phones (Indian & International with country code or 10 digits)
        result = INTERNATIONAL_PHONE_PATTERN.sub("[REDACTED_PHONE]", result)
        result = INDIAN_PHONE_PATTERN.sub("[REDACTED_PHONE]", result)

        # 5. Redact Continuous 12-digit Aadhaar
        result = AADHAAR_CONTINUOUS_PATTERN.sub("[REDACTED_AADHAAR]", result)

        return result


pii_redactor_service = PIIRedactorService()
