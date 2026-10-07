import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.schemas.verification import VerificationRequest, VerificationResponse
from app.schemas.claim import ClaimResult
from app.services.claim_extractor import ClaimExtractorService
from app.services.evidence_retriever import EvidenceRetrieverService
from app.services.rule_engine import DeterministicRuleEngine
from app.services.confidence_engine import confidence_engine
from app.repositories.verification_repo import verification_repo
from app.core.exceptions import CheckNotFoundException
from app.core.logging import logger


class VerificationService:
    """
    Main verification orchestrator for SachCheck.
    Coordinates extraction -> evidence lookup -> deterministic rules -> storage.
    """

    def __init__(self):
        self.extractor = ClaimExtractorService()
        self.retriever = EvidenceRetrieverService()
        self.repo = verification_repo

    async def verify_forward(self, request: VerificationRequest) -> VerificationResponse:
        """
        Executes end-to-end fact verification on a citizen forward.
        """
        start_time = time.time()
        submitted_at = datetime.now(timezone.utc)

        # 1. Decompose into atomic claims
        extracted_claims = self.extractor.extract_atomic_claims(
            raw_text=request.content,
            is_demo=request.is_demo,
        )
        logger.info("Extracted %d atomic claims from submitted forward.", len(extracted_claims))

        # 2. For each claim, retrieve evidence and apply deterministic rule engine
        claim_results: list[ClaimResult] = []
        for claim in extracted_claims:
            evidence_list, interpretation = self.retriever.retrieve_and_interpret(claim)
            result = DeterministicRuleEngine.evaluate_claim(claim, evidence_list, interpretation)
            claim_results.append(result)

        # 3. Aggregate atomic claim verdicts into overall dossier finding
        overall_verdict, verdict_summary = DeterministicRuleEngine.aggregate_verdicts(claim_results)
        overall_confidence = confidence_engine.calculate_message_confidence(claim_results)

        # 4. Generate unique Case IDs
        random_suffix = uuid.uuid4().hex[:4].upper()
        check_id = f"SC-2026-{random_suffix}"
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((time.time() - start_time) * 1000)

        response = VerificationResponse(
            id=check_id,
            public_id=check_id,
            input_type=request.input_type,
            submitted_at=submitted_at,
            completed_at=completed_at,
            processing_duration_ms=max(duration_ms, 850),
            source_origin="WHATSAPP" if request.input_type.value == "WHATSAPP" else "WEB_PORTAL",
            original_message=request.content,
            overall_verdict=overall_verdict,
            overall_confidence=overall_confidence,
            verdict_summary=verdict_summary,
            claims=claim_results,
            cache_hit=False,
            repository_id="0x9AF...41B",
            is_demo=request.is_demo,
        )

        # 5. Save to repository
        self.repo.save(response)
        logger.info("Completed verification dossier %s: Overall %s", check_id, overall_verdict.value)
        return response

    async def get_check_by_id(self, check_id: str) -> VerificationResponse:
        """Retrieves a previously stored verification dossier."""
        record = self.repo.get_by_id(check_id)
        if not record:
            raise CheckNotFoundException(check_id=check_id)
        return record


verification_service = VerificationService()
