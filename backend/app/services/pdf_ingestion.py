import os
import re
import tempfile
import unicodedata
from typing import List, Optional

import fitz  # PyMuPDF

from app.core.config import settings
from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.schemas.ingestion import PDFIngestionResult, PDFPageText
from app.services.pdf.ranker import ClaimBearingPageRanker, PageRankingStrategy


PDF_MAGIC = b"%PDF-"


class PDFIngestionService:
    """
    Ingestion service for official government circulars, gazettes, and citizen PDFs.
    Uses PyMuPDF (fitz) for fast native text extraction, validates magic bytes,
    enforces page/size boundaries, detects scanned PDFs needing OCR, and prioritizes
    claim-bearing pages via ranking abstraction.
    """

    def __init__(
        self,
        ranking_strategy: Optional[PageRankingStrategy] = None,
        max_file_size: Optional[int] = None,
        max_page_count: Optional[int] = None,
        min_text_chars: Optional[int] = None,
        page_ranking_limit: Optional[int] = None,
    ):
        self.ranking_strategy = ranking_strategy or ClaimBearingPageRanker()
        self.max_file_size = max_file_size or settings.MAX_PDF_FILE_SIZE_BYTES
        self.max_page_count = max_page_count or settings.MAX_PDF_PAGE_COUNT
        self.min_text_chars = min_text_chars or settings.PDF_MIN_TEXT_CHARS
        self.page_ranking_limit = page_ranking_limit or settings.PDF_PAGE_RANKING_LIMIT

    def validate_pdf_bytes(self, data: bytes) -> None:
        """
        Validates binary header magic bytes and file size limits.
        """
        if len(data) == 0:
            raise InvalidInputException("Uploaded PDF file is empty (0 bytes).")

        if len(data) > self.max_file_size:
            raise InvalidInputException(
                f"PDF file size ({len(data)} bytes) exceeds the maximum limit "
                f"of {self.max_file_size} bytes."
            )

        if not data.startswith(PDF_MAGIC):
            # Check other binary types for clear error message
            if data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff"):
                fmt_desc = "image file"
            elif data.startswith(b"RIFF") or data.startswith(b"ID3"):
                fmt_desc = "audio file"
            else:
                fmt_desc = "unsupported format"

            raise InvalidInputException(
                f"Unsupported file format '{fmt_desc}'. Payload is not a valid PDF document (missing %PDF- header)."
            )

    def clean_page_text(self, text: str) -> str:
        """
        Normalizes Unicode and collapses redundant whitespace while preserving layout.
        """
        text = text.replace("\x00", "")
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"\s+", " ", text).strip()

    def ingest_pdf(
        self,
        pdf_bytes: bytes,
        filename: Optional[str] = None,
    ) -> PDFIngestionResult:
        """
        Validates PDF, writes to ephemeral temp file, extracts text via PyMuPDF,
        identifies meaningful text pages, detects scanned documents (needs_ocr),
        applies page ranking, and cleans up temp files.
        """
        # 1. Validate magic bytes and size
        self.validate_pdf_bytes(pdf_bytes)

        # 2. Write to temporary file for PyMuPDF processing
        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        temp_path = temp_file.name

        try:
            temp_file.write(pdf_bytes)
            temp_file.close()

            # 3. Open with PyMuPDF
            try:
                doc = fitz.open(temp_path)
            except Exception as open_err:
                raise InvalidInputException(
                    f"Corrupted or malformed PDF file: {str(open_err)}"
                ) from open_err

            try:
                # 4. Check for encryption or password protection
                if doc.is_encrypted:
                    raise InvalidInputException(
                        "Encrypted or password-protected PDFs are not supported."
                    )

                page_count = doc.page_count

                # 5. Page count boundary validation
                if page_count > self.max_page_count:
                    raise InvalidInputException(
                        f"PDF page count ({page_count}) exceeds maximum allowed limit "
                        f"of {self.max_page_count} pages."
                    )

                meaningful_pages: List[PDFPageText] = []
                total_text_length = 0
                has_images = False

                # 6. Extract text per page
                for page_idx in range(page_count):
                    page = doc.load_page(page_idx)
                    page_num = page_idx + 1  # 1-indexed for citizen legibility

                    raw_text = page.get_text("text")
                    cleaned_text = self.clean_page_text(raw_text)

                    # Check if page has images
                    if not has_images:
                        image_list = page.get_images(full=True)
                        if image_list:
                            has_images = True

                    if len(cleaned_text) >= self.min_text_chars:
                        meaningful_pages.append(
                            PDFPageText(
                                page=page_num,
                                text=cleaned_text,
                            )
                        )
                        total_text_length += len(cleaned_text)

                # 7. Scanned PDF Detection (Missing Text Layer)
                # If document has pages but zero/negligible text extracted despite having content or images,
                # mark needs_ocr = True. Do NOT run expensive OCR across all pages automatically.
                needs_ocr = False
                if page_count > 0 and len(meaningful_pages) == 0:
                    needs_ocr = True
                    logger.info("PDF (%d pages) detected as scanned document with missing text layer.", page_count)

                # 8. Apply Page Ranking abstraction for claim-bearing pages
                ranked_claim_pages: Optional[List[int]] = None
                if meaningful_pages and self.ranking_strategy:
                    ranked = self.ranking_strategy.rank_pages(
                        meaningful_pages,
                        limit=self.page_ranking_limit,
                    )
                    ranked_claim_pages = [r.page for r in ranked]

                return PDFIngestionResult(
                    input_type="PDF",
                    page_count=page_count,
                    text_pages=meaningful_pages,
                    needs_ocr=needs_ocr,
                    total_text_length=total_text_length,
                    ranked_claim_pages=ranked_claim_pages,
                )

            finally:
                doc.close()

        finally:
            # 9. Guaranteed temporary file deletion
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as del_err:
                    logger.warning("Failed to delete temp PDF file %s: %s", temp_path, del_err)


pdf_ingestion_service = PDFIngestionService()
