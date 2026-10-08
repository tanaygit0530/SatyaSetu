import re
from typing import List, Set, Tuple

from app.core.exceptions import InvalidInputException, SecurityViolationException
from app.core.logging import logger

# Dangerous PDF object and action signatures defined in Adobe PDF Reference
DANGEROUS_PDF_TOKENS = {
    b"/JavaScript": "Embedded JavaScript action",
    b"/JS": "Embedded JavaScript script block",
    b"/Launch": "External process execution command (/Launch)",
    b"/EmbeddedFiles": "Embedded binary files / attachments",
    b"/SubmitForm": "Form submission external network action",
    b"/ImportData": "External data import action",
    b"/RichMedia": "Rich media / Flash execution object",
    b"/AcroForm": "Interactive form object with potential scripts",
}

# Regex to detect dangerous URI protocols inside PDF /URI actions
DANGEROUS_URI_PATTERNS = [
    re.compile(rb"/URI\s*\((javascript|data|file|vbscript):", re.IGNORECASE),
]


class PDFSecurityValidator:
    """
    Hardened PDF security controls:
    - JavaScript execution blocking (no JS runtime)
    - Deep structural scanning to reject dangerous executable actions (/Launch, /JS, /EmbeddedFiles)
    - Rejection of malicious URI protocols
    - Defense against PDF-based exploit payloads
    """

    def scan_for_dangerous_content(self, pdf_bytes: bytes) -> List[str]:
        """
        Inspects PDF byte stream and dictionary definitions for dangerous active content.
        Returns a list of detected threat descriptions.
        """
        threats: List[str] = []

        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
            return threats

        # 1. Search for dangerous PDF action dictionary tokens
        for token, desc in DANGEROUS_PDF_TOKENS.items():
            if token in pdf_bytes:
                # Disambiguate /AcroForm: only flag if accompanied by /JS or /JavaScript or actions
                if token == b"/AcroForm":
                    if b"/JS" in pdf_bytes or b"/JavaScript" in pdf_bytes or b"/AA" in pdf_bytes:
                        threats.append(f"AcroForm containing executable scripts: {desc}")
                else:
                    threats.append(desc)

        # 2. Check for dangerous non-HTTP URI schemes inside /URI dictionaries
        for pat in DANGEROUS_URI_PATTERNS:
            if pat.search(pdf_bytes):
                threats.append("Dangerous URI protocol handler (javascript:/file:/data:)")

        return threats

    def validate_pdf_security(self, pdf_bytes: bytes) -> None:
        """
        Validates PDF against all security requirements.
        Raises SecurityViolationException if any dangerous content is detected.
        """
        if not pdf_bytes:
            raise InvalidInputException("PDF payload is empty.")

        threats = self.scan_for_dangerous_content(pdf_bytes)
        if threats:
            threat_summary = "; ".join(threats)
            logger.warning("PDF security violation detected: %s", threat_summary)
            raise SecurityViolationException(
                f"PDF contains dangerous or forbidden embedded content: {threat_summary}. "
                "Document rejected for security reasons."
            )


pdf_security_validator = PDFSecurityValidator()
