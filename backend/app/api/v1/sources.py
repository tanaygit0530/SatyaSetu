from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.source import SourceRankResult, SourceRecord
from app.services.source_registry import source_registry_service

router = APIRouter(prefix="/sources", tags=["Source Registry"])


@router.get(
    "",
    response_model=List[SourceRecord],
    status_code=status.HTTP_200_OK,
    summary="List registered authoritative and secondary sources",
    description="Retrieves registered sources from the Source Registry with optional filtering by precedence tier and allowed status.",
)
async def list_sources(
    tier: Optional[int] = Query(None, ge=1, le=3, description="Filter by precedence tier (1, 2, or 3)"),
    allowed: Optional[bool] = Query(None, description="Filter by allowed status (true or false)"),
) -> List[SourceRecord]:
    sources = source_registry_service.list_sources(tier=tier)
    if allowed is not None:
        sources = [s for s in sources if s.allowed is allowed]
    return sources


@router.get(
    "/rank",
    response_model=SourceRankResult,
    status_code=status.HTTP_200_OK,
    summary="Rank domain/URL evidentiary authority",
    description="Evaluates a source domain or URL against the 3-tier registry. Unknown or blacklisted sources return credibility_score=0.0 and allowed=false.",
)
async def rank_source_endpoint(
    domain: str = Query(..., min_length=2, description="Domain name or URL to rank"),
) -> SourceRankResult:
    return source_registry_service.rank_source(domain)


@router.get(
    "/{domain}",
    response_model=SourceRecord,
    status_code=status.HTTP_200_OK,
    summary="Get registered source by domain",
    description="Retrieves a specific source registry record by domain or URL.",
)
async def get_source_endpoint(domain: str) -> SourceRecord:
    source = source_registry_service.get_source(domain)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{domain}' not found in registry",
        )
    return source


@router.post(
    "",
    response_model=SourceRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Register or update source record",
    description="Adds a new source or updates an existing source in the registry.",
)
async def register_source_endpoint(source: SourceRecord) -> SourceRecord:
    return source_registry_service.register_source(source)
