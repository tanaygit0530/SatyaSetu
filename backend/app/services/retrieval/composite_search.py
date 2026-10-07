import httpx
from typing import List, Optional
from urllib.parse import quote_plus, urlparse

from app.core.logging import logger
from app.schemas.retrieval import CandidateEvidence
from app.services.retrieval.base import WebSearchProvider
from app.services.retrieval.tavily_search import TavilySearchProvider


class DuckDuckGoSearchProvider(WebSearchProvider):
    """
    Keyless fallback search provider querying DuckDuckGo instant answer and related topic links.
    Ensures search capabilities even when commercial API keys are unavailable.
    """

    def __init__(self, timeout: float = 6.0) -> None:
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "duckduckgo_search"

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        clean_query = query.strip()
        if not clean_query:
            return []

        candidates: List[CandidateEvidence] = []
        try:
            url = f"https://api.duckduckgo.com/?q={quote_plus(clean_query)}&format=json&no_html=1&skip_disambig=1"
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)

            if resp.status_code == 200:
                data = resp.json()
                # 1. Primary abstract
                abstract_url = data.get("AbstractURL")
                abstract_text = data.get("AbstractText")
                abstract_source = data.get("AbstractSource")
                if abstract_url and abstract_text:
                    domain = urlparse(abstract_url).netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    candidates.append(
                        CandidateEvidence(
                            url=abstract_url,
                            title=f"{abstract_source or 'Instant Answer'}: {clean_query[:50]}",
                            snippet=abstract_text[:400],
                            publisher=abstract_source,
                            domain=domain,
                            source_type="SEARCH",
                            credibility_score=0.7,
                        )
                    )

                # 2. Related topics
                for topic in data.get("RelatedTopics", []):
                    if len(candidates) >= max_results:
                        break
                    topic_url = topic.get("FirstURL")
                    topic_text = topic.get("Text")
                    if topic_url and topic_text:
                        domain = urlparse(topic_url).netloc.lower()
                        if domain.startswith("www."):
                            domain = domain[4:]
                        candidates.append(
                            CandidateEvidence(
                                url=topic_url,
                                title=topic_text[:80],
                                snippet=topic_text[:300],
                                publisher=None,
                                domain=domain,
                                source_type="SEARCH",
                                credibility_score=0.6,
                            )
                        )
        except Exception as e:
            logger.info("DuckDuckGo search provider fallback skipped: %s", str(e))

        return candidates[:max_results]


class CompositeWebSearchProvider(WebSearchProvider):
    """
    Composite search provider that cascades through configured search providers:
    1. Primary provider (e.g. TavilySearchProvider)
    2. Fallback provider (e.g. DuckDuckGoSearchProvider or configured fallback)

    CRITICAL ARCHITECTURAL GUARANTEE:
    Do not make the entire system depend on one provider.
    """

    def __init__(
        self,
        providers: Optional[List[WebSearchProvider]] = None,
    ) -> None:
        if providers:
            self.providers = providers
        else:
            self.providers = [
                TavilySearchProvider(),
                DuckDuckGoSearchProvider(),
            ]

    @property
    def provider_name(self) -> str:
        return "composite_web_search"

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        """
        Executes query through available providers in order of precedence.
        Returns first successful non-empty candidate list, or combines candidates if needed.
        """
        all_candidates: List[CandidateEvidence] = []
        for provider in self.providers:
            try:
                results = provider.search(query=query, max_results=max_results)
                if results:
                    logger.info(
                        "Search provider '%s' returned %d results for query '%s'",
                        provider.provider_name,
                        len(results),
                        query[:40],
                    )
                    all_candidates.extend(results)
                    if len(all_candidates) >= max_results:
                        return all_candidates[:max_results]
            except Exception as e:
                logger.warning(
                    "Search provider '%s' encountered error: %s; falling back to next provider.",
                    provider.provider_name,
                    str(e),
                )
                continue

        return all_candidates[:max_results]
