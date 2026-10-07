import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from app.core.logging import logger
from app.schemas.evidence import EvidenceCandidate, RetrievedSource
from app.services.source_registry import source_registry_service


class EvidenceExtractorService:
    """
    Evidence Extraction Service.

    Orchestrates Stage 2 of the Evidence Lifecycle:
    Stage 1: Retrieved Evidence (RetrievedSource)
             ↓
    Stage 2: Candidate Evidence (EvidenceCandidate)
             ↓
    Stage 3: Validated Evidence (EvidenceItem / ValidatedEvidence)

    Guarantees:
    - Identifies passages and candidate quotes relevant to the claim.
    - Strictly does NOT mark something as validated evidence yet (is_validated=False).
    - Stores structured source IDs.
    - Anti-Hallucination Guarantee: Never allows the LLM or engine to invent URLs;
      URLs are strictly bound to retrieved sources.
    - Captures preliminary stance hints (e.g. REFUTES / supports FALSE verdict).
    """

    REFUTATION_SIGNALS: Set[str] = {
        "not announced",
        "has not",
        "did not",
        "denied",
        "denies",
        "no ban",
        "not banned",
        "fake",
        "false",
        "baseless",
        "misleading",
        "no shutdown",
        "untrue",
        "clarified",
        "dismissed",
        "hoax",
        "rumour",
        "rumor",
        "no truth",
        "no such",
        "rejected",
    }

    SUPPORT_SIGNALS: Set[str] = {
        "has announced",
        "officially notified",
        "banned with effect",
        "ordered closure",
        "prohibits",
        "will be suspended",
        "sanctioned",
        "confirmed",
        "gazetted",
    }

    STOP_WORDS: Set[str] = {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "shall", "should", "may", "might", "must",
        "can", "could", "this", "that", "these", "those", "it", "its",
    }

    def __init__(self) -> None:
        pass

    def extract_candidates(
        self,
        claim_text: str,
        sources: List[Union[RetrievedSource, Dict[str, Any]]],
        claim_id: Optional[str] = "clm_001",
    ) -> List[EvidenceCandidate]:
        """
        Extracts candidate evidence items from a collection of retrieved sources for a claim.
        """
        clean_claim = claim_text.strip()
        if not clean_claim or not sources:
            return []

        candidates: List[EvidenceCandidate] = []
        for idx, src in enumerate(sources):
            src_obj = src if isinstance(src, RetrievedSource) else RetrievedSource.model_validate(src)
            candidate_id = f"cand_{idx + 1:03d}"
            extracted = self.extract_from_source(
                claim_text=clean_claim,
                source=src_obj,
                claim_id=claim_id,
                candidate_id=candidate_id,
            )
            if extracted is not None:
                candidates.append(extracted)

        return candidates

    def extract_from_source(
        self,
        claim_text: str,
        source: RetrievedSource,
        claim_id: Optional[str] = "clm_001",
        candidate_id: Optional[str] = "cand_001",
    ) -> Optional[EvidenceCandidate]:
        """
        Extracts title, publisher, URL, dates, relevant text, and candidate quotes from a retrieved source.
        Does NOT validate the candidate yet.
        """
        clean_claim = claim_text.strip()
        body_text = source.text.strip()
        if not clean_claim or not body_text:
            return None

        # 1. Identify relevant passage and candidate quotes
        passage_info = self._identify_relevant_passage(clean_claim, body_text)
        if not passage_info or passage_info["relevance_score"] < 0.20:
            logger.info("Retrieved source %s contains no relevant passages for claim.", source.url)
            return None

        # 2. Resolve source ID
        source_id = self._resolve_source_id(source)

        # 3. Resolve metadata (publisher, title, domain)
        domain = source.domain or self._extract_domain(source.url)
        publisher = source.publisher
        title = source.title
        if not publisher or not title:
            source_rec = source_registry_service.get_source(domain or source.url)
            if source_rec:
                publisher = publisher or source_rec.publisher
            publisher = publisher or domain or "Unknown Publisher"
            title = title or f"Document from {domain}"

        # 4. Strict URL binding: Never allow invented URLs!
        # The URL MUST be the verified source URL from the retrieved document.
        url = source.url.strip()

        # 5. Determine stance hint
        stance_hint = self._detect_stance(passage_info["candidate_quotes"], clean_claim)

        # 6. Construct EvidenceCandidate (Explicitly is_validated=False)
        return EvidenceCandidate(
            candidate_id=candidate_id or "cand_001",
            claim_id=claim_id,
            claim_text=clean_claim,
            source_id=source_id,
            title=title,
            publisher=publisher,
            url=url,
            published_date=source.published_date,
            retrieved_date=source.retrieved_date or datetime.now(timezone.utc).isoformat(),
            relevant_text=passage_info["relevant_text"],
            candidate_quotes=passage_info["candidate_quotes"],
            relevance_score=round(passage_info["relevance_score"], 2),
            stance_hint=stance_hint,
            is_validated=False,
            validation_notes="Candidate evidence pending statutory and temporal rule engine validation.",
        )

    def _identify_relevant_passage(
        self, claim_text: str, document_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Scans document text, identifies relevant paragraphs/passages, and extracts candidate quotes.
        """
        claim_tokens = self._tokenize(claim_text)
        if not claim_tokens:
            return None

        # Split document into paragraphs and sentences
        paragraphs = [p.strip() for p in document_text.split("\n\n") if len(p.strip()) > 20]
        if not paragraphs:
            paragraphs = [p.strip() for p in document_text.split("\n") if len(p.strip()) > 20]
        if not paragraphs:
            paragraphs = [document_text]

        scored_passages: List[Dict[str, Any]] = []

        for para in paragraphs:
            para_tokens = self._tokenize(para)
            overlap = len(claim_tokens.intersection(para_tokens))
            if overlap == 0:
                continue

            jaccard = overlap / len(claim_tokens.union(para_tokens))
            recall = overlap / len(claim_tokens)

            # Check refutation / support bonus
            para_lower = para.lower()
            has_signal = any(sig in para_lower for sig in self.REFUTATION_SIGNALS | self.SUPPORT_SIGNALS)
            signal_bonus = 0.25 if has_signal else 0.0

            score = min(1.0, (recall * 0.6) + (jaccard * 0.2) + signal_bonus)
            if score > 0.20:
                scored_passages.append({
                    "text": para,
                    "score": score,
                })

        if not scored_passages:
            # Fallback to sentence-level scan across the whole document
            sentences = self._split_sentences(document_text)
            for sent in sentences:
                sent_tokens = self._tokenize(sent)
                overlap = len(claim_tokens.intersection(sent_tokens))
                if overlap > 0:
                    score = min(1.0, (overlap / len(claim_tokens)) * 0.8)
                    if score > 0.20:
                        scored_passages.append({"text": sent, "score": score})

        if not scored_passages:
            return None

        # Pick highest scoring passage as relevant_text
        best_passage = max(scored_passages, key=lambda p: p["score"])
        relevant_text = best_passage["text"]
        relevance_score = best_passage["score"]

        # Extract candidate quotes from relevant text
        candidate_quotes = self._extract_candidate_quotes(relevant_text, claim_tokens)

        return {
            "relevant_text": relevant_text,
            "candidate_quotes": candidate_quotes,
            "relevance_score": relevance_score,
        }

    def _extract_candidate_quotes(
        self, passage: str, claim_tokens: Set[str]
    ) -> List[str]:
        """
        Extracts salient, exact sentences from the passage that directly address the claim.
        """
        sentences = self._split_sentences(passage)
        if not sentences:
            return [passage[:250].strip()]

        scored_sentences = []
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            s_tokens = self._tokenize(s_clean)
            overlap = len(claim_tokens.intersection(s_tokens))
            s_lower = s_clean.lower()
            signal_bonus = 2 if any(sig in s_lower for sig in self.REFUTATION_SIGNALS | self.SUPPORT_SIGNALS) else 0
            score = overlap + signal_bonus
            if score > 0:
                scored_sentences.append((score, s_clean))

        if scored_sentences:
            scored_sentences.sort(key=lambda x: x[0], reverse=True)
            # Return top 1-2 quotes
            return [item[1] for item in scored_sentences[:2]]

        return [sentences[0].strip()]

    def _detect_stance(self, quotes: List[str], claim_text: str) -> str:
        """
        Detects preliminary stance hint:
        - REFUTES: quotes contain explicit denials, rebuttals, or negations (e.g. supporting FALSE verdict)
        - SUPPORTS: quotes corroborate assertions
        - NEUTRAL: informative or non-committal
        """
        combined = " ".join(quotes).lower()
        if any(sig in combined for sig in self.REFUTATION_SIGNALS):
            return "REFUTES"
        if any(sig in combined for sig in self.SUPPORT_SIGNALS):
            return "SUPPORTS"
        return "NEUTRAL"

    def _resolve_source_id(self, source: RetrievedSource) -> str:
        """
        Ensures a structured source ID is stored.
        Uses source.source_id if present; otherwise derives from domain or registry.
        """
        if source.source_id and source.source_id.strip():
            return source.source_id.strip()

        domain = source.domain or self._extract_domain(source.url)
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", domain.replace(".", "_"))
        return f"src_{clean_name}"

    def _extract_domain(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower()
            if ":" in domain:
                domain = domain.split(":", 1)[0]
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"

    def _tokenize(self, text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\u0900-\u097F]+\b", text.lower())
        return {w for w in words if w not in self.STOP_WORDS and len(w) > 1}

    def _split_sentences(self, text: str) -> List[str]:
        # Split on standard sentence boundaries while respecting abbreviations
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in raw_sentences if s.strip()]


# Default singleton instance
evidence_extractor_service = EvidenceExtractorService()
