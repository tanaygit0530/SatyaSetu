from typing import List, Optional, Union
from pydantic import BaseModel, Field

from app.schemas.claim import AtomicClaim


class ClaimSearchQueries(BaseModel):
    """
    Structured search queries generated for an individual atomic claim:
    1. Original-language query
    2. English query
    3. Entity-focused query
    4. Number/date-aware query
    5. Contradiction query
    """
    claim_id: str = Field(..., description="Unique claim identifier, e.g. 'clm_001'")
    claim_text: str = Field(..., description="Reference claim text")
    original_query: str = Field(..., description="Query formulated in original vernacular language or script")
    english_query: str = Field(..., description="Query formulated with English keywords")
    entity_query: str = Field(..., description="Authority-focused query (e.g. NPCI, RBI, Ministry of Education)")
    number_date_query: str = Field(..., description="Query incorporating numbers, dates, or deadlines")
    contradiction_query: str = Field(..., description="Query searching for official denials, counter-evidence, or PIB Fact Checks")
    all_queries: List[str] = Field(
        default_factory=list,
        description="Deduplicated list of all distinct search queries generated for this claim",
    )


class SearchQueryGenerationOutput(BaseModel):
    """
    Container for search query generation results.
    Strictly generated without web browsing, returned as structured JSON.
    """
    claim_queries: List[ClaimSearchQueries] = Field(
        default_factory=list,
        description="Search queries mapped per claim",
    )
    total_unique_queries: int = Field(
        default=0,
        description="Total deduplicated unique queries across all claims in the set",
    )


class QueryGenerationInput(BaseModel):
    """Input payload for evidence search query generation."""
    claims: Optional[List[AtomicClaim]] = Field(
        default=None,
        description="Optional list of structured atomic claims",
    )
    claim_text: Optional[str] = Field(
        default=None,
        description="Optional single claim text if submitting a single claim directly",
    )
    claim_id: Optional[str] = Field(
        default="clm_001",
        description="Claim identifier if submitting single text",
    )
