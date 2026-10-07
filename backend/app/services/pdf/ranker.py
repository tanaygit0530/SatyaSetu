from abc import ABC, abstractmethod
import re
from typing import List, Set
from app.schemas.ingestion import PDFPageText

# High-signal policy, statutory, and claim terms common in official circulars & viral claims
CLAIM_KEYWORDS: Set[str] = {
    "scheme", "yojana", "order", "notification", "circular", "gazette", "ministry",
    "department", "government", "cabinet", "pm", "chief", "sanction", "grant",
    "subsidy", "disbursement", "scholarship", "eligibility", "benefit", "deadline",
    "effective", "date", "rupees", "rs", "inr", "crore", "lakh", "amount", "rate",
    "approved", "banned", "suspended", "fake", "clarification", "advisory", "cert",
    "शासकीय", "योजना", "आदेश", "मंत्रालय", "शासन", "निर्णय", "अनुदान",
}


class PageRankingStrategy(ABC):
    """Abstract strategy for prioritizing PDF pages containing actionable factual claims."""

    @abstractmethod
    def rank_pages(self, pages: List[PDFPageText], limit: int = 10) -> List[PDFPageText]:
        """Ranks and scores pages based on evidentiary/claim likelihood."""
        pass


class ClaimBearingPageRanker(PageRankingStrategy):
    """
    Heuristic rule and density-based ranker prioritizing pages with official notices,
    monetary figures, dates, percentages, and statutory claim assertions.
    """

    def rank_pages(self, pages: List[PDFPageText], limit: int = 10) -> List[PDFPageText]:
        if not pages:
            return []

        scored_pages: List[PDFPageText] = []

        for p in pages:
            text_lower = p.text.lower()
            words = set(re.findall(r"\b\w+\b", text_lower))

            # 1. Keyword density score
            matched_keywords = words.intersection(CLAIM_KEYWORDS)
            keyword_score = len(matched_keywords) * 2.5

            # 2. Monetary / Number density score
            currency_matches = len(re.findall(r"[₹$€]|rs\.?|inr", text_lower))
            number_matches = len(re.findall(r"\b\d+([,\.]\d+)?\b", text_lower))
            numeric_score = (currency_matches * 3.0) + min(10.0, number_matches * 0.5)

            # 3. Year / Temporal reference score (e.g. 2024, 2025, 2026, 2027)
            year_matches = len(re.findall(r"\b202[0-9]\b", text_lower))
            temporal_score = year_matches * 2.0

            total_score = round(keyword_score + numeric_score + temporal_score, 2)

            scored_page = PDFPageText(
                page=p.page,
                text=p.text,
                score=total_score,
            )
            scored_pages.append(scored_page)

        # Sort descending by score, maintaining page order for ties
        scored_pages.sort(key=lambda x: (x.score or 0.0), reverse=True)
        return scored_pages[:limit]
