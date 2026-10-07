from fastapi import APIRouter, status

from app.schemas.claim import (
    AtomicClaimsOutput,
    ClaimExtractionInput,
)
from app.schemas.dependency import (
    ClaimDependencyGraph,
    DependencyAnalysisInput,
)
from app.schemas.query import (
    ClaimSearchQueries,
    QueryGenerationInput,
    SearchQueryGenerationOutput,
)
from app.services.claim_extractor import claim_extractor_service
from app.services.claim_dependency import claim_dependency_service
from app.services.query_generator import evidence_query_generator_service

router = APIRouter(prefix="/claims", tags=["Claim Extraction, Dependencies & Evidence Queries"])


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


@router.post(
    "/generate-queries",
    response_model=SearchQueryGenerationOutput,
    status_code=status.HTTP_200_OK,
    summary="Generate 5-dimensional evidence search queries for claims",
    description="Generates original, English, entity-focused, number/date-aware, and contradiction queries with deduplication without browsing the web.",
)
async def generate_queries_endpoint(payload: QueryGenerationInput) -> SearchQueryGenerationOutput:
    """
    Generates structured search queries across 5 dimensions:
    1. Original-language query
    2. English query
    3. Entity-focused query
    4. Number/date-aware query
    5. Contradiction query
    Includes automatic deduplication.
    """
    if payload.claims:
        return evidence_query_generator_service.generate_queries_batch(payload.claims)
    if payload.claim_text:
        single_res = evidence_query_generator_service.generate_queries_for_claim(payload.claim_text)
        return SearchQueryGenerationOutput(
            claim_queries=[single_res],
            total_unique_queries=len(single_res.all_queries),
        )
    return SearchQueryGenerationOutput(claim_queries=[], total_unique_queries=0)


