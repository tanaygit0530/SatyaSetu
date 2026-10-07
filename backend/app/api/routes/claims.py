from fastapi import APIRouter, status

from app.schemas.claim import (
    AtomicClaimsOutput,
    ClaimExtractionInput,
)
from app.services.claim_extractor import claim_extractor_service

router = APIRouter(prefix="/claims", tags=["Claim Extraction"])


@router.post(
    "/extract",
    response_model=AtomicClaimsOutput,
    status_code=status.HTTP_200_OK,
    summary="Decompose citizen forward into atomic factual claims",
    description="Decomposes compound messages into atomic claims, preserves original wording, and identifies non-verifiable opinions/predictions/questions.",
)
async def extract_claims_endpoint(payload: ClaimExtractionInput) -> AtomicClaimsOutput:
    """
    Extracts atomic claims:
    - Splits compound assertions into individual atomic propositions
    - Preserves verbatim source text
    - Identifies entities, numbers, dates, locations, temporal expressions
    - Marks opinions, speculative predictions, and questions with check_worthiness = False
    """
    return claim_extractor_service.extract_claims(payload.text, is_demo=payload.is_demo)
