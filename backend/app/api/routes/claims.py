from fastapi import APIRouter, status

from app.schemas.claim import (
    AtomicClaimsOutput,
    ClaimExtractionInput,
)
from app.schemas.dependency import (
    ClaimDependencyGraph,
    DependencyAnalysisInput,
)
from app.schemas.evidence import (
    EvidenceExtractionInput,
    EvidenceExtractionOutput,
)
from app.schemas.query import (
    ClaimSearchQueries,
    QueryGenerationInput,
    SearchQueryGenerationOutput,
)
from app.schemas.retrieval import (
    RetrievalInput,
    RetrievalPipelineOutput,
)
from app.services.claim_extractor import claim_extractor_service
from app.services.claim_dependency import claim_dependency_service
from app.services.query_generator import evidence_query_generator_service
from app.services.retrieval import evidence_retrieval_pipeline
from app.services.evidence_extractor import evidence_extractor_service

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


@router.post(
    "/retrieve-evidence",
    response_model=RetrievalPipelineOutput,
    status_code=status.HTTP_200_OK,
    summary="Execute multi-provider evidence retrieval pipeline",
    description="Orchestrates Fact Check API, search API, candidate deduplication, source ranking, page fetch, and quote extraction.",
)
async def retrieve_evidence_endpoint(payload: RetrievalInput) -> RetrievalPipelineOutput:
    """
    Executes the 8-stage evidence retrieval pipeline:
    claim -> Fact Check API -> search API -> deduplicate -> rank -> fetch -> extract.
    """
    return evidence_retrieval_pipeline.retrieve_evidence_for_claim(
        claim_text=payload.claim_text,
        language=payload.language,
        max_candidates=payload.max_results,
    )


@router.post(
    "/extract-evidence",
    response_model=EvidenceExtractionOutput,
    status_code=status.HTTP_200_OK,
    summary="Extract candidate evidence from retrieved sources",
    description="Extracts relevant passages, candidate quotes, source IDs, and uninvented URLs for a claim. Does not mark candidates as validated evidence.",
)
async def extract_evidence_endpoint(payload: EvidenceExtractionInput) -> EvidenceExtractionOutput:
    """
    Executes Stage 2: Candidate Evidence Extraction.
    Extracts title, publisher, URL, published date, retrieved date, relevant text, and candidate quotes.
    Candidate evidence is explicitly marked is_validated=False.
    """
    candidates = evidence_extractor_service.extract_candidates(
        claim_text=payload.claim_text,
        sources=payload.retrieved_sources,
        claim_id=payload.claim_id,
    )
    return EvidenceExtractionOutput(
        claim_text=payload.claim_text,
        candidates=candidates,
        total_candidates=len(candidates),
    )


