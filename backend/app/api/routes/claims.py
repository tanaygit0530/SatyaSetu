from fastapi import APIRouter, status

from app.schemas.claim import (
    AtomicClaimsOutput,
    ClaimExtractionInput,
)
from app.schemas.dependency import (
    ClaimDependencyGraph,
    DependencyAnalysisInput,
)
from app.services.claim_extractor import claim_extractor_service
from app.services.claim_dependency import claim_dependency_service

router = APIRouter(prefix="/claims", tags=["Claim Extraction & Dependency Analysis"])


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


@router.post(
    "/analyze-dependencies",
    response_model=ClaimDependencyGraph,
    status_code=status.HTTP_200_OK,
    summary="Analyze dependencies between atomic claims",
    description="Identifies DEPENDS_ON, DUPLICATE_OF, and CONTRADICTS links without unnecessary graph complexity, establishing optimal verification execution order.",
)
async def analyze_dependencies_endpoint(payload: DependencyAnalysisInput) -> ClaimDependencyGraph:
    """
    Analyzes claim dependencies:
    - Discovers presupposition links (DEPENDS_ON)
    - Detects duplicate assertions (DUPLICATE_OF)
    - Uncovers contradictory claims (CONTRADICTS)
    - Produces topological execution order for verification
    """
    return claim_dependency_service.analyze_dependencies(payload.claims)

