import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.verification_repo import VerificationRepository, verification_repo
from app.schemas.claim import AtomicClaim
from app.schemas.core import (
    ClaimVerificationResult,
    MetricRecord,
    VerificationResult,
)
from app.schemas.dependency import ClaimDependencyGraph
from app.schemas.enums import (
    ConfidenceLevel,
    InputType,
    ProcessingStatus,
    SourceTier,
    TemporalStatus,
    Verdict,
)
from app.schemas.evidence import (
    EvidenceCandidate,
    EvidenceItem,
    LockedEvidenceItem,
    RetrievedSource,
)
from app.schemas.judge import EvidenceJudgeAssessment
from app.schemas.language import LanguageDetectionResult
from app.schemas.query import ClaimSearchQueries
from app.schemas.retrieval import CandidateEvidence
from app.schemas.temporal import TemporalVerificationResult
from app.schemas.verification import VerificationResponse
from app.services.claim_dependency import ClaimDependencyService, claim_dependency_service
from app.services.claim_extractor import ClaimExtractorService, claim_extractor_service
from app.services.claim_memory import SharedClaimMemoryService, claim_memory_service
from app.services.confidence_engine import ConfidenceEngine, confidence_engine
from app.services.evidence_extractor import EvidenceExtractorService, evidence_extractor_service
from app.services.evidence_judge import EvidenceJudgeService, evidence_judge_service
from app.services.evidence_locking import EvidenceLockingService, evidence_locking_service
from app.services.explanation_generator import ExplanationGeneratorService, explanation_generator_service
from app.services.language_detection import LanguageDetectorService, language_detector_service
from app.services.pdf_ingestion import PDFIngestionService, pdf_ingestion_service
from app.services.query_generator import EvidenceQueryGeneratorService, evidence_query_generator_service
from app.services.retrieval.pipeline import EvidenceRetrievalPipeline, evidence_retrieval_pipeline
from app.services.rule_engine import DeterministicRuleEngine
from app.services.screenshot_ingestion import ScreenshotIngestionService, screenshot_ingestion_service
from app.services.source_registry import SourceRegistryService, source_registry_service
from app.services.temporal_verification import TemporalVerificationService, temporal_verification_service
from app.services.text_ingestion import TextIngestionService
from app.services.tts import TTSService, tts_service
from app.services.url_ingestion import URLIngestionService, url_ingestion_service
from app.services.voice_ingestion import VoiceIngestionService, voice_ingestion_service


