import concurrent.futures
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


from app.core.logging import logger
from app.schemas.enums import SourceTier
from app.schemas.evidence import EvidenceItem
from app.schemas.retrieval import (
    CandidateEvidence,
    RetrievalPipelineOutput,
)
from app.services.query_generator import evidence_query_generator_service
from app.services.retrieval.base import FactCheckProvider, WebSearchProvider
from app.services.retrieval.composite_search import CompositeWebSearchProvider
from app.services.retrieval.google_factcheck import GoogleFactCheckProvider
from app.services.source_registry import source_registry_service
from app.services.url_ingestion import url_ingestion_service


class EvidenceRetrievalPipeline:
    """
    End-to-End Evidence Retrieval Engine.

    Execution Pipeline:
    claim
    ↓
    Fact Check API
    ↓
    search API
    ↓
    collect candidates
    ↓
    deduplicate
    ↓
    source ranking
    ↓
    article/page fetch
    ↓
    evidence extraction

    Guarantees:
    - Multi-provider resilience: Does not depend on a single provider.
    - Source tier enforcement: Unknown/untrusted sources cannot become strong evidence.
    - Zero fabrication: If no useful evidence, returns an empty evidence set. Never invents evidence.
    """

    def __init__(
        self,
        fact_check_provider: Optional[FactCheckProvider] = None,
        search_provider: Optional[WebSearchProvider] = None,
    ) -> None:
        self.fact_check_provider = fact_check_provider or GoogleFactCheckProvider()
        self.search_provider = search_provider or CompositeWebSearchProvider()

    def retrieve_evidence_for_claim(
        self,
        claim_text: str,
        language: Optional[str] = None,
        max_candidates: int = 10,
        fetch_pages: bool = True,
    ) -> RetrievalPipelineOutput:
        """
        Executes the full 8-stage evidence retrieval pipeline for a given atomic claim.
        """
        clean_claim = claim_text.strip()
        if not clean_claim:
            return RetrievalPipelineOutput(
                claim_text="",
                candidates=[],
                evidence_items=[],
                status="EMPTY",
            )

        logger.info("Executing Evidence Retrieval Pipeline for claim: '%s'", clean_claim[:60])

        # ----------------------------------------------------------------------
        # Stage 1: Evidence Search Query Generation
        # ----------------------------------------------------------------------
        query_set = evidence_query_generator_service.generate_queries_for_claim(clean_claim)
        english_query = query_set.english_query or clean_claim
        entity_query = query_set.entity_query or clean_claim
        contradiction_query = query_set.contradiction_query or f"{clean_claim} not true fact check"

        # ----------------------------------------------------------------------
        # Stages 2 & 3: Concurrent Fact Check & Web Retrieval (Part 14)
        # ----------------------------------------------------------------------
        fact_check_candidates: List[CandidateEvidence] = []
        search_candidates: List[CandidateEvidence] = []

        search_terms = [q for q in [entity_query, english_query, contradiction_query] if q]
        deduped_search_terms = list(dict.fromkeys(search_terms))

        def _fetch_fact_checks() -> List[CandidateEvidence]:
            fc_res: List[CandidateEvidence] = []
            try:
                fc_res.extend(self.fact_check_provider.search_claims(query=clean_claim, language_code=language, max_results=4))
                if contradiction_query and contradiction_query != clean_claim:
                    fc_res.extend(self.fact_check_provider.search_claims(query=contradiction_query, language_code=language, max_results=3))
            except Exception as fe:
                logger.warning("Fact check provider search error: %s", fe)
            return fc_res

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            fc_future = executor.submit(_fetch_fact_checks)
            search_futures = {
                executor.submit(self.search_provider.search, q, 4): q
                for q in deduped_search_terms[:4]
            }

            try:
                fact_check_candidates = fc_future.result(timeout=6.0)
            except Exception as e:
                logger.warning("Fact check future resolution note: %s", e)

            for fut in concurrent.futures.as_completed(search_futures, timeout=8.0):
                try:
                    res = fut.result()
                    if res:
                        search_candidates.extend(res)
                except Exception as e:
                    logger.warning("Search query future resolution note: %s", e)

        # ----------------------------------------------------------------------
        # Stage 4: Collect Candidates
        # ----------------------------------------------------------------------
        all_raw_candidates: List[CandidateEvidence] = fact_check_candidates + search_candidates
        fact_check_count = len(fact_check_candidates)
        search_count = len(search_candidates)


        if not all_raw_candidates:
            logger.info("No candidates discovered from fact check or search APIs.")
            return RetrievalPipelineOutput(
                claim_text=clean_claim,
                candidates=[],
                evidence_items=[],
                total_candidates=0,
                fact_check_count=0,
                search_count=0,
                status="EMPTY",
            )

        # ----------------------------------------------------------------------
        # Stage 5: Deduplicate Candidates
        # ----------------------------------------------------------------------
        deduplicated = self._deduplicate_candidates(all_raw_candidates)

        # ----------------------------------------------------------------------
        # Stage 6: Source Ranking (SourceRegistryService)
        # ----------------------------------------------------------------------
        ranked_candidates = self._rank_and_filter_candidates(deduplicated)
        if not ranked_candidates:
            logger.info("All retrieved candidates were rejected by source trust policies.")
            return RetrievalPipelineOutput(
                claim_text=clean_claim,
                candidates=[],
                evidence_items=[],
                total_candidates=0,
                fact_check_count=fact_check_count,
                search_count=search_count,
                status="EMPTY",
            )

        top_candidates = ranked_candidates[:max_candidates]

        # ----------------------------------------------------------------------
        # Stage 7: Article / Page Fetch (Safe URL Ingestion with SSRF Protection)
        # ----------------------------------------------------------------------
        if fetch_pages:
            top_candidates = self._fetch_candidate_pages(top_candidates)

        # ----------------------------------------------------------------------
        # Stage 8: Evidence Extraction (Synthesize EvidenceItems)
        # ----------------------------------------------------------------------
        evidence_items = self._extract_evidence_items(top_candidates, clean_claim)

        return RetrievalPipelineOutput(
            claim_text=clean_claim,
            candidates=top_candidates,
            evidence_items=evidence_items,
            total_candidates=len(top_candidates),
            fact_check_count=fact_check_count,
            search_count=search_count,
            status="SUCCESS" if evidence_items else "EMPTY",
        )

    def _deduplicate_candidates(
        self, candidates: List[CandidateEvidence]
    ) -> List[CandidateEvidence]:
        """
        Deduplicates candidate evidence by normalized URL and canonical domain + title.
        Retains the richest representation if duplicates exist.
        """
        seen_urls = set()
        seen_keys = set()
        unique: List[CandidateEvidence] = []

        for c in candidates:
            # 1. Normalize URL
            norm_url = c.url.strip().lower().rstrip("/")
            if "://" in norm_url:
                norm_url = norm_url.split("://", 1)[1]

            # 2. Canonical key
            norm_title = "".join(ch for ch in c.title.lower() if ch.isalnum() or ch.isspace())[:50]
            composite_key = f"{c.domain}::{norm_title}"

            if norm_url in seen_urls or composite_key in seen_keys:
                continue

            seen_urls.add(norm_url)
            seen_keys.add(composite_key)
            unique.append(c)

        return unique

    def _rank_and_filter_candidates(
        self, candidates: List[CandidateEvidence]
    ) -> List[CandidateEvidence]:
        """
        Evaluates each candidate through SourceRegistryService.
        Enforces precedence: Tier 1 (Official) > Tier 2 (Reputable Fact-Checks/News) > Tier 3.
        Filters out disallowed/blacklisted domains.
        Unknown/untrusted sources receive credibility_score=0.0 and cannot become strong evidence.
        """
        ranked: List[CandidateEvidence] = []

        for c in candidates:
            rank = source_registry_service.rank_source(c.domain or c.url)

            # Skip explicitly disallowed or blacklisted domains
            if not rank.allowed and rank.notes and "blocked" in rank.notes.lower():
                logger.warning("Filtering blacklisted candidate: %s", c.url)
                continue

            c.tier = rank.tier
            c.is_authoritative = rank.is_authoritative
            c.publisher = c.publisher or rank.publisher or rank.domain

            # If the source registry has assigned a tier, use its credibility score;
            # otherwise, if untrusted, credibility is 0.0.
            if rank.tier is not None:
                c.credibility_score = max(c.credibility_score, rank.credibility_score)
            else:
                c.credibility_score = 0.0

            ranked.append(c)

        # Sort order:
        # 1. is_authoritative (Tier 1 official portals first)
        # 2. tier (Tier 1 > Tier 2 > Tier 3 > None)
        # 3. credibility_score (highest weight first)
        def sort_key(cand: CandidateEvidence):
            tier_val = cand.tier if cand.tier is not None else 99
            return (
                0 if cand.is_authoritative else 1,
                tier_val,
                -cand.credibility_score,
            )

        ranked.sort(key=sort_key)
        return ranked

    def _fetch_candidate_pages(
        self, candidates: List[CandidateEvidence], max_fetches: int = 3
    ) -> List[CandidateEvidence]:
        """
        Safely fetches clean article text for top candidates concurrently using url_ingestion_service.
        Adheres to SSRF restrictions, timeouts, and redirect limits.
        """
        to_fetch = []
        for c in candidates[:max_fetches]:
            if c.raw_content and len(c.raw_content) > 300:
                continue
            if not c.url.startswith("http://") and not c.url.startswith("https://"):
                continue
            to_fetch.append(c)

        if not to_fetch:
            return candidates

        def _fetch_single(cand: CandidateEvidence):
            try:
                ingested = url_ingestion_service.ingest_url(cand.url)
                if ingested.status == "SUCCESS" and ingested.text:
                    cand.raw_content = ingested.text
                    if ingested.title and (not cand.title or len(cand.title) < 10):
                        cand.title = ingested.title
                    if ingested.publisher and not cand.publisher:
                        cand.publisher = ingested.publisher
                    if ingested.published_date and not cand.publish_date:
                        cand.publish_date = ingested.published_date
            except Exception as e:
                logger.info("Page fetch for %s skipped safely: %s", cand.url, str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(to_fetch), 4)) as executor:
            list(executor.map(_fetch_single, to_fetch))

        return candidates

    def _extract_evidence_items(
        self, candidates: List[CandidateEvidence], claim_text: str
    ) -> List[EvidenceItem]:
        """
        Extracts salient quotations and synthesizes EvidenceItem records.
        Ensures strict compliance:
        - Never invents evidence.
        - Unknown/untrusted sources cannot become Tier 1 or strong evidence.
        """
        evidence_items: List[EvidenceItem] = []

        for i, c in enumerate(candidates):
            # Only consider sources with an assigned registry tier
            if c.tier is None or c.credibility_score <= 0.0:
                continue

            # Map tier integer to SourceTier enum
            if c.tier == 1:
                source_tier = SourceTier.TIER_1_PRIMARY
            elif c.tier == 2:
                source_tier = SourceTier.TIER_2_SECONDARY
            else:
                source_tier = SourceTier.TIER_3_REPUTABLE

            # Extract quote from raw content or snippet
            quote = self._extract_best_quote(c, claim_text)
            if not quote:
                continue

            evidence_items.append(
                EvidenceItem(
                    id=f"CIT-{i+1:02d}",
                    publisher=c.publisher or c.domain,
                    domain=c.domain,
                    title=c.title,
                    publish_date=c.publish_date,
                    tier=source_tier,
                    url=c.url,
                    exact_quote=quote,
                    confidence_score=round(c.credibility_score, 2),
                    is_authoritative=c.is_authoritative,
                )
            )

        return evidence_items

    @staticmethod
    def _extract_best_quote(candidate: CandidateEvidence, claim_text: str) -> str:
        """
        Pulls the most salient sentence from the fetched content or snippet.
        """
        body = candidate.raw_content or candidate.snippet or ""
        if not body:
            return ""

        sentences = [s.strip() for s in body.replace("\n", ". ").split(". ") if len(s.strip()) > 20]
        if not sentences:
            return body[:250].strip()

        claim_tokens = set(claim_text.lower().split())

        def sentence_relevance(sentence: str) -> int:
            s_words = set(sentence.lower().split())
            return len(s_words.intersection(claim_tokens))

        best_sentence = max(sentences, key=sentence_relevance, default="")
        if best_sentence:
            return best_sentence[:300].strip()

        return sentences[0][:300].strip()


# Default singleton instance
evidence_retrieval_pipeline = EvidenceRetrievalPipeline()
