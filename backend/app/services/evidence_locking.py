import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.logging import logger
from app.schemas.enums import SourceTier
from app.schemas.evidence import (
    EvidenceCandidate,
    EvidenceItem,
    GroundingValidationResult,
    LockedEvidenceItem,
    RetrievedSource,
)
from app.services.source_registry import source_registry_service


class EvidenceLockingService:
    """
    Evidence Locking & Grounding Validation System.

    Guarantees:
    - Every evidence quote MUST be grounded in the fetched source text.
    - If quote does not exist in stored source text: REJECT EVIDENCE.
    - Minor whitespace differences are normalized and accepted.
    - Altered numbers, dates, words, or completely invented quotes are strictly REJECTED.
    - The system must NEVER display fabricated quotes.
    - Runs BEFORE verdict calculation.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes text for grounding comparison:
        - Normalizes unicode punctuation (curly quotes, dashes).
        - Replaces non-breaking spaces, tabs, and newlines with spaces.
        - Collapses multiple consecutive whitespace characters to a single space.
        - Strips leading and trailing whitespace.
        """
        if not text:
            return ""

        # Normalize unicode quotes and dashes
        s = text
        s = s.replace("“", '"').replace("”", '"')
        s = s.replace("‘", "'").replace("’", "'")
        s = s.replace("—", "-").replace("–", "-")
        s = s.replace("\u00a0", " ").replace("\u200b", "")

        # Collapse whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def verify_quote_grounding(
        self,
        exact_quote: str,
        source_text: str,
    ) -> GroundingValidationResult:
        """
        Verifies whether exact_quote is strictly grounded in the stored source_text.

        Behavior:
        1. Exact quote -> accepted
        2. Minor whitespace difference -> normalized and accepted
        3. Changed number -> rejected (QUOTE_NOT_FOUND)
        4. Changed date -> rejected (QUOTE_NOT_FOUND)
        5. Completely invented quote -> rejected (QUOTE_NOT_FOUND)
        """
        if not exact_quote or not exact_quote.strip():
            return GroundingValidationResult(
                valid=False,
                reason="QUOTE_NOT_FOUND",
                source_text_reference=None,
            )

        if not source_text or not source_text.strip():
            return GroundingValidationResult(
                valid=False,
                reason="QUOTE_NOT_FOUND",
                source_text_reference=None,
            )

        norm_quote = self.normalize_text(exact_quote)
        norm_source = self.normalize_text(source_text)

        # 1. Exact or normalized substring search
        pos = norm_source.find(norm_quote)

        if pos != -1:
            end_pos = pos + len(norm_quote)
            ref_str = f"offset:{pos}-{end_pos}"
            return GroundingValidationResult(
                valid=True,
                reason=None,
                source_text_reference=ref_str,
            )

        # 2. Check sentence-by-sentence containment (in case of punctuation edge-cases)
        # Quote was NOT found in source text
        logger.warning(
            "Evidence Grounding REJECTED [QUOTE_NOT_FOUND]. Quote: '%s' not present in source text.",
            exact_quote[:80],
        )
        return GroundingValidationResult(
            valid=False,
            reason="QUOTE_NOT_FOUND",
            source_text_reference=None,
        )

    def lock_evidence(
        self,
        evidence: Union[EvidenceCandidate, EvidenceItem, Dict[str, Any]],
        source_text: str,
        claim_relation: Optional[str] = None,
    ) -> GroundingValidationResult:
        """
        Validates grounding of an evidence item against source_text and returns
        a GroundingValidationResult containing a LockedEvidenceItem if valid.
        """
        # Extract quote
        if isinstance(evidence, EvidenceCandidate):
            exact_quote = evidence.candidate_quotes[0] if evidence.candidate_quotes else evidence.relevant_text
            source_url = evidence.url
            source_title = evidence.title
            publisher = evidence.publisher
            published_date = evidence.published_date
            retrieved_at = evidence.retrieved_date
            source_tier = source_registry_service.get_tier(source_url) or 2
            rel = claim_relation or evidence.stance_hint or "NEUTRAL"
        elif isinstance(evidence, EvidenceItem):
            exact_quote = evidence.exact_quote
            source_url = evidence.url
            source_title = evidence.title
            publisher = evidence.publisher
            published_date = evidence.publish_date
            retrieved_at = datetime.now(timezone.utc).isoformat()
            if evidence.tier == SourceTier.TIER_1_PRIMARY:
                source_tier = 1
            elif evidence.tier == SourceTier.TIER_2_SECONDARY:
                source_tier = 2
            else:
                source_tier = 3
            rel = claim_relation or "NEUTRAL"
        else:  # Dict
            exact_quote = evidence.get("exact_quote") or evidence.get("quote") or ""
            source_url = evidence.get("source_url") or evidence.get("url") or ""
            source_title = evidence.get("source_title") or evidence.get("title") or "Document"
            publisher = evidence.get("publisher") or "Publisher"
            published_date = evidence.get("published_date") or evidence.get("publish_date")
            retrieved_at = evidence.get("retrieved_at") or evidence.get("retrieved_date") or datetime.now(timezone.utc).isoformat()
            raw_tier = evidence.get("source_tier") or evidence.get("tier") or 2
            source_tier = 1 if raw_tier in (1, "TIER_1_PRIMARY", SourceTier.TIER_1_PRIMARY) else 2
            rel = claim_relation or evidence.get("claim_relation") or "NEUTRAL"

        # Verify quote grounding
        validation = self.verify_quote_grounding(exact_quote, source_text)
        if not validation.valid:
            return validation

        # Construct locked evidence item
        locked_item = LockedEvidenceItem(
            source_url=source_url,
            source_title=source_title,
            publisher=publisher,
            published_date=published_date,
            retrieved_at=retrieved_at,
            source_tier=source_tier,
            exact_quote=exact_quote.strip(),
            source_text_reference=validation.source_text_reference or "offset:verified",
            claim_relation=rel,
        )

        return GroundingValidationResult(
            valid=True,
            reason=None,
            source_text_reference=validation.source_text_reference,
            locked_evidence=locked_item,
        )

    def validate_and_filter_evidence(
        self,
        evidence_list: List[EvidenceItem],
        source_texts: Dict[str, str],
    ) -> Tuple[List[EvidenceItem], List[Dict[str, Any]]]:
        """
        Runs BEFORE verdict calculation.
        Validates every EvidenceItem in evidence_list against its stored source text.
        Returns:
        - grounded_evidence: List of EvidenceItems that passed grounding validation.
        - rejected_evidence: List of rejection metadata dictionaries for rejected items.
        """
        grounded_evidence: List[EvidenceItem] = []
        rejected_evidence: List[Dict[str, Any]] = []

        for ev in evidence_list:
            # Look up source text by URL or domain
            src_text = source_texts.get(ev.url) or source_texts.get(ev.domain)
            if not src_text:
                # If no raw source text provided for verification, check if exact_quote is self-consistent
                # but if strict mode is active, reject
                logger.warning("No stored source text found for URL '%s'; rejecting under strict evidence locking.", ev.url)
                rejected_evidence.append({
                    "evidence_id": ev.id,
                    "url": ev.url,
                    "reason": "SOURCE_TEXT_NOT_STORED",
                })
                continue

            result = self.verify_quote_grounding(ev.exact_quote, src_text)
            if result.valid:
                grounded_evidence.append(ev)
            else:
                rejected_evidence.append({
                    "evidence_id": ev.id,
                    "url": ev.url,
                    "quote": ev.exact_quote,
                    "reason": result.reason,
                })

        return grounded_evidence, rejected_evidence


# Default singleton instance
evidence_locking_service = EvidenceLockingService()
