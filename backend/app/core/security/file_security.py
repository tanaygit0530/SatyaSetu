import os
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.exceptions import InvalidInputException, SecurityViolationException
from app.core.logging import logger

# Magic byte signatures mapped to MIME types
MAGIC_BYTES_MAP: Dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"%PDF-": "application/pdf",
    b"OggS": "audio/ogg",
    b"\x1a\x45\xdf\xa3": "audio/webm",
}

# Variable-length magic byte prefixes checked dynamically
RIFF_MAGIC = b"RIFF"
WAVE_MAGIC = b"WAVE"
ID3_MAGIC = b"ID3"
MP3_SYNC_MAGICS = (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
M4A_FTYP = b"ftyp"

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".m4a", ".webm"}
ALLOWED_PDF_EXTENSIONS = {".pdf"}

ALL_ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS | ALLOWED_PDF_EXTENSIONS

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".ps1", ".vbs", ".js", ".mjs",
    ".py", ".pyw", ".php", ".phtml", ".html", ".htm", ".svg", ".xml",
    ".jar", ".war", ".bin", ".scr", ".msi", ".dll", ".so", ".dylib",
    ".com", ".app", ".apk",
}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "audio/wav",
    "audio/mpeg",
    "audio/ogg",
    "audio/mp4",
    "audio/webm",
}


