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

    def score_passage_relevance(
        self,
        claim_text: str,
        passage_text: str,
        source_tier: int = 2,
    ) -> float:
        """
        Calculates 7-factor relevance score for candidate evidence passages (Part 7):
        evidence_score =
            0.25 * semantic_similarity
          + 0.20 * entity_match
          + 0.25 * relation_match
          + 0.10 * exact_term_match
          + 0.10 * source_authority
          + 0.10 * temporal_relevance
        """
        claim_lower = claim_text.lower()
        passage_lower = passage_text.lower()

        claim_tokens = self._tokenize(claim_text)
        passage_tokens = self._tokenize(passage_text)

        if not claim_tokens or not passage_tokens:
            return 0.0

        # 1. Semantic similarity (recall + Jaccard)
        overlap = len(claim_tokens.intersection(passage_tokens))
        jaccard = overlap / len(claim_tokens.union(passage_tokens))
        recall = overlap / len(claim_tokens)
        semantic_similarity = (recall * 0.7) + (jaccard * 0.3)

        # 2. Entity match: check entities (capitalized / acronym / key tokens)
        entities = [w for w in re.findall(r"\b[A-Za-z0-9_]{2,}\b", claim_text) if w[0].isupper() or w.isupper()]
        if not entities:
            entities = list(claim_tokens)
        entity_hits = sum(1 for e in entities if e.lower() in passage_lower)
        entity_match = min(1.0, entity_hits / max(len(entities), 1))

        # 3. Relationship match: predicate/verbs/relations (e.g. developed, launched, banned, charges, works)
        relation_keywords = {
            "developed", "develop", "developer", "built", "created", "founded",
            "charges", "fee", "cost", "free", "available", "works", "hours",
            "banned", "ban", "prohibited", "launched", "notified", "announced",
            "national", "animal", "president", "minister", "governor",
        }
        claim_relations = [w for w in claim_tokens if w in relation_keywords]
        if claim_relations:
            relation_hits = sum(1 for r in claim_relations if r in passage_lower)
            relation_match = min(1.0, relation_hits / len(claim_relations))
        else:
            # If no explicit relation keyword, derive from refutation / corroboration signals
            has_signals = any(sig in passage_lower for sig in self.REFUTATION_SIGNALS | self.SUPPORT_SIGNALS)
            relation_match = 0.8 if has_signals else (0.5 if recall > 0.4 else 0.2)

        # 4. Exact keyword / phrase match (n-grams)
        words = [w for w in claim_lower.split() if w not in self.STOP_WORDS and len(w) > 2]
        exact_bigram_hit = False
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if bigram in passage_lower:
                exact_bigram_hit = True
                break
        exact_term_match = 1.0 if exact_bigram_hit else (0.5 if recall > 0.6 else 0.0)

        # 5. Source authority
        authority_map = {1: 1.0, 2: 0.8, 3: 0.5}
        source_authority = authority_map.get(source_tier, 0.4)

        # 6. Temporal relevance
        temporal_relevance = 0.8  # Default high for non-conflicting current passages

        score = (
            (0.25 * semantic_similarity)
            + (0.20 * entity_match)
            + (0.25 * relation_match)
            + (0.10 * exact_term_match)
            + (0.10 * source_authority)
            + (0.10 * temporal_relevance)
        )
        return min(1.0, max(0.0, score))

    def _identify_relevant_passage(
        self,
        claim_text: str,
        document_text: str,
        source_tier: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """
        Scans document text, locates small candidate paragraphs (Part 8),
        ranks candidate passages using 7-factor relevance scoring (Part 7),
        and extracts exact candidate quotes.
        """
        claim_tokens = self._tokenize(claim_text)
        if not claim_tokens:
            return None

        # Split document into paragraphs
        raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", document_text) if len(p.strip()) > 20]
        if not raw_paragraphs:
            raw_paragraphs = [p.strip() for p in document_text.split("\n") if len(p.strip()) > 20]
        if not raw_paragraphs:
            raw_paragraphs = [document_text.strip()]

        scored_passages: List[Dict[str, Any]] = []
        for para in raw_paragraphs:
            score = self.score_passage_relevance(claim_text, para, source_tier=source_tier)
            if score >= 0.20:
                scored_passages.append({
                    "text": para,
                    "score": score,
                })

        if not scored_passages:
            # Fallback to sentence-level scan across the whole document
            sentences = self._split_sentences(document_text)
            for sent in sentences:
                score = self.score_passage_relevance(claim_text, sent, source_tier=source_tier)
                if score >= 0.20:
                    scored_passages.append({"text": sent, "score": score})

        if not scored_passages:
            return None

        # Sort candidate passages by score
        scored_passages.sort(key=lambda p: p["score"], reverse=True)

        # Extract small candidate windows: Top 3-5 relevant passages (Part 8)
        top_windows = scored_passages[:5]
        combined_relevant_text = "\n\n".join(w["text"] for w in top_windows)
        highest_score = top_windows[0]["score"]

        # Extract verbatim candidate quotes from the top candidate windows
        candidate_quotes = self._extract_candidate_quotes(top_windows[0]["text"], claim_tokens)

        return {
            "relevant_text": combined_relevant_text,
            "candidate_quotes": candidate_quotes,
            "relevance_score": highest_score,
        }

    def _extract_candidate_quotes(
        self, passage: str, claim_tokens: Set[str]
    ) -> List[str]:
        """
        Extracts salient, exact verbatim sentences from the passage that address the claim.
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
            if overlap == 0:
                continue

            s_lower = s_clean.lower()
            signal_bonus = 3 if any(sig in s_lower for sig in self.REFUTATION_SIGNALS | self.SUPPORT_SIGNALS) else 0

            # Relation check
            relation_keywords = {"developed", "built", "created", "founded", "hours", "fee", "animal", "national"}
            relation_bonus = 2 if any(r in s_lower for r in relation_keywords) else 0

            score = overlap + signal_bonus + relation_bonus
            scored_sentences.append((score, s_clean))

        if scored_sentences:
            scored_sentences.sort(key=lambda x: x[0], reverse=True)
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
