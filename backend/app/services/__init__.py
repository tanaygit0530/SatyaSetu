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
]
