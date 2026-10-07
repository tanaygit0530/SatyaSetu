from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, status
from app.schemas.ingestion import (
    ScreenshotIngestionResult,
    TextInput,
    TextIngestionResult,
    VoiceIngestionResult,
)
from app.services.screenshot_ingestion import screenshot_ingestion_service
from app.services.text_ingestion import text_ingestion_service
from app.services.voice_ingestion import voice_ingestion_service

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


@router.post(
    "/voice",
    response_model=VoiceIngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest voice note or audio recording with Sarvam STT",
    description="Validates audio magic bytes, enforces 60s max duration, chunks if needed, transcribes vernacular speech, and evaluates uncertainty.",
)
async def ingest_voice_endpoint(
    file: UploadFile = File(..., description="Uploaded audio file (WAV, MP3, OGG, M4A)"),
    language_hint: Optional[str] = Form(None, description="Optional vernacular language hint (en, hi, mr, hinglish)"),
) -> VoiceIngestionResult:
    """
    Ingests audio upload, checks 60-second limit, chunks, transcribes via STTProvider,
    and returns transcript and confidence rating.
    """
    contents = await file.read()
    return voice_ingestion_service.ingest_voice(
        contents,
        language_hint=language_hint,
        filename=file.filename,
    )
