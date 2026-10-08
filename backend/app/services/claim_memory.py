import hashlib
import math
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.repositories.claim_memory_repository import ClaimMemoryRepository
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.core import MetricRecord
from app.schemas.enums import Verdict
from app.schemas.claim_memory import (
    ClaimMemoryLookupInput,
    ClaimMemoryLookupResult,
    ClaimMemoryRecord,
    ClaimMemoryStoreInput,
)

# Number & date extraction regex patterns
NUM_PATTERN = re.compile(r"(?:₹|\$|€|£)?\b\d+(?:[,\.]\d+)?%?\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
MONTH_PATTERN = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b(?:\s+\d{1,2}(?:st|nd|rd|th)?)?",
    re.IGNORECASE,
)
REL_DATE_PATTERN = re.compile(
    r"\b(?:tomorrow|yesterday|today|tonight|next week|last week|next year|last year)\b",
    re.IGNORECASE,
)


class SharedClaimMemoryService:
    """
    Two-Level Shared Claim Memory for SachCheck.

    CRITICAL ARCHITECTURE:
    L0: Exact normalized claim hash lookup via Firestore.
    L1: Semantic similarity using dense embeddings with temporal & critical fact safety guardrails.

    GUARANTEES:
    - Never reuse a cached result blindly.
    - Check evidence expiry before reusing.
    - If critical numbers or dates change, reject L1 reuse and rerun verification.
    - Record cache_hit metric in telemetry.
    """

    def __init__(
        self,
        memory_repo: Optional[ClaimMemoryRepository] = None,
        metrics_repo: Optional[MetricsRepository] = None,
    ):
        self.memory_repo = memory_repo or ClaimMemoryRepository()
        self.metrics_repo = metrics_repo or MetricsRepository()
        self.gemini_key = settings.GEMINI_API_KEY
        self.default_threshold = 0.85
        self.vector_dim = 256

    STOPWORDS = {
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "by", "for",
        "with", "about", "against", "between", "into", "through", "during", "before",
        "after", "above", "below", "from", "up", "down", "out", "off", "over",
        "under", "is", "are", "was", "were", "be", "been", "being", "have", "has",
        "had", "do", "does", "did", "will", "would", "shall", "should", "may",
        "might", "must", "can", "could", "that", "this", "these", "those"
    }

    # -------------------------------------------------------------------------
    # Normalization & Hashing
    # -------------------------------------------------------------------------

    def normalize_claim(self, claim_text: str) -> str:
        """
        Normalizes a claim assertion into canonical form:
        - Lowercasing
        - Stripping leading/trailing punctuation and whitespace
        - Unicode NFKD normalization
        - Whitespace collapsing
        - Standardize compound verbal forms (e.g. 'shut down' -> 'shutdown')
        """
        if not claim_text:
            return ""

        # Unicode normalization
        text = unicodedata.normalize("NFKD", claim_text.strip())

        # Lowercase
        text = text.lower()

        # Standardize quotation marks and dashes
        text = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", text)
        text = re.sub(r"[\u2013\u2014]", "-", text)

        # Standardize compound verbal forms
        text = re.sub(r"\bshut\s+down\b", "shutdown", text)

        # Remove trailing and leading punctuation (periods, commas, exclamation marks)
        text = text.strip(".!?;:, '\"")

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def hash_claim(self, normalized_claim: str) -> str:
        """Generates cryptographic SHA-256 hash of normalized claim."""
        return hashlib.sha256(normalized_claim.encode("utf-8")).hexdigest()

    # -------------------------------------------------------------------------
    # Embeddings & Similarity Math
    # -------------------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a 256-dimensional L2-normalized vector embedding.
        Uses subword and character n-gram feature hashing with frequency weighting.
        Guarantees cosine similarity is simply the dot product.
        """
        # Call Gemini Embedding API if online & configured
        if self.gemini_key and not settings.DEMO_MODE:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.gemini_key}"
                payload = {"content": {"parts": [{"text": text}]}}
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_vec = data.get("embedding", {}).get("values", [])
                        if raw_vec:
                            return self._normalize_l2(raw_vec[:self.vector_dim])
            except Exception as e:
                logger.debug("Remote embedding failed, falling back to local deterministic embedding: %s", e)

        # Local deterministic semantic vectorizer
        return self._generate_local_embedding(text)

    def _generate_local_embedding(self, text: str) -> List[float]:
        """
        Deterministic, zero-dependency dense semantic embedding generator.
        Extracts content words, word bigrams, and character 3-grams/4-grams to capture
        paraphrase semantics, morphologic roots, and syntactic variations.
        """
        norm = self.normalize_claim(text)
        vec = [0.0] * self.vector_dim
        if not norm:
            return vec

        words = norm.split()

        # 1. Word unigrams (content words weighted heavily over grammatical stopwords)
        for w in words:
            weight = 0.25 if w in self.STOPWORDS else 3.5
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:8], 16) % self.vector_dim
            vec[h] += weight

        # 2. Word bigrams (contextual order)
        for i in range(len(words) - 1):
            bg = f"{words[i]}_{words[i+1]}"
            h = int(hashlib.md5(bg.encode("utf-8")).hexdigest()[:8], 16) % self.vector_dim
            vec[h] += 1.0

        # 3. Subword & character n-grams of content words
        content_words = [w for w in words if w not in self.STOPWORDS]
        char_corpus = "".join(content_words) if content_words else "".join(words)
        for n in (3, 4):
            for i in range(max(0, len(char_corpus) - n + 1)):
                ngram = char_corpus[i : i + n]
                h = int(hashlib.md5(ngram.encode("utf-8")).hexdigest()[:8], 16) % self.vector_dim
                vec[h] += 0.8

        return self._normalize_l2(vec)

    @staticmethod
    def _normalize_l2(vec: List[float]) -> List[float]:
        """Normalizes vector to unit length (Euclidean norm = 1.0)."""
        norm_val = math.sqrt(sum(x * x for x in vec))
        if norm_val <= 1e-9:
            return vec
        return [round(x / norm_val, 6) for x in vec]

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Computes cosine similarity between two unit vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return max(-1.0, min(1.0, dot))

    # -------------------------------------------------------------------------
    # Critical Fact Extraction & Compatibility Checks
    # -------------------------------------------------------------------------

    def extract_numbers(self, text: str) -> Set[str]:
        """Extracts normalized numbers, percentages, and amounts."""
        if not text:
            return set()
        numbers = set()
        for m in NUM_PATTERN.finditer(text):
            tok = m.group().strip()
            clean = re.sub(r"[₹\$€£,%]", "", tok).strip()
            if clean:
                numbers.add(clean.lower())
                try:
                    num_f = float(clean)
                    if num_f.is_integer():
                        numbers.add(str(int(num_f)))
                except ValueError:
                    pass
        return numbers

    def extract_dates(self, text: str) -> Set[str]:
        """Extracts years, calendar dates, and relative dates."""
        if not text:
            return set()
        dates = set()
        for m in YEAR_PATTERN.finditer(text):
            dates.add(m.group().strip().lower())
        for m in MONTH_PATTERN.finditer(text):
            token = m.group().strip().lower()
            dates.add(token)
            for part in token.split():
                cleaned = re.sub(r"(?:st|nd|rd|th)", "", part).strip()
                if cleaned:
                    dates.add(cleaned)
        for m in REL_DATE_PATTERN.finditer(text):
            dates.add(m.group().strip().lower())
        return dates

    def are_critical_facts_compatible(
        self,
        claim_text: str,
        cached_text: str,
    ) -> Tuple[bool, bool]:
        """
        Safety guardrail: Checks if numbers or dates in query conflict with cached record.
        Returns: (numbers_match, dates_match)
        """
        q_nums = self.extract_numbers(claim_text)
        c_nums = self.extract_numbers(cached_text)

        # Numbers match if both have none, or if their factual number sets intersect cleanly
        numbers_match = True
        if q_nums or c_nums:
            if q_nums != c_nums:
                numbers_match = False

        q_dates = self.extract_dates(claim_text)
        c_dates = self.extract_dates(cached_text)

        # Dates match if both have none, or if their date sets match
        dates_match = True
        if q_dates or c_dates:
            if q_dates != c_dates:
                dates_match = False

        return numbers_match, dates_match

    # -------------------------------------------------------------------------
    # Core Two-Level Lookup (L0 & L1)
    # -------------------------------------------------------------------------

    def lookup_claim(
        self,
        claim_text: str,
        current_time: Optional[datetime] = None,
        similarity_threshold: Optional[float] = None,
    ) -> ClaimMemoryLookupResult:
        """
        Executes two-level Shared Claim Memory lookup:
        - L0: Exact normalized claim hash
        - L1: Semantic similarity with temporal freshness & critical fact guardrails
        """
        norm_claim = self.normalize_claim(claim_text)
        if not norm_claim:
            return ClaimMemoryLookupResult(hit=False, reason="EMPTY_CLAIM")

        claim_hash = self.hash_claim(norm_claim)
        now = current_time or datetime.now(timezone.utc)
        threshold = similarity_threshold if similarity_threshold is not None else self.default_threshold

        # =====================================================================
        # Level 0 (L0): Exact Normalized Claim Hash Lookup
        # =====================================================================
        cached_l0 = self.memory_repo.get_by_claim_hash(claim_hash)
        if cached_l0 is not None:
            # Verify temporal freshness: if expiry has passed, do NOT reuse!
            if cached_l0.expires_at < now:
                logger.info("L0 exact match found for hash '%s', but cache is STALE (expired at %s).", claim_hash, cached_l0.expires_at)
                return ClaimMemoryLookupResult(
                    hit=False,
                    level=None,
                    record=cached_l0,
                    similarity=1.0,
                    reason="STALE_CACHE_EXPIRED",
                )

            # Valid L0 Cache Hit!
            self.memory_repo.increment_hit_count(cached_l0.cache_id)
            self._record_cache_hit_metric(level="L0", verdict=cached_l0.verdict, claim_hash=claim_hash, now=now)
            logger.info("L0 cache hit for claim hash '%s': Verdict %s", claim_hash, cached_l0.verdict.value)
            return ClaimMemoryLookupResult(
                hit=True,
                level="L0",
                record=cached_l0,
                similarity=1.0,
                reason="L0_EXACT_MATCH",
            )

        # =====================================================================
        # Level 1 (L1): Semantic Similarity Using Embeddings
        # =====================================================================
        query_embedding = self.generate_embedding(norm_claim)
        candidate_records = self.memory_repo.list_all_records()

        if not candidate_records:
            return ClaimMemoryLookupResult(hit=False, reason="CACHE_MISS_EMPTY_MEMORY")

        best_record: Optional[ClaimMemoryRecord] = None
        best_sim: float = -1.0

        for cand in candidate_records:
            sim = self.cosine_similarity(query_embedding, cand.embedding)
            if sim > best_sim:
                best_sim = sim
                best_record = cand

        if best_record is None or best_sim < threshold:
            logger.debug("L1 scan highest similarity was %.3f (below threshold %.2f).", best_sim, threshold)
            return ClaimMemoryLookupResult(
                hit=False,
                level=None,
                similarity=round(best_sim, 3) if best_sim >= 0 else None,
                reason="SIMILARITY_BELOW_THRESHOLD",
            )

        # Verify temporal freshness for candidate
        if best_record.expires_at < now:
            logger.info("L1 semantic candidate '%s' has expired at %s. Marking stale.", best_record.cache_id, best_record.expires_at)
            return ClaimMemoryLookupResult(
                hit=False,
                level=None,
                record=best_record,
                similarity=round(best_sim, 3),
                reason="STALE_CACHE_EXPIRED",
            )

        # CRITICAL SAFETY: Never reuse a cached result blindly if critical numbers or dates changed
        numbers_match, dates_match = self.are_critical_facts_compatible(
            claim_text=claim_text,
            cached_text=best_record.normalized_claim,
        )

        if not dates_match:
            logger.warning(
                "L1 candidate '%s' rejected: Dates changed between query '%s' and cached '%s'.",
                best_record.cache_id,
                claim_text,
                best_record.normalized_claim,
            )
            return ClaimMemoryLookupResult(
                hit=False,
                level=None,
                record=best_record,
                similarity=round(best_sim, 3),
                reason="CRITICAL_DATE_MISMATCH",
                numbers_matched=numbers_match,
                dates_matched=False,
            )

        if not numbers_match:
            logger.warning(
                "L1 candidate '%s' rejected: Numbers changed between query '%s' and cached '%s'.",
                best_record.cache_id,
                claim_text,
                best_record.normalized_claim,
            )
            return ClaimMemoryLookupResult(
                hit=False,
                level=None,
                record=best_record,
                similarity=round(best_sim, 3),
                reason="CRITICAL_NUMBER_MISMATCH",
                numbers_matched=False,
                dates_matched=dates_match,
            )
            return ClaimMemoryLookupResult(
                hit=False,
                level=None,
                record=best_record,
                similarity=round(best_sim, 3),
                reason="CRITICAL_DATE_MISMATCH",
                numbers_matched=numbers_match,
                dates_matched=False,
            )

        # Valid Safe L1 Cache Hit!
        self.memory_repo.increment_hit_count(best_record.cache_id)
        self._record_cache_hit_metric(level="L1", verdict=best_record.verdict, claim_hash=best_record.claim_hash, now=now)
        logger.info(
            "L1 semantic cache hit (similarity=%.3f) for claim: '%s' -> Cached: '%s'",
            best_sim,
            claim_text,
            best_record.normalized_claim,
        )
        return ClaimMemoryLookupResult(
            hit=True,
            level="L1",
            record=best_record,
            similarity=round(best_sim, 3),
            reason="L1_SEMANTIC_MATCH",
            numbers_matched=True,
            dates_matched=True,
        )

    # -------------------------------------------------------------------------
    # Store Operation
    # -------------------------------------------------------------------------

    def store_claim(
        self,
        claim_text: str,
        verdict: Verdict,
        evidence_ids: Optional[List[str]] = None,
        ttl_hours: int = 48,
        source_versions: Optional[Dict[str, str]] = None,
        rule_trace: Optional[List[str]] = None,
        explanation: Optional[str] = None,
        confidence: Optional[str] = None,
        verified_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> ClaimMemoryRecord:
        """
        Stores a verified claim into Shared Claim Memory (L0 and L1).
        Guarantees storage of:
        - claim_hash
        - normalized_claim
        - embedding
        - verdict
        - evidence_ids
        - verified_at
        - expires_at
        - source_versions
        """
        norm_claim = self.normalize_claim(claim_text)
        claim_hash = self.hash_claim(norm_claim)
        embedding = self.generate_embedding(norm_claim)

        now = verified_at or datetime.now(timezone.utc)
        exp = expires_at or (now + timedelta(hours=ttl_hours))

        record = ClaimMemoryRecord(
            claim_hash=claim_hash,
            normalized_claim=norm_claim,
            embedding=embedding,
            verdict=verdict,
            evidence_ids=evidence_ids or [],
            verified_at=now,
            expires_at=exp,
            source_versions=source_versions or {},
            cache_id=f"cch_{claim_hash[:16]}",
            rule_trace=rule_trace or [],
            explanation=explanation,
            confidence=confidence,
            last_accessed_at=now,
        )

        saved = self.memory_repo.save_memory_record(record)
        logger.info("Stored claim into memory (hash: %s, verdict: %s, expires: %s)", claim_hash[:12], verdict.value, exp.isoformat())
        return saved

    def invalidate_claim(self, claim_hash: str) -> bool:
        """Deletes a record from Shared Claim Memory by hash."""
        cache_id = f"cch_{claim_hash[:16]}"
        return self.memory_repo.delete_record(cache_id)

    # -------------------------------------------------------------------------
    # Telemetry Metrics
    # -------------------------------------------------------------------------

    def _record_cache_hit_metric(
        self,
        level: str,
        verdict: Verdict,
        claim_hash: str,
        now: datetime,
    ) -> None:
        """Records cache_hit metric in operational telemetry repository."""
        try:
            metric = MetricRecord(
                metric_id=f"met_chit_{uuid.uuid4().hex[:8]}",
                metric_name="cache_hit",
                value=1.0,
                dimensions={
                    "level": level,
                    "verdict": verdict.value,
                    "claim_hash": claim_hash[:16],
                },
                timestamp=now,
            )
            self.metrics_repo.record_metric(metric)
        except Exception as e:
            logger.debug("Telemetry metric record skipped: %s", e)


# Singleton instance
claim_memory_service = SharedClaimMemoryService()
