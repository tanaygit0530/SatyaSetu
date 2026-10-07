from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.retrieval import CandidateEvidence


class FactCheckProvider(ABC):
    """
    Abstract interface for professional fact-checking registry search providers
    (e.g. Google Fact Check Tools API, ClaimReview aggregators).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier for the fact check provider."""
        pass

    @abstractmethod
    def search_claims(
        self,
        query: str,
        language_code: Optional[str] = None,
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        """
        Queries verified fact-checking records for debunks or reviews matching the query.
        Returns a list of structured CandidateEvidence objects.
        """
        pass


class WebSearchProvider(ABC):
    """
    Abstract interface for web and documentary search providers
    (e.g. Tavily, DuckDuckGo, sovereign portal indexers).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier for the search provider."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CandidateEvidence]:
        """
        Performs web search across official, news, and authoritative domains.
        Returns a list of structured CandidateEvidence objects.
        """
        pass
