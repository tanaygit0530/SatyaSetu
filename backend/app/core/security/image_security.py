import io
from typing import Optional, Tuple
from PIL import Image, ImageOps

from app.core.exceptions import InvalidInputException, SecurityViolationException
from app.core.logging import logger


class ImageSecurityService:
    """
    Image security controls:
    - Byte integrity verification
    - Forced re-encoding into a freshly initialized in-memory image canvas
    - Complete stripping of EXIF tags, GPS metadata, camera identifiers, and comments
    - Prevention of image decompression bombs and malicious payload embedding
    """

    def __init__(self, max_pixels: int = 25_000_000):
        # Prevent decompression bomb attacks
        Image.MAX_IMAGE_PIXELS = max_pixels

    def has_exif(self, image_bytes: bytes) -> bool:
        """
        Detects whether an image payload contains embedded EXIF metadata tags.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                exif = img.getexif()
                return bool(exif and len(exif) > 0)
        except Exception:
            return False

    def sanitize_and_reencode(
        self,
        image_bytes: bytes,
        output_format: str = "PNG",
        max_dimension: Optional[int] = 4096,
    ) -> bytes:
        """
        Re-encodes image and strips all EXIF metadata.
        
        Security guarantees:
        1. Opens image and executes verify() on raw data.
        2. Transfers only raw pixel values onto a brand new Image surface.
        3. Completely drops all EXIF tags, IPTC, ICC profiles, and arbitrary chunks.
        4. Constrains dimensions to protect downstream OCR against memory exhaustion.
        5. Returns sanitized bytes in desired format (default PNG).
        """
        if not image_bytes:
            raise InvalidInputException("Image byte payload is empty.")

        # 1. Byte integrity verification
        try:
            with Image.open(io.BytesIO(image_bytes)) as check_img:
                check_img.verify()
        except Exception as e:
            raise SecurityViolationException(f"Corrupted or malformed image data: {str(e)}") from e

        # 2. Re-open to extract clean pixels
        try:
            with Image.open(io.BytesIO(image_bytes)) as raw_img:
                # Auto-orient if EXIF orientation was present BEFORE stripping
                try:
                    oriented = ImageOps.exif_transpose(raw_img)
                except Exception:
                    oriented = raw_img

                width, height = oriented.size

                # Enforce dimension sanity
                if max_dimension and (width > max_dimension or height > max_dimension):
                    scale = min(max_dimension / width, max_dimension / height)
                    new_size = (int(width * scale), int(height * scale))
                    oriented = oriented.resize(new_size, Image.Resampling.LANCZOS)
                    width, height = new_size

                # Construct a completely fresh clean canvas
                if oriented.mode in ("RGBA", "LA") or (oriented.mode == "P" and "transparency" in oriented.info):
                    clean_canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
                    clean_canvas.paste(oriented, mask=oriented.split()[-1] if oriented.mode in ("RGBA", "LA") else None)
                else:
                    clean_canvas = Image.new("RGB", (width, height), (255, 255, 255))
                    clean_canvas.paste(oriented.convert("RGB"))

                # 3. Save into fresh memory buffer without any EXIF or metadata parameters
                output_buf = io.BytesIO()
                clean_format = output_format.upper()
                if clean_format not in ("PNG", "JPEG"):
                    clean_format = "PNG"

                clean_canvas.save(output_buf, format=clean_format, optimize=True)
                sanitized_bytes = output_buf.getvalue()

                logger.debug(
                    "Image successfully sanitized and re-encoded: original=%d bytes, clean=%d bytes, format=%s",
                    len(image_bytes),
                    len(sanitized_bytes),
                    clean_format,
                )
                return sanitized_bytes

        except Exception as e:
            if isinstance(e, (InvalidInputException, SecurityViolationException)):
                raise
            raise SecurityViolationException(f"Image security processing failed: {str(e)}") from e


image_security_service = ImageSecurityService()
