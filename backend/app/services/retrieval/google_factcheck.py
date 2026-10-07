import httpx
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.core.logging import logger
from app.schemas.retrieval import CandidateEvidence
from app.services.retrieval.base import FactCheckProvider


class GoogleFactCheckProvider(FactCheckProvider):
    """
    Fact-checking provider utilizing the Google Fact Check Tools API (ClaimReview markup).
    Queries verified international and Indian IFCN signatory debunk databases.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = 8.0,
    ) -> None:
        self.api_key = api_key or settings.GOOGLE_FACT_CHECK_API_KEY or settings.GEMINI_API_KEY
        self.api_url = api_url or settings.GOOGLE_FACT_CHECK_API_URL
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "google_fact_check_tools"

    def search_claims(
        self,
        query: str,
        language_code: Optional[str] = None,
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        """
        Executes Google Fact Check Tools claim search query.
        Gracefully returns an empty list if unconfigured, rate-limited, or no records exist.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        if not self.api_key:
            logger.info("Google Fact Check API key not configured; skipping provider lookup.")
            return []

        params: Dict[str, Any] = {
            "query": clean_query,
            "key": self.api_key,
            "pageSize": min(max_results, 10),
        }
        if language_code:
            params["languageCode"] = language_code

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.api_url, params=params)

            if response.status_code == 400 or response.status_code == 403:
                logger.warning(
                    "Google Fact Check API returned HTTP %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return []

            response.raise_for_status()
            data = response.json()
            return self._parse_claims_response(data, max_results=max_results)

        except Exception as e:
            logger.warning("Google Fact Check API query failed gracefully: %s", str(e))
            return []

    def _parse_claims_response(
        self,
        data: Dict[str, Any],
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        """
        Parses Google Fact Check Tools API response structure into CandidateEvidence models.
        """
        candidates: List[CandidateEvidence] = []
        raw_claims = data.get("claims", [])
        if not raw_claims or not isinstance(raw_claims, list):
            return []

        for claim in raw_claims:
            claim_text = claim.get("text", "")
            claim_reviews = claim.get("claimReview", [])
            if not isinstance(claim_reviews, list):
                continue

            for review in claim_reviews:
                url = review.get("url")
                if not url:
                    continue

                publisher_info = review.get("publisher", {})
                publisher_name = publisher_info.get("name") or "Verified Fact Checker"
                site = publisher_info.get("site")

                # Extract domain
                if site:
                    domain = site.strip().lower()
                else:
                    try:
                        domain = urlparse(url).netloc.lower()
                    except Exception:
                        domain = "unknown"

                if domain.startswith("www."):
                    domain = domain[4:]

                title = review.get("title") or f"Fact Check: {claim_text[:60]}"
                rating = review.get("textualRating")
                review_date = review.get("reviewDate")

                snippet = f"Claim: '{claim_text}'. Rating: {rating or 'Reviewed'} by {publisher_name}."

                candidates.append(
                    CandidateEvidence(
                        url=url,
                        title=title,
                        snippet=snippet,
                        publisher=publisher_name,
                        domain=domain,
                        source_type="FACT_CHECK",
                        publish_date=review_date,
                        rating=rating,
                        credibility_score=0.85,  # Fact-check base baseline before source registry ranking
                    )
                )

                if len(candidates) >= max_results:
                    return candidates

        return candidates
