from app.services.text_ingestion import (
    TextIngestionService,
    text_ingestion_service,
)
from app.services.screenshot_ingestion import (
    ScreenshotIngestionService,
    screenshot_ingestion_service,
)
from app.services.voice_ingestion import (
    VoiceIngestionService,
    voice_ingestion_service,
)
from app.services.pdf_ingestion import (
    PDFIngestionService,
    pdf_ingestion_service,
)
from app.services.url_ingestion import (
    URLIngestionService,
    url_ingestion_service,
)
from app.services.language_detection import (
    LanguageDetectorService,
    language_detector_service,
)
from app.services.claim_extractor import (
    ClaimExtractorService,
    claim_extractor_service,
)
from app.services.claim_dependency import (
    ClaimDependencyService,
    claim_dependency_service,
)
from app.services.query_generator import (
    EvidenceQueryGeneratorService,
    evidence_query_generator_service,
)
from app.services.source_registry import (
    SourceRegistryService,
    source_registry_service,
)
from app.services.retrieval import (
    CompositeWebSearchProvider,
    DuckDuckGoSearchProvider,
    EvidenceRetrievalPipeline,
    FactCheckProvider,
    GoogleFactCheckProvider,
    TavilySearchProvider,
    WebSearchProvider,
    evidence_retrieval_pipeline,
)
from app.services.evidence_extractor import (
    EvidenceExtractorService,
    evidence_extractor_service,
)
from app.services.evidence_locking import (
    EvidenceLockingService,
    evidence_locking_service,
)
from app.services.evidence_judge import (
    EvidenceJudgeService,
    evidence_judge_service,
)
from app.services.temporal_verification import (
    TemporalVerificationService,
    temporal_verification_service,
)
from app.services.rule_engine import (
    DeterministicRuleEngine,
    deterministic_rule_engine,
)
from app.services.confidence_engine import (
    ConfidenceEngine,
    confidence_engine,
)
from app.services.explanation_generator import (
    ExplanationGeneratorService,
    explanation_generator_service,
)
from app.services.claim_memory import (
    SharedClaimMemoryService,
    claim_memory_service,
)


__all__ = [
    "TextIngestionService",
    "text_ingestion_service",
    "ScreenshotIngestionService",
    "screenshot_ingestion_service",
    "VoiceIngestionService",
    "voice_ingestion_service",
    "PDFIngestionService",
    "pdf_ingestion_service",
    "URLIngestionService",
    "url_ingestion_service",
    "LanguageDetectorService",
    "language_detector_service",
    "ClaimExtractorService",
    "claim_extractor_service",
    "ClaimDependencyService",
    "claim_dependency_service",
    "EvidenceQueryGeneratorService",
    "evidence_query_generator_service",
    "SourceRegistryService",
    "source_registry_service",
    "FactCheckProvider",
    "WebSearchProvider",
    "GoogleFactCheckProvider",
    "TavilySearchProvider",
    "DuckDuckGoSearchProvider",
    "CompositeWebSearchProvider",
    "EvidenceRetrievalPipeline",
    "evidence_retrieval_pipeline",
    "EvidenceExtractorService",
    "evidence_extractor_service",
    "EvidenceLockingService",
    "evidence_locking_service",
    "EvidenceJudgeService",
    "evidence_judge_service",
    "TemporalVerificationService",
    "temporal_verification_service",
    "DeterministicRuleEngine",
    "deterministic_rule_engine",
    "ConfidenceEngine",
    "confidence_engine",
    "ExplanationGeneratorService",
    "explanation_generator_service",
    "SharedClaimMemoryService",
    "claim_memory_service",
]
