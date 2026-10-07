from typing import Any, Dict
from fastapi import APIRouter, status

from app.schemas.language import (
    ClaimRepresentation,
    LanguageDetectionInput,
    LanguageDetectionResult,
)
from app.services.language_detection import language_detector_service

router = APIRouter(prefix="/language", tags=["Language Detection & Representation"])


@router.post(
    "/detect",
    status_code=status.HTTP_200_OK,
    summary="Detect language, script, code-mixing, and Hinglish",
    description="Analyzes input text to identify English, Hindi, Marathi, Hinglish, or mixed vernacular code-switching.",
)
async def detect_language_endpoint(payload: LanguageDetectionInput) -> Dict[str, Any]:
    """
    Detects language ('en', 'hi', 'mr'), script ('Devanagari', 'Latin'),
    code-mixing ('is_mixed'), and Hinglish ('is_hinglish').
    Returns exact specification dictionary shape.
    """
    detection = language_detector_service.detect(payload.text)
    return detection.to_dict()


@router.post(
    "/represent-claim",
    response_model=ClaimRepresentation,
    status_code=status.HTTP_200_OK,
    summary="Create language-aware claim representation without translating original claim",
    description="Preserves original claim text, generates a separate English search-query representation for retrieval, and extracts structured language-neutral facts.",
)
async def represent_claim_endpoint(payload: LanguageDetectionInput) -> ClaimRepresentation:
    """
    Processes citizen assertion:
    - Never mutates or translates original text.
    - Generates separate English search-query representation for official retrieval.
    - Extracts language-neutral facts (numbers, dates, entities, relationships, temporal status).
    """
    return language_detector_service.create_claim_representation(payload.text)
