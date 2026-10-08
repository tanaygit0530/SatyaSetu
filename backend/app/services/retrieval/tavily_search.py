import httpx
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.core.logging import logger
from app.schemas.retrieval import CandidateEvidence
from app.services.retrieval.base import WebSearchProvider


class TavilySearchProvider(WebSearchProvider):
    """
    Search provider using Tavily Search API.
    Retrieves web content with rich snippet abstracts and publication dates.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = 8.0,
    ) -> None:
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.api_url = api_url or settings.TAVILY_API_URL
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=15, max_connections=30, keepalive_expiry=30.0)
            self._client = httpx.Client(timeout=self.timeout, limits=limits)
        return self._client

    @property
    def provider_name(self) -> str:
        return "tavily_search"

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        """
        Executes web search via Tavily Search API with connection pooling.
        Gracefully returns empty list if unconfigured or unreachable.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        if not self.api_key:
            logger.info("Tavily API key not configured; skipping Tavily search provider.")
            return []

        payload: Dict[str, Any] = {
            "api_key": self.api_key,
            "query": clean_query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
        }

        try:
            client = self._get_client()
            response = client.post(self.api_url, json=payload)


            if response.status_code == 401 or response.status_code == 403:
                logger.warning("Tavily API authentication failed: HTTP %d", response.status_code)
                return []

            response.raise_for_status()
            data = response.json()
            return self._parse_results(data, max_results=max_results)

        except Exception as e:
            logger.warning("Tavily API request failed gracefully: %s", str(e))
            return []

    def _parse_results(
        self,
        data: Dict[str, Any],
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        """
        Converts Tavily search result entries into CandidateEvidence models.
        """
        candidates: List[CandidateEvidence] = []
        raw_results = data.get("results", [])
        if not raw_results or not isinstance(raw_results, list):
            return []

        for item in raw_results[:max_results]:
            url = item.get("url")
            if not url:
                continue

            try:
                domain = urlparse(url).netloc.lower()
            except Exception:
                domain = "unknown"

            if domain.startswith("www."):
                domain = domain[4:]

            title = item.get("title") or f"Web result: {domain}"
            content = item.get("content") or ""
            published_date = item.get("published_date")
            score = float(item.get("score") or 0.7)

            candidates.append(
                CandidateEvidence(
                    url=url,
                    title=title,
                    snippet=content[:500],
                    publisher=None,  # Will be enriched by SourceRegistryService
                    domain=domain,
                    source_type="SEARCH",
                    publish_date=published_date,
                    credibility_score=score,
                    raw_content=content,
                )
            )

        return candidates