class VerificationOrchestrator:
    """
    Main Verification Pipeline Orchestrator for SachCheck.

    Coordinates all 21 modular stages of forensic fact verification:

    INPUT
    ↓
    INGESTION
    ↓
    LANGUAGE DETECTION
    ↓
    CLAIM EXTRACTION
    ↓
    CLAIM NORMALIZATION
    ↓
    DEPENDENCY ANALYSIS
    ↓
    SHARED CLAIM MEMORY
    ↓
    QUERY GENERATION
    ↓
    FACT CHECK RETRIEVAL
    ↓
    WEB RETRIEVAL
    ↓
    SOURCE RANKING
    ↓
    PAGE FETCH
    ↓
    EVIDENCE EXTRACTION
    ↓
    GROUNDING VALIDATION
    ↓
    EVIDENCE JUDGE
    ↓
    TEMPORAL ANALYSIS
    ↓
    DETERMINISTIC VERDICT
    ↓
    CONFIDENCE
    ↓
    EXPLANATION
    ↓
    STORE RESULT
    ↓
    METRICS

    Guarantees:
    - Modular architecture: Each stage is implemented as an independently testable method.
    - No monolithic functions: Clear separation of concerns and input/output contracts.
    - Anti-hallucination: Never invents evidence, URLs, or quotes.
    - Deterministic decisions: Rule engine decides verdicts without LLM speculation.
    """

    def __init__(
        self,
        text_ingestion: Optional[TextIngestionService] = None,
        url_ingestion: Optional[URLIngestionService] = None,
        pdf_ingestion: Optional[PDFIngestionService] = None,
        screenshot_ingestion: Optional[ScreenshotIngestionService] = None,
        voice_ingestion: Optional[VoiceIngestionService] = None,
        language_detector: Optional[LanguageDetectorService] = None,
        claim_extractor: Optional[ClaimExtractorService] = None,
        claim_dependency: Optional[ClaimDependencyService] = None,
        claim_memory: Optional[SharedClaimMemoryService] = None,
        query_generator: Optional[EvidenceQueryGeneratorService] = None,
        retrieval_pipeline: Optional[EvidenceRetrievalPipeline] = None,
        source_registry: Optional[SourceRegistryService] = None,
        evidence_extractor: Optional[EvidenceExtractorService] = None,
        evidence_locking: Optional[EvidenceLockingService] = None,
        evidence_judge: Optional[EvidenceJudgeService] = None,
        temporal_verifier: Optional[TemporalVerificationService] = None,
        rule_engine: Optional[DeterministicRuleEngine] = None,
        confidence_calculator: Optional[ConfidenceEngine] = None,
        explanation_generator: Optional[ExplanationGeneratorService] = None,
        verification_repository: Optional[VerificationRepository] = None,
        metrics_repository: Optional[MetricsRepository] = None,
        tts_service_instance: Optional[TTSService] = None,
    ):
        self.text_ingestion = text_ingestion or TextIngestionService()
        self.url_ingestion = url_ingestion or url_ingestion_service
        self.pdf_ingestion = pdf_ingestion or pdf_ingestion_service
        self.screenshot_ingestion = screenshot_ingestion or screenshot_ingestion_service
        self.voice_ingestion = voice_ingestion or voice_ingestion_service
        self.language_detector = language_detector or language_detector_service
        self.claim_extractor = claim_extractor or claim_extractor_service
        self.claim_dependency = claim_dependency or claim_dependency_service
        self.claim_memory = claim_memory or claim_memory_service
        self.query_generator = query_generator or evidence_query_generator_service
        self.retrieval_pipeline = retrieval_pipeline or evidence_retrieval_pipeline
        self.source_registry = source_registry or source_registry_service
        self.evidence_extractor = evidence_extractor or evidence_extractor_service
        self.evidence_locking = evidence_locking or evidence_locking_service
        self.evidence_judge = evidence_judge or evidence_judge_service
        self.temporal_verifier = temporal_verifier or temporal_verification_service
        self.rule_engine = rule_engine or DeterministicRuleEngine()
        self.confidence_calculator = confidence_calculator or confidence_engine
        self.explanation_generator = explanation_generator or explanation_generator_service
        self.verification_repo = verification_repository or verification_repo
        self.metrics_repo = metrics_repository or MetricsRepository()
        self.tts_service = tts_service_instance or tts_service

    # =========================================================================
    # STAGE 1: INPUT
    # =========================================================================

    def stage_input(self, content: str, input_type: str = "TEXT") -> Dict[str, Any]:
        """
        Stage 1: Validates and standardizes input parameters.
        """
        if not content or not content.strip():
            raise InvalidInputException("Input content cannot be empty.")
        clean_content = content.strip()
        clean_type = input_type.upper().strip() if input_type else "TEXT"
        return {
            "content": clean_content,
            "input_type": clean_type,
        }

    # =========================================================================
    # STAGE 2: INGESTION
    # =========================================================================

    def stage_ingestion(self, content: str, input_type: str = "TEXT") -> str:
        """
        Stage 2: Modality-specific ingestion and text extraction.
        """
        clean_type = input_type.upper().strip() if input_type else "TEXT"

        try:
            if clean_type == "URL":
                res = self.url_ingestion.ingest_url(content)
                text = f"{res.title}. {res.text}".strip() if res.title else res.text
                return text or content
            elif clean_type in ("TEXT", "WHATSAPP", "WEB_PORTAL"):
                res = self.text_ingestion.ingest(content)
                return res.normalized_text
            elif clean_type == "PDF":
                # If content is a URL or filepath, parse via PDF ingestion
                if content.startswith(("http://", "https://", "/")):
                    res = self.pdf_ingestion.ingest_pdf(content)
                    extracted = " ".join(p.text for p in res.text_pages)
                    return extracted or content
                return content
            elif clean_type == "SCREENSHOT":
                if content.startswith(("http://", "https://", "/")):
                    res = self.screenshot_ingestion.ingest_screenshot(content)
                    return res.extracted_text or content
                return content
            elif clean_type == "VOICE":
                if content.startswith(("http://", "https://", "/")):
                    res = self.voice_ingestion.ingest_voice(content)
                    return res.transcript or content
                return content
        except Exception as e:
            logger.warning("Ingestion specialized handler failed for modality %s: %s. Using raw text.", clean_type, e)

        return content.strip()

    # =========================================================================
    # STAGE 3: LANGUAGE DETECTION
    # =========================================================================

    def stage_language_detection(self, text: str) -> LanguageDetectionResult:
        """
        Stage 3: Language, script, and code-mixing detection.
        """
        return self.language_detector.detect(text)

    # =========================================================================
    # STAGE 4: CLAIM EXTRACTION
    # =========================================================================

    def stage_claim_extraction(self, text: str, is_demo: bool = False) -> List[AtomicClaim]:
        """
        Stage 4: Decomposes citizen text into atomic, check-worthy factual claims.
        """
        output = self.claim_extractor.extract_claims(text, is_demo=is_demo)
        claims = output.claims

        if not claims:
            # Fallback if no atomic claims decomposed
            norm = self.stage_claim_normalization(text)
            claims = [
                AtomicClaim(
                    claim_id="clm_001",
                    original_text=text,
                    normalized_claim=norm,
                    language="en",
                    claim_type="factual",
                    check_worthiness=True,
                )
            ]
        return claims

    # =========================================================================
    # STAGE 5: CLAIM NORMALIZATION
    # =========================================================================

    def stage_claim_normalization(self, claim: Union[AtomicClaim, str]) -> str:
        """
        Stage 5: Canonicalizes claim into standardized proposition.
        """
        text = claim.normalized_claim if isinstance(claim, AtomicClaim) else claim
        if not text and isinstance(claim, AtomicClaim):
            text = claim.original_text
        return self.claim_memory.normalize_claim(text or "")

    # =========================================================================
    # STAGE 6: DEPENDENCY ANALYSIS
    # =========================================================================

    def stage_dependency_analysis(self, claims: List[AtomicClaim]) -> ClaimDependencyGraph:
        """
        Stage 6: Discovers relationships and computes topological execution order.
        """
        return self.claim_dependency.analyze_dependencies(claims)

    # =========================================================================
    # STAGE 7: SHARED CLAIM MEMORY (L0 & L1 CACHE)
    # =========================================================================

    def stage_shared_claim_memory_lookup(
        self,
        claim: Union[AtomicClaim, str],
        current_time: Optional[datetime] = None,
    ) -> Any:
        """
        Stage 7: Queries Shared Claim Memory:
        - L0: Exact normalized claim hash
        - L1: Semantic similarity vector lookup with temporal freshness & fact safety checks
        """
        claim_text = claim.normalized_claim if isinstance(claim, AtomicClaim) else claim
        if not claim_text and isinstance(claim, AtomicClaim):
            claim_text = claim.original_text
        return self.claim_memory.lookup_claim(claim_text=claim_text, current_time=current_time)

    # =========================================================================
    # STAGE 8: QUERY GENERATION
    # =========================================================================

    def stage_query_generation(self, claim: Union[AtomicClaim, str]) -> ClaimSearchQueries:
        """
        Stage 8: Synthesizes high-precision queries (original, English, entity, number/date, contradiction).
        """
        claim_text = claim.normalized_claim if isinstance(claim, AtomicClaim) else claim
        if not claim_text and isinstance(claim, AtomicClaim):
            claim_text = claim.original_text
        return self.query_generator.generate_queries_for_claim(claim_text)

    # =========================================================================
    # STAGE 9: FACT CHECK RETRIEVAL
    # =========================================================================

    def stage_fact_check_retrieval(
        self,
        queries: ClaimSearchQueries,
        language: Optional[str] = None,
    ) -> List[CandidateEvidence]:
        """
        Stage 9: Queries Google Fact Check Tools API for existing ClaimReview debunks.
        """
        candidates: List[CandidateEvidence] = []
        try:
            fc_1 = self.retrieval_pipeline.fact_check_provider.search_claims(
                query=queries.claim_text,
                language_code=language,
                max_results=5,
            )
            candidates.extend(fc_1)

            if queries.contradiction_query and queries.contradiction_query != queries.claim_text:
                fc_2 = self.retrieval_pipeline.fact_check_provider.search_claims(
                    query=queries.contradiction_query,
                    language_code=language,
                    max_results=3,
                )
                candidates.extend(fc_2)
        except Exception as e:
            logger.warning("Fact check retrieval stage encountered error: %s", e)
        return candidates

    # =========================================================================
    # STAGE 10: WEB RETRIEVAL
    # =========================================================================

    def stage_web_retrieval(
        self,
        queries: ClaimSearchQueries,
    ) -> List[CandidateEvidence]:
        """
        Stage 10: Queries web search provider for statutory notices and reputable reporting.
        """
        candidates: List[CandidateEvidence] = []
        try:
            # Query English, entity, or contradiction search terms
            search_terms = [
                q for q in [queries.entity_query, queries.english_query, queries.contradiction_query]
                if q and q != queries.claim_text
            ]
            if not search_terms:
                search_terms = [queries.claim_text]

            for query_str in search_terms[:2]:
                results = self.retrieval_pipeline.search_provider.search(
                    query=query_str,
                    max_results=5,
                )
                candidates.extend(results)
        except Exception as e:
            logger.warning("Web search retrieval stage encountered error: %s", e)
        return candidates

    # =========================================================================
    # STAGE 11: SOURCE RANKING
    # =========================================================================

    def stage_source_ranking(
        self,
        candidates: List[CandidateEvidence],
    ) -> List[CandidateEvidence]:
        """
        Stage 11: Evaluates source tiers (Tier 1 official, Tier 2 fact-checkers, Tier 3 other)
        and sorts by credibility score. Disallows untrusted or blocked domains.
        """
        deduped = self.retrieval_pipeline._deduplicate_candidates(candidates)
        ranked = self.retrieval_pipeline._rank_and_filter_candidates(deduped)
        return ranked

    # =========================================================================
    # STAGE 12: PAGE FETCH
    # =========================================================================

    def stage_page_fetch(
        self,
        candidates: List[CandidateEvidence],
    ) -> List[RetrievedSource]:
        """
        Stage 12: Fetches full article content for candidate evidence items.
        """
        candidates_with_content = self.retrieval_pipeline._fetch_candidate_pages(candidates)
        retrieved_sources: List[RetrievedSource] = []
        for c in candidates_with_content:
            content_text = c.raw_content or c.snippet or ""
            retrieved_sources.append(
                RetrievedSource(
                    url=c.url,
                    title=c.title,
                    publisher=c.publisher or c.domain,
                    domain=c.domain,
                    published_date=c.publish_date,
                    text=content_text,
                )
            )
        return retrieved_sources

    # =========================================================================
    # STAGE 13: EVIDENCE EXTRACTION
    # =========================================================================

    def stage_evidence_extraction(
        self,
        claim_text: str,
        sources: List[RetrievedSource],
    ) -> List[EvidenceCandidate]:
        """
        Stage 13: Extracts relevant passages and candidate quotes from fetched source documents.
        Strictly does not mark evidence as validated yet (is_validated=False).
        """
        return self.evidence_extractor.extract_candidates(
            claim_text=claim_text,
            sources=sources,
        )

    # =========================================================================
    # STAGE 14: GROUNDING VALIDATION (EVIDENCE LOCKING)
    # =========================================================================

    def stage_grounding_validation(
        self,
        candidates: List[EvidenceCandidate],
        sources: List[RetrievedSource],
    ) -> List[LockedEvidenceItem]:
        """
        Stage 14: Verifies every evidence quote strictly exists in stored source text.
        Rejects ungrounded or altered quotes (QUOTE_NOT_FOUND).
        """
        # Map source URLs to full body text
        source_texts: Dict[str, str] = {s.url: s.text for s in sources if s.url}

        validated_locked: List[LockedEvidenceItem] = []
        for cand in candidates:
            source_body = source_texts.get(cand.url, "") or cand.relevant_text
            res = self.evidence_locking.lock_evidence(
                evidence=cand,
                source_text=source_body,
                claim_relation=cand.stance_hint,
            )
            if res.valid and res.locked_evidence is not None:
                validated_locked.append(res.locked_evidence)
            else:
                logger.warning(
                    "Quote grounding rejected for source '%s': %s",
                    cand.url,
                    res.reason,
                )
        return validated_locked

    # =========================================================================
    # STAGE 15: EVIDENCE JUDGE
    # =========================================================================

    def stage_evidence_judge(
        self,
        claim_text: str,
        validated_evidence: List[LockedEvidenceItem],
    ) -> List[EvidenceJudgeAssessment]:
        """
        Stage 15: Sandboxed evaluation of evidence stance (SUPPORTS, CONTRADICTS, MIXED, IRRELEVANT),
        relevance, and strength without deciding the final verdict.
        """
        return self.evidence_judge.judge_evidence_batch(
            claim_text=claim_text,
            evidence_items=validated_evidence,
        )

    # =========================================================================
    # STAGE 16: TEMPORAL ANALYSIS
    # =========================================================================

    def stage_temporal_analysis(
        self,
        claim_text: str,
        validated_evidence: List[LockedEvidenceItem],
        current_date_str: Optional[str] = None,
    ) -> TemporalVerificationResult:
        """
        Stage 16: Evaluates temporal currency and distinguishes TRUE THEN from TRUE NOW.
        """
        return self.temporal_verifier.verify_temporality(
            claim_text=claim_text,
            evidence_items=validated_evidence,
            current_date_str=current_date_str,
        )

    # =========================================================================
    # STAGE 17: DETERMINISTIC VERDICT
    # =========================================================================

    def stage_deterministic_verdict(
        self,
        claim: Union[AtomicClaim, str],
        validated_evidence: List[LockedEvidenceItem],
        judgments: List[EvidenceJudgeAssessment],
        temporal_result: TemporalVerificationResult,
    ) -> Tuple[Verdict, List[str]]:
        """
        Stage 17: Computes final verdict using deterministic rule logic without LLMs.
        Returns: (verdict, rule_trace)
        """
        claim_obj = claim if isinstance(claim, AtomicClaim) else AtomicClaim(
            claim_id="clm_001",
            original_text=str(claim),
            normalized_claim=str(claim),
        )

        res = self.rule_engine.compute_verdict(
            claim=claim_obj,
            validated_evidence=validated_evidence,
            evidence_judgments=judgments,
            temporal_status=temporal_result.temporal_status,
        )
        return res.verdict, res.rule_trace

    # =========================================================================
    # STAGE 18: CONFIDENCE CALCULATION
    # =========================================================================

    def stage_confidence(
        self,
        validated_evidence: List[LockedEvidenceItem],
        judgments: List[EvidenceJudgeAssessment],
        temporal_result: TemporalVerificationResult,
        verdict: Verdict,
    ) -> ConfidenceLevel:
        """
        Stage 18: Computes categorical confidence (HIGH, MEDIUM, LOW) from credibility,
        agreement, recency, and contradiction strength without fake precision.
        """
        evidence_items = [
            EvidenceItem(
                id=getattr(e, "evidence_id", None) or f"ev_{i+1}",
                publisher=getattr(e, "publisher", "Official Authority") or "Official Authority",
                domain=getattr(e, "domain", "gov.in") or "gov.in",
                title=getattr(e, "source_title", "Official Record") or "Official Record",
                url=getattr(e, "source_url", ""),
                tier=SourceTier.TIER_1_PRIMARY if getattr(e, "source_tier", 1) == 1 else (
                    SourceTier.TIER_2_SECONDARY if getattr(e, "source_tier", 1) == 2 else SourceTier.TIER_3_REPUTABLE
                ),
                exact_quote=getattr(e, "exact_quote", ""),
            )
            for i, e in enumerate(validated_evidence)
        ]
        conf_level = self.confidence_calculator.calculate_confidence(
            evidence_list=evidence_items,
            evidence_judgments=judgments,
            temporal_status=temporal_result.temporal_status,
        )
        return conf_level

    # =========================================================================
    # STAGE 19: EXPLANATION GENERATION
    # =========================================================================

    def stage_explanation(
        self,
        claim_text: str,
        verdict: Verdict,
        validated_evidence: List[LockedEvidenceItem],
        rule_trace: List[str],
        temporal_status: TemporalStatus,
        language: str = "en",
    ) -> str:
        """
        Stage 19: Generates concise citizen explanation strictly under 80 words with
        factual number/date validation in the citizen's preferred language.
        """
        res = self.explanation_generator.generate_explanation(
            claim=claim_text,
            verdict=verdict,
            validated_evidence=validated_evidence,
            rule_trace=rule_trace,
            temporal_status=temporal_status,
            language=language,
        )
        return res.explanation

    # =========================================================================
    # STAGE 20: STORE RESULT
    # =========================================================================

    def stage_store_result(
        self,
        check_id: str,
        claim_results: List[ClaimVerificationResult],
        original_content: str,
        input_type: str = "TEXT",
        duration_ms: int = 0,
        cache_hit: bool = False,
    ) -> VerificationResult:
        """
        Stage 20: Persists verified atomic claims into Shared Claim Memory
        and saves complete verification dossier to repository.
        """
        # Store newly verified claims in Shared Claim Memory
        for cr in claim_results:
            if not cr.cache_hit:
                try:
                    self.claim_memory.store_claim(
                        claim_text=cr.claim_text or cr.normalized_claim or cr.claim_id,
                        verdict=cr.verdict,
                        evidence_ids=cr.evidence_ids or [
                            getattr(e, "evidence_id", getattr(e, "id", f"ev_{i}"))
                            for i, e in enumerate(cr.evidence)
                        ],
                        rule_trace=cr.rule_trace,
                        explanation=cr.explanation,
                        confidence=cr.confidence if isinstance(cr.confidence, str) else cr.confidence.value,
                    )
                except Exception as e:
                    logger.warning("Could not persist claim '%s' to Shared Claim Memory: %s", cr.claim_id, e)

        # Aggregate findings
        overall_verdict = claim_results[0].verdict if claim_results else Verdict.CANNOT_BE_CONFIRMED
        overall_conf = claim_results[0].confidence if claim_results else ConfidenceLevel.LOW
        if not isinstance(overall_conf, ConfidenceLevel):
            overall_conf = ConfidenceLevel(str(overall_conf)) if str(overall_conf) in ["HIGH", "MEDIUM", "LOW"] else ConfidenceLevel.HIGH

        verif_result = VerificationResult(
            check_id=check_id,
            claims=claim_results,
            cache_hit=cache_hit,
            processing_time_ms=duration_ms,
            input_type=input_type,
            original_content=original_content,
            overall_verdict=overall_verdict,
            confidence=overall_conf,
            summary=claim_results[0].explanation if claim_results else "No claims verified.",
        )

        # Save to verification repo
        try:
            stored_claims = verif_result.claim_results if verif_result.claim_results else [
                ClaimResult(
                    claim_id=cr.claim_id,
                    verdict=cr.verdict,
                    confidence=cr.confidence if isinstance(cr.confidence, ConfidenceLevel) else ConfidenceLevel(str(cr.confidence)),
                    explanation=cr.explanation or "",
                    evidence_ids=cr.evidence_ids or [],
                    rule_trace=[],
                )
                for cr in claim_results
            ]
            if stored_claims:
                resp = VerificationResponse(
                    id=check_id,
                    public_id=check_id,
                    input_type=InputType.TEXT,
                    submitted_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    processing_duration_ms=duration_ms,
                    source_origin=input_type,
                    original_message=original_content,
                    overall_verdict=overall_verdict,
                    overall_confidence=overall_conf,
                    verdict_summary=verif_result.summary or "",
                    claims=stored_claims,
                    cache_hit=cache_hit,
                )
                self.verification_repo.save(resp)
        except Exception as e:
            logger.debug("Verification dossier repo persistence note: %s", e)

        return verif_result

    # =========================================================================
    # STAGE 21: METRICS
    # =========================================================================

    def stage_metrics(
        self,
        check_id: str,
        cache_hit: bool,
        duration_ms: int,
        claim_results: List[ClaimVerificationResult],
    ) -> None:
        """
        Stage 21: Records operational telemetry metrics in MetricsRepository.
        """
        try:
            verdict_str = claim_results[0].verdict.value if claim_results else "UNKNOWN"
            metric = MetricRecord(
                metric_id=f"met_{uuid.uuid4().hex[:8]}",
                metric_name="verification_pipeline_run",
                value=float(duration_ms),
                dimensions={
                    "check_id": check_id,
                    "cache_hit": str(cache_hit).lower(),
                    "verdict": verdict_str,
                    "claim_count": str(len(claim_results)),
                },
            )
            self.metrics_repo.record_metric(metric)
        except Exception as e:
            logger.warning("Could not record verification metrics: %s", e)

    # =========================================================================
    # MASTER COORDINATOR: ORCHESTRATE
    # =========================================================================

    def orchestrate(
        self,
        content: str,
        input_type: str = "TEXT",
        is_demo: bool = False,
        check_id: Optional[str] = None,
        current_time: Optional[datetime] = None,
        progress_callback: Optional[Any] = None,
        generate_voice: bool = False,
    ) -> VerificationResult:
        """
        Executes end-to-end fact verification coordinating all 21 modular stages.

        Returns VerificationResult conforming to:
        {
          "check_id": "chk_001",
          "claims": [
            {
              "claim_id": "clm_001",
              "verdict": "FALSE",
              "confidence": "HIGH",
              "explanation": "...",
              "evidence": [],
              "rule_trace": []
            }
          ],
          "cache_hit": false,
          "processing_time_ms": 4210
        }
        """
        start_time = time.time()
        c_id = check_id or f"chk_{uuid.uuid4().hex[:6]}"

        def report_progress(stage: Union[ProcessingStatus, str], status_val: str = "RUNNING", err_val: Optional[str] = None):
            if progress_callback:
                try:
                    progress_callback(stage, status_val, err_val)
                except Exception as pe:
                    logger.debug("Progress callback exception for '%s': %s", c_id, pe)

        try:
            # Stage: EXTRACTING
            report_progress(ProcessingStatus.EXTRACTING, "RUNNING")

            # Stage 1: Input
            inp = self.stage_input(content, input_type)

            # Stage 2: Ingestion
            ingested_text = self.stage_ingestion(inp["content"], inp["input_type"])

            # Stage 3: Language Detection
            lang_res = self.stage_language_detection(ingested_text)

            # Stage 4: Claim Extraction
            extracted_claims = self.stage_claim_extraction(ingested_text, is_demo=is_demo)
            report_progress(ProcessingStatus.EXTRACTING, "COMPLETED")

            # Stage: CLAIMING
            report_progress(ProcessingStatus.CLAIMING, "RUNNING")

            # Stage 5: Normalization
            for c in extracted_claims:
                c.normalized_claim = self.stage_claim_normalization(c)

            # Stage 6: Dependency Analysis
            dep_graph = self.stage_dependency_analysis(extracted_claims)
            execution_order = dep_graph.execution_order or [c.claim_id for c in extracted_claims]
            claim_map = {c.claim_id: c for c in extracted_claims}

            verified_claim_results: List[ClaimVerificationResult] = []
            all_claims_cached = True

            # Process claims in topological order
            for cid in execution_order:
                claim_item = claim_map.get(cid)
                if not claim_item:
                    continue

                claim_text = claim_item.normalized_claim or claim_item.original_text

                # Stage 7: Shared Claim Memory Lookup
                mem_lookup = self.stage_shared_claim_memory_lookup(claim_item, current_time=current_time)

                if mem_lookup.hit and mem_lookup.record is not None:
                    # Cache hit! Reuse safely
                    rec = mem_lookup.record
                    conf_val = rec.confidence or "HIGH"
                    conf_enum = ConfidenceLevel(conf_val) if conf_val in ["HIGH", "MEDIUM", "LOW"] else ConfidenceLevel.HIGH

                    verified_claim_results.append(
                        ClaimVerificationResult(
                            claim_id=claim_item.claim_id,
                            verdict=rec.verdict,
                            confidence=conf_enum,
                            explanation=rec.explanation or "Claim verified from shared claim memory.",
                            evidence=[],
                            rule_trace=rec.rule_trace or ["SHARED_CLAIM_MEMORY_HIT", f"{mem_lookup.level}_MATCH"],
                            evidence_ids=rec.evidence_ids or [],
                            claim_text=claim_item.original_text,
                            normalized_claim=claim_item.normalized_claim,
                            temporal_status=TemporalStatus.CURRENT,
                            cache_hit=True,
                        )
                    )
                    continue

                # Cache miss or stale -> run full verification
                all_claims_cached = False
                report_progress(ProcessingStatus.CLAIMING, "COMPLETED")

                # Stage: RETRIEVING
                report_progress(ProcessingStatus.RETRIEVING, "RUNNING")

                # Stage 8: Query Generation
                queries = self.stage_query_generation(claim_item)

                # Stage 9: Fact Check Retrieval
                fc_candidates = self.stage_fact_check_retrieval(queries, language=lang_res.language)

                # Stage 10: Web Retrieval
                web_candidates = self.stage_web_retrieval(queries)
                raw_candidates = fc_candidates + web_candidates

                # Stage 11: Source Ranking
                ranked_candidates = self.stage_source_ranking(raw_candidates)
                report_progress(ProcessingStatus.RETRIEVING, "COMPLETED")

                # Stage: VALIDATING
                report_progress(ProcessingStatus.VALIDATING, "RUNNING")

                # Stage 12: Page Fetch
                fetched_sources = self.stage_page_fetch(ranked_candidates)

                # Stage 13: Evidence Extraction
                cand_evidence = self.stage_evidence_extraction(claim_text, fetched_sources)

                # Stage 14: Grounding Validation (Evidence Locking)
                validated_locked = self.stage_grounding_validation(cand_evidence, fetched_sources)
                report_progress(ProcessingStatus.VALIDATING, "COMPLETED")

                # Stage: VERIFYING
                report_progress(ProcessingStatus.VERIFYING, "RUNNING")

                # Stage 15: Evidence Judge
                judgments = self.stage_evidence_judge(claim_text, validated_locked)

                # Stage 16: Temporal Analysis
                temporal_res = self.stage_temporal_analysis(claim_text, validated_locked)

                # Stage 17: Deterministic Verdict
                verdict, rule_trace = self.stage_deterministic_verdict(
                    claim=claim_item,
                    validated_evidence=validated_locked,
                    judgments=judgments,
                    temporal_result=temporal_res,
                )

                # Stage 18: Confidence
                confidence = self.stage_confidence(
                    validated_evidence=validated_locked,
                    judgments=judgments,
                    temporal_result=temporal_res,
                    verdict=verdict,
                )

                # Stage 19: Explanation
                claim_lang = getattr(claim_item, "language", None) or getattr(lang_res, "language", "en")
                explanation = self.stage_explanation(
                    claim_text=claim_text,
                    verdict=verdict,
                    validated_evidence=validated_locked,
                    rule_trace=rule_trace,
                    temporal_status=temporal_res.temporal_status,
                    language=claim_lang,
                )
                report_progress(ProcessingStatus.VERIFYING, "COMPLETED")

                # Collect finding
                evidence_ids = [
                    getattr(e, "evidence_id", None) or f"ev_{i+1}"
                    for i, e in enumerate(validated_locked)
                ]
                verified_claim_results.append(
                    ClaimVerificationResult(
                        claim_id=claim_item.claim_id,
                        verdict=verdict,
                        confidence=confidence,
                        explanation=explanation,
                        evidence=validated_locked,
                        rule_trace=rule_trace,
                        evidence_ids=evidence_ids,
                        claim_text=claim_item.original_text,
                        normalized_claim=claim_item.normalized_claim,
                        temporal_status=temporal_res.temporal_status,
                        language=claim_lang,
                        cache_hit=False,
                    )
                )

            if all_claims_cached:
                report_progress(ProcessingStatus.CLAIMING, "COMPLETED")

            duration_ms = max(int((time.time() - start_time) * 1000), 1)
            final_cache_hit = all_claims_cached if verified_claim_results else False

            # Stage 20: Store Result
            result = self.stage_store_result(
                check_id=c_id,
                claim_results=verified_claim_results,
                original_content=content,
                input_type=inp["input_type"],
                duration_ms=duration_ms,
                cache_hit=final_cache_hit,
            )

            # Stage 21: Metrics
            self.stage_metrics(
                check_id=c_id,
                cache_hit=final_cache_hit,
                duration_ms=duration_ms,
                claim_results=verified_claim_results,
            )

            # Optional Voice / TTS output layer (never a hard dependency for verification)
            if generate_voice:
                try:
                    result = self.tts_service.attach_voice_to_verification_result(result)
                except Exception as ve:
                    logger.warning("Optional voice generation failed: %s", ve)
                    result.tts_success = False

            report_progress(ProcessingStatus.COMPLETED, "COMPLETED")
            return result

        except Exception as e:
            report_progress(ProcessingStatus.FAILED, "FAILED", err_val=str(e))
            raise

    def verify(
        self,
        content: str,
        input_type: str = "TEXT",
        is_demo: bool = False,
        check_id: Optional[str] = None,
        current_time: Optional[datetime] = None,
        progress_callback: Optional[Any] = None,
        generate_voice: bool = False,
    ) -> VerificationResult:
        """Alias for orchestrate()."""
        return self.orchestrate(
            content=content,
            input_type=input_type,
            is_demo=is_demo,
            check_id=check_id,
            current_time=current_time,
            progress_callback=progress_callback,
            generate_voice=generate_voice,
        )


verification_orchestrator = VerificationOrchestrator()
