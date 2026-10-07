from fastapi import APIRouter, File, UploadFile, status
from app.schemas.ingestion import ScreenshotIngestionResult, TextInput, TextIngestionResult
from app.services.screenshot_ingestion import screenshot_ingestion_service
from app.services.text_ingestion import text_ingestion_service

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post(
    "/text",
    response_model=TextIngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest and normalize citizen text submission",
    description="Validates, Unicode-sanitizes, whitespace-normalizes, and fingerprints citizen text input.",
)
async def ingest_text_endpoint(payload: TextInput) -> TextIngestionResult:
    """
    Ingests raw text input, validates constraints, normalizes whitespace,
    and returns sanitized text alongside SHA-256 content hash.
    """
    return text_ingestion_service.ingest(payload)


@router.post(
    "/screenshot",
    response_model=ScreenshotIngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest screenshot with multi-engine OCR fallback",
    description="Validates image magic bytes, strips EXIF metadata, executes OCR with fallback, and cleans up temp files.",
)
async def ingest_screenshot_endpoint(
    file: UploadFile = File(..., description="Uploaded JPG/JPEG or PNG screenshot"),
) -> ScreenshotIngestionResult:
    """
    Ingests binary image upload, validates MIME via magic bytes, strips EXIF,
    executes OCR with provider fallback, and returns extracted text.
    """
    contents = await file.read()
    return screenshot_ingestion_service.ingest_screenshot(contents, filename=file.filename)
