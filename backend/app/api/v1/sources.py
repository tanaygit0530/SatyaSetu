from fastapi import APIRouter
from typing import List
from app.schemas.enums import SourceTier
from pydantic import BaseModel

router = APIRouter(prefix="/sources", tags=["Source Registry"])


class SourceRegistryItem(BaseModel):
    id: str
    name: str
    domain: str
    tier: SourceTier
    category: str
    precedence_rank: int
    status: str
    records_indexed: int


OFFICIAL_REGISTRIES: List[SourceRegistryItem] = [
    SourceRegistryItem(
        id="SRC-01",
        name="The Gazette of India (eGazette)",
        domain="egazette.gov.in",
        tier=SourceTier.TIER_1_PRIMARY,
        category="STATE_GAZETTE",
        precedence_rank=1,
        status="HEALTHY",
        records_indexed=1420500,
    ),
    SourceRegistryItem(
        id="SRC-02",
        name="Press Information Bureau (PIB Fact Check)",
        domain="pib.gov.in",
        tier=SourceTier.TIER_1_PRIMARY,
        category="PIB",
        precedence_rank=2,
        status="HEALTHY",
        records_indexed=89400,
    ),
    SourceRegistryItem(
        id="SRC-03",
        name="National Scholarship Portal (NSP)",
        domain="scholarships.gov.in",
        tier=SourceTier.TIER_1_PRIMARY,
        category="MINISTRY",
        precedence_rank=3,
        status="HEALTHY",
        records_indexed=12400,
    ),
    SourceRegistryItem(
        id="SRC-04",
        name="Ministry of Railways (Railway Board)",
        domain="indianrailways.gov.in",
        tier=SourceTier.TIER_1_PRIMARY,
        category="MINISTRY",
        precedence_rank=4,
        status="HEALTHY",
        records_indexed=284000,
    ),
    SourceRegistryItem(
        id="SRC-05",
        name="Reserve Bank of India (RBI Notifications)",
        domain="rbi.org.in",
        tier=SourceTier.TIER_1_PRIMARY,
        category="STATUTORY_BODY",
        precedence_rank=5,
        status="HEALTHY",
        records_indexed=64200,
    ),
    SourceRegistryItem(
        id="SRC-06",
        name="CERT-In Security Advisories",
        domain="cert-in.org.in",
        tier=SourceTier.TIER_1_PRIMARY,
        category="STATUTORY_BODY",
        precedence_rank=6,
        status="HEALTHY",
        records_indexed=18200,
    ),
]


@router.get("", response_model=List[SourceRegistryItem])
async def list_sources():
    """Lists registered authoritative government and statutory source repositories."""
    return OFFICIAL_REGISTRIES
