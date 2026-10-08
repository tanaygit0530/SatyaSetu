from fastapi import APIRouter, status

from app.schemas.claim import (
    AtomicClaimsOutput,
    ClaimExtractionInput,
    ClaimResult,
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
from app.schemas.judge import (
    JudgeEvaluationInput,
    JudgeEvaluationOutput,
)
from app.schemas.temporal import (
    TemporalVerificationInput,
    TemporalVerificationResult,
)
from app.schemas.rule_engine import VerdictEngineInput
from app.schemas.confidence import (
    ConfidenceInput,
    ConfidenceOutput,
    MessageConfidenceInput,
    MessageConfidenceOutput,
)
from app.schemas.explanation import (
    ExplanationInput,
    ExplanationOutput,
)
from app.schemas.claim_memory import (
    ClaimMemoryLookupInput,
    ClaimMemoryLookupResult,
    ClaimMemoryRecord,
    ClaimMemoryStoreInput,
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
from app.services.evidence_judge import evidence_judge_service
from app.services.temporal_verification import temporal_verification_service
from app.services.rule_engine import DeterministicRuleEngine
from app.services.confidence_engine import confidence_engine
from app.services.explanation_generator import explanation_generator_service
from app.services.claim_memory import claim_memory_service

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


@router.post(
    "/judge-evidence",
    response_model=JudgeEvaluationOutput,
    status_code=status.HTTP_200_OK,
    summary="Evaluate evidence stance using sandboxed Evidence Judge",
    description="Judges evidence stance (SUPPORTS, CONTRADICTS, MIXED, IRRELEVANT) without deciding final verdict, browsing, or inventing URLs.",
)
async def judge_evidence_endpoint(payload: JudgeEvaluationInput) -> JudgeEvaluationOutput:
    """
    Executes Evidence Judge:
    - Sandboxed view: sees ONLY claim, validated quotes, IDs, and source metadata.
    - Strictly prohibited from browsing, creating URLs, or deciding TRUE/FALSE verdicts.
    - Defense against prompt injection inside quotes.
    - Returns structured JSON assessments passed to deterministic code.
    """
    assessments = evidence_judge_service.judge_evidence_batch(
        claim_text=payload.claim_text,
        evidence_items=payload.evidence_items,
    )
    return JudgeEvaluationOutput(
        claim_text=payload.claim_text,
        assessments=assessments,
    )


@router.post(
    "/verify-temporality",
    response_model=TemporalVerificationResult,
    status_code=status.HTTP_200_OK,
    summary="Distinguish TRUE THEN from TRUE NOW with temporal verification",
    description="Extracts claim date, evidence date, effective date, expiry date, current date, and determines temporal status.",
)
async def verify_temporality_endpoint(payload: TemporalVerificationInput) -> TemporalVerificationResult:
    """
    Executes Temporal Verification:
    - Distinguishes TRUE THEN from TRUE NOW
    - Detects historical claims vs ongoing present claims
    - Identifies supersession by newer contradictory evidence
    - Extracts claim date, evidence date, effective date, expiry date, current date
    """
    return temporal_verification_service.verify_temporality(
        claim_text=payload.claim_text,
        evidence_items=payload.evidence_items,
        current_date_str=payload.current_date,
    )


@router.post(
    "/compute-verdict",
    response_model=ClaimResult,
    status_code=status.HTTP_200_OK,
    summary="Compute deterministic verdict without LLM calls",
    description="Deterministic evaluation over 5 canonical verdicts (VERIFIED, FALSE, OUTDATED, PARTLY_SUPPORTED, CANNOT_BE_CONFIRMED) with explicit audit rule trace.",
)
async def compute_verdict_endpoint(payload: VerdictEngineInput) -> ClaimResult:
    """
    Executes Deterministic Verdict Engine:
    - Strictly does NOT call an LLM.
    - Evaluates statutory precedence rules, source tiers, temporal status, contradictions, and agreements.
    - Produces canonical verdict and explicit rule trace for audit dashboards.
    """
    return DeterministicRuleEngine.compute_verdict(
        claim=payload.claim,
        validated_evidence=payload.validated_evidence,
        evidence_judgments=payload.evidence_judgments,
        temporal_status=payload.temporal_status,
        source_tiers=payload.source_tiers,
        contradiction_strength=payload.contradiction_strength,
        agreement=payload.agreement,
        recency=payload.recency,
        retrieval_quality=payload.retrieval_quality,
    )


@router.post(
    "/calculate-confidence",
    response_model=ConfidenceOutput,
    status_code=status.HTTP_200_OK,
    summary="Compute deterministic confidence without LLM calls",
    description="Calculates categorical confidence (HIGH, MEDIUM, LOW) from credibility, agreement, relevance, recency, retrieval quality, contradiction strength, ambiguity, and evidence quantity.",
)
async def calculate_confidence_endpoint(payload: ConfidenceInput) -> ConfidenceOutput:
    """
    Executes Deterministic Confidence Calculation:
    - Strictly does NOT call an LLM.
    - Evaluates 8 core evidentiary signals.
    - Returns strictly HIGH, MEDIUM, or LOW without exposing fake precision.
    """
    return confidence_engine.calculate_confidence_detailed(payload)


@router.post(
    "/message-confidence",
    response_model=MessageConfidenceOutput,
    status_code=status.HTTP_200_OK,
    summary="Compute aggregate message confidence limited by weakest important claim",
    description="Aggregates individual atomic claim confidence ratings. Overall confidence is limited by the weakest important claim.",
)
async def message_confidence_endpoint(payload: MessageConfidenceInput) -> MessageConfidenceOutput:
    """
    Executes Aggregate Message Confidence:
    - Limited by the weakest important claim.
    """
    return confidence_engine.calculate_message_confidence_detailed(payload.claims)


@router.post(
    "/generate-explanation",
    response_model=ExplanationOutput,
    status_code=status.HTTP_200_OK,
    summary="Generate forensic explanation under 80 words with factual grounding",
    description="Generated AFTER verdict. Ensures every number/date exists in claim or evidence. Regenerates once if invalid, then falls back to safe template.",
)
async def generate_explanation_endpoint(payload: ExplanationInput) -> ExplanationOutput:
    """
    Executes Explanation Generation:
    - Generated AFTER the verdict.
    - Simple explanation strictly under 80 words.
    - Validates that every factual number/date exists in claim or validated evidence.
    - Regenerates once on failure, then falls back to safe template.
    """
    return explanation_generator_service.generate_explanation(
        claim=payload.claim,
        verdict=payload.verdict,
        validated_evidence=payload.validated_evidence,
        rule_trace=payload.rule_trace,
        temporal_status=payload.temporal_status,
    )


@router.post(
    "/memory/lookup",
    response_model=ClaimMemoryLookupResult,
    status_code=status.HTTP_200_OK,
    summary="Query Shared Claim Memory (L0 Hash & L1 Semantic Similarity)",
    description="Queries L0 exact normalized hash or L1 semantic similarity. Verifies temporal freshness and ensures critical facts (numbers/dates) are not changed.",
)
async def memory_lookup_endpoint(payload: ClaimMemoryLookupInput) -> ClaimMemoryLookupResult:
    """
    Two-Level Shared Claim Memory Lookup:
    - L0: Exact normalized claim hash
    - L1: Semantic similarity with temporal & factual safety checks
    """
    return claim_memory_service.lookup_claim(
        claim_text=payload.claim_text,
        current_time=payload.current_time,
        similarity_threshold=payload.similarity_threshold,
    )


@router.post(
    "/memory/store",
    response_model=ClaimMemoryRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Store verified claim into Shared Claim Memory",
    description="Stores normalized claim, hash, embedding, verdict, evidence IDs, timestamps, and source versions.",
)
async def memory_store_endpoint(payload: ClaimMemoryStoreInput) -> ClaimMemoryRecord:
    """
    Stores verified claim in Shared Claim Memory.
    """
    return claim_memory_service.store_claim(
        claim_text=payload.claim_text,
        verdict=payload.verdict,
        evidence_ids=payload.evidence_ids,
        ttl_hours=payload.ttl_hours,
        source_versions=payload.source_versions,
        rule_trace=payload.rule_trace,
        explanation=payload.explanation,
        confidence=payload.confidence,
        verified_at=payload.verified_at,
        expires_at=payload.expires_at,
    )





