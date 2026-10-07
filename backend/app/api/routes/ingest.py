from fastapi import APIRouter, status
from app.schemas.ingestion import TextInput, TextIngestionResult
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