class FileSecurityValidator:
    """
    Comprehensive file security validator:
    - Magic bytes validation
    - MIME type verification
    - File extension allowlist & path traversal prevention
    - File size limits
    - PDF page limits
    - Audio duration limits
    """

    def __init__(
        self,
        max_image_bytes: Optional[int] = None,
        max_pdf_bytes: Optional[int] = None,
        max_audio_bytes: Optional[int] = None,
        max_pdf_pages: Optional[int] = None,
        max_audio_duration_seconds: Optional[float] = None,
    ):
        self.max_image_bytes = max_image_bytes or settings.MAX_IMAGE_FILE_SIZE_BYTES
        self.max_pdf_bytes = max_pdf_bytes or settings.MAX_PDF_FILE_SIZE_BYTES
        self.max_audio_bytes = max_audio_bytes or settings.MAX_VOICE_FILE_SIZE_BYTES
        self.max_pdf_pages = max_pdf_pages or settings.MAX_PDF_PAGE_COUNT
        self.max_audio_duration_seconds = max_audio_duration_seconds or settings.MAX_VOICE_DURATION_SECONDS

    def detect_magic_mime(self, data: bytes) -> Optional[str]:
        """
        Detects true MIME type from binary magic bytes header.
        Never relies on user-supplied Content-Type or file extension.
        """
        if not data:
            return None

        # 1. Exact starts-with checks
        for magic, mime in MAGIC_BYTES_MAP.items():
            if data.startswith(magic):
                return mime

        # 2. WAV audio inspection (RIFF....WAVE)
        if len(data) >= 12 and data.startswith(RIFF_MAGIC) and data[8:12] == WAVE_MAGIC:
            return "audio/wav"

        # 3. MP3 audio inspection (ID3 tag or MPEG sync frames)
        if len(data) >= 3 and (data.startswith(ID3_MAGIC) or any(data.startswith(s) for s in MP3_SYNC_MAGICS)):
            return "audio/mpeg"

        # 4. M4A / MP4 audio inspection
        if len(data) >= 12 and M4A_FTYP in data[4:12]:
            return "audio/mp4"

        # 5. AAC raw ADTS sync frames
        if len(data) >= 2 and (data.startswith(b"\xff\xf1") or data.startswith(b"\xff\xf9")):
            return "audio/mp4"

        return None

    def validate_extension(
        self,
        filename: Optional[str],
        allowed_extensions: Optional[Set[str]] = None,
    ) -> str:
        """
        Validates filename and extension against security rules:
        - Blocks path traversal / directory components
        - Blocks dangerous executable / script extensions
        - Enforces strict allowlist
        - Detects double extension bypass attempts (e.g. evil.exe.jpg)
        """
        if not filename or not filename.strip():
            raise InvalidInputException("Filename must not be empty.")

        clean_name = os.path.basename(filename.strip().lower())
        if not clean_name or clean_name in (".", ".."):
            raise SecurityViolationException("Invalid filename pattern.")

        # Check for dangerous extensions anywhere in dotted names
        parts = clean_name.split(".")
        if len(parts) > 1:
            for ext_candidate in parts[1:]:
                if f".{ext_candidate}" in DANGEROUS_EXTENSIONS:
                    raise SecurityViolationException(
                        f"Forbidden dangerous file extension '.{ext_candidate}' in filename '{clean_name}'."
                    )

        _, ext = os.path.splitext(clean_name)
        if not ext:
            raise InvalidInputException(f"Filename '{clean_name}' is missing an extension.")

        allowlist = allowed_extensions or ALL_ALLOWED_EXTENSIONS
        if ext not in allowlist:
            raise SecurityViolationException(
                f"File extension '{ext}' is not permitted. Allowed: {sorted(list(allowlist))}."
            )

        return ext

    def validate_file(
        self,
        data: bytes,
        filename: Optional[str] = None,
        expected_category: Optional[str] = None,
        custom_max_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Complete file validation pipeline:
        1. 0-byte check
        2. Size boundary check
        3. Magic bytes / MIME detection
        4. MIME allowlist check
        5. Extension allowlist check
        6. Extension and MIME type consistency check
        """
        if len(data) == 0:
            raise InvalidInputException("File payload is empty (0 bytes).")

        # Determine size limit based on category
        cat_lower = (expected_category or "").lower()
        if cat_lower in ("image", "screenshot"):
            max_size = custom_max_bytes or self.max_image_bytes
        elif cat_lower in ("pdf", "circular"):
            max_size = custom_max_bytes or self.max_pdf_bytes
        elif cat_lower in ("audio", "voice"):
            max_size = custom_max_bytes or self.max_audio_bytes
        else:
            max_size = custom_max_bytes or max(self.max_image_bytes, self.max_pdf_bytes, self.max_audio_bytes)

        if len(data) > max_size:
            raise InvalidInputException(
                f"File size ({len(data)} bytes) exceeds the maximum allowed limit of {max_size} bytes."
            )

        # Detect MIME from magic bytes
        detected_mime = self.detect_magic_mime(data)
        if not detected_mime or detected_mime not in ALLOWED_MIME_TYPES:
            raise SecurityViolationException(
                f"MIME validation failed: Unrecognized or forbidden file format. "
                f"Detected MIME: '{detected_mime or 'unknown'}'. Magic bytes signature is not permitted."
            )

        # Category consistency check
        if cat_lower in ("image", "screenshot") and not detected_mime.startswith("image/"):
            raise SecurityViolationException(
                f"Expected image content, but detected MIME '{detected_mime}'."
            )
        if cat_lower in ("pdf", "circular") and detected_mime != "application/pdf":
            raise SecurityViolationException(
                f"Expected PDF content, but detected MIME '{detected_mime}'."
            )
        if cat_lower in ("audio", "voice") and not detected_mime.startswith("audio/"):
            raise SecurityViolationException(
                f"Expected audio content, but detected MIME '{detected_mime}'."
            )

        # Extension validation if filename provided
        valid_ext = None
        if filename:
            valid_ext = self.validate_extension(filename)
            # Ensure extension matches detected MIME
            if detected_mime == "application/pdf" and valid_ext != ".pdf":
                raise SecurityViolationException("MIME type 'application/pdf' does not match file extension.")
            if detected_mime.startswith("image/") and valid_ext not in ALLOWED_IMAGE_EXTENSIONS:
                raise SecurityViolationException(f"Image MIME '{detected_mime}' does not match extension '{valid_ext}'.")
            if detected_mime.startswith("audio/") and valid_ext not in ALLOWED_AUDIO_EXTENSIONS:
                raise SecurityViolationException(f"Audio MIME '{detected_mime}' does not match extension '{valid_ext}'.")

        return {
            "size_bytes": len(data),
            "mime_type": detected_mime,
            "extension": valid_ext,
            "category": detected_mime.split("/")[0] if detected_mime != "application/pdf" else "pdf",
            "is_valid": True,
        }

    def validate_page_limit(self, page_count: int, max_pages: Optional[int] = None) -> None:
        """Enforces PDF document page boundaries."""
        cap = max_pages or self.max_pdf_pages
        if page_count < 1:
            raise InvalidInputException("PDF document contains 0 pages.")
        if page_count > cap:
            raise InvalidInputException(
                f"PDF page count ({page_count}) exceeds the maximum allowed limit of {cap} pages."
            )

    def validate_audio_duration_limit(
        self,
        duration_seconds: float,
        max_duration: Optional[float] = None,
    ) -> None:
        """Enforces audio recording duration boundaries."""
        cap = max_duration or self.max_audio_duration_seconds
        if duration_seconds <= 0:
            return  # Allow 0 or empty for edge-case silent audio
        if duration_seconds > cap:
            raise InvalidInputException(
                f"Audio recording duration ({duration_seconds:.1f}s) exceeds the maximum allowed limit "
                f"of {cap:.0f} seconds."
            )


file_security_validator = FileSecurityValidator()
