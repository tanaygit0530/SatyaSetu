import pytest
import httpx
from app.main import app
from app.schemas.enums import SourceTier, Verdict
from app.schemas.claim import ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceInterpretation
from app.schemas.source import SourceRecord, SourceTierLevel
from app.services.source_registry import SourceRegistryService, source_registry_service
from app.services.rule_engine import DeterministicRuleEngine


def test_specification_example_source():
    """
    Validates the specification example:
    {
      "domain": "example.gov.in",
      "publisher": "Example Government Department",
      "tier": 1,
      "allowed": true
    }
    """
    source = source_registry_service.get_source("example.gov.in")
    assert source is not None
    assert source.domain == "example.gov.in"
    assert source.publisher == "Example Government Department"
    assert source.tier == 1
    assert source.allowed is True

    tier = source_registry_service.get_tier("example.gov.in")
    assert tier == 1

    allowed = source_registry_service.is_allowed("example.gov.in")
    assert allowed is True

    rank = source_registry_service.rank_source("example.gov.in")
    assert rank.tier == 1
    assert rank.is_authoritative is True
    assert rank.credibility_score == 1.0
    assert rank.evidence_strength == "STRONG"


def test_tier_1_official_government_sources():
    """
    Tier 1: official government sources, official agencies, official organizations.
    Must have tier=1, allowed=True, is_authoritative=True, credibility_score=1.0.
    """
    tier1_domains = [
        ("egazette.gov.in", "The Gazette of India (eGazette)"),
        ("pib.gov.in", "Press Information Bureau (PIB)"),
        ("scholarships.gov.in", "National Scholarship Portal (NSP)"),
        ("indianrailways.gov.in", "Ministry of Railways (Railway Board)"),
        ("rbi.org.in", "Reserve Bank of India (RBI)"),
        ("cert-in.org.in", "Indian Computer Emergency Response Team (CERT-In)"),
        ("npci.org.in", "National Payments Corporation of India (NPCI)"),
        ("who.int", "World Health Organization (WHO)"),
    ]

    for domain, expected_publisher in tier1_domains:
        source = source_registry_service.get_source(domain)
        assert source is not None, f"Expected {domain} to be registered"
        assert source.tier == 1
        assert source.allowed is True
        assert source_registry_service.get_tier(domain) == 1
        assert source_registry_service.is_allowed(domain) is True

        rank = source_registry_service.rank_source(domain)
        assert rank.tier == 1
        assert rank.is_authoritative is True
        assert rank.credibility_score == 1.0
        assert rank.evidence_strength == "STRONG"


def test_dynamic_sovereign_government_domain_resolution():
    """
    Apex .gov.in and .nic.in domains are strictly issued to government ministries.
    Unlisted valid government portals should dynamically resolve to Tier 1 official sources.
    """
    unlisted_gov = "delhipolice.gov.in"
    unlisted_nic = "highcourt.nic.in"

    assert source_registry_service.get_tier(unlisted_gov) == 1
    assert source_registry_service.is_allowed(unlisted_gov) is True

    rank = source_registry_service.rank_source(unlisted_nic)
    assert rank.tier == 1
    assert rank.is_authoritative is True
    assert rank.evidence_strength == "STRONG"


def test_tier_2_reputable_fact_checkers_and_established_news():
    """
    Tier 2: reputable fact-checking organizations, high-quality established news sources.
    Must have tier=2, allowed=True, is_authoritative=False, credibility_score=0.8.
    """
    tier2_domains = [
        "altnews.in",
        "boomlive.in",
        "thequint.com",
        "vishvasnews.com",
        "thehindu.com",
        "indianexpress.com",
        "reuters.com",
        "bbc.com",
    ]

    for domain in tier2_domains:
        source = source_registry_service.get_source(domain)
        assert source is not None, f"Expected {domain} in registry"
        assert source.tier == 2
        assert source.allowed is True
        assert source_registry_service.get_tier(domain) == 2
        assert source_registry_service.is_allowed(domain) is True

        rank = source_registry_service.rank_source(domain)
        assert rank.tier == 2
        assert rank.is_authoritative is False
        assert rank.is_trusted is True
        assert rank.credibility_score == 0.8
        assert rank.evidence_strength == "MODERATE"


def test_tier_3_other_useful_sources():
    """
    Tier 3: other useful sources.
    Must have tier=3, allowed=True, is_authoritative=False, credibility_score=0.5.
    """
    tier3_domains = [
        "wikipedia.org",
        "scroll.in",
        "lokmat.com",
        "esakal.com",
    ]

    for domain in tier3_domains:
        source = source_registry_service.get_source(domain)
        assert source is not None, f"Expected {domain} in registry"
        assert source.tier == 3
        assert source.allowed is True
        assert source_registry_service.get_tier(domain) == 3
        assert source_registry_service.is_allowed(domain) is True

        rank = source_registry_service.rank_source(domain)
        assert rank.tier == 3
        assert rank.is_authoritative is False
        assert rank.credibility_score == 0.5
        assert rank.evidence_strength == "WEAK"


def test_unknown_and_untrusted_sources_cannot_become_strong_evidence():
    """
    CRITICAL REQUIREMENT:
    Unknown/untrusted sources must NOT automatically become strong evidence.
    """
    untrusted_domains = [
        "random-unverified-blog.xyz",
        "viral-whatsapp-leak.co",
        "fake-news-portal.info",
        "unknown-conspiracy.org",
    ]

    for domain in untrusted_domains:
        assert source_registry_service.get_source(domain) is None
        assert source_registry_service.get_tier(domain) is None
        assert source_registry_service.is_allowed(domain) is False

        rank = source_registry_service.rank_source(domain)
        assert rank.tier is None
        assert rank.allowed is False
        assert rank.is_trusted is False
        assert rank.is_authoritative is False
        assert rank.credibility_score == 0.0
        assert rank.evidence_strength == "UNTRUSTED"


def test_blacklisted_and_disallowed_sources():
    """
    Known phishing or malicious links are marked allowed=False.
    Must return credibility_score=0.0 and allowed=False.
    """
    assert source_registry_service.is_allowed("pmssy-gov.in") is False
    assert source_registry_service.get_tier("pmssy-gov.in") is None

    rank = source_registry_service.rank_source("pmssy-gov.in")
    assert rank.allowed is False
    assert rank.is_trusted is False
    assert rank.credibility_score == 0.0
    assert rank.evidence_strength == "UNTRUSTED"


def test_url_and_subdomain_normalization():
    """
    Ensures URLs with schemes, paths, queries, ports, and subdomains are normalized.
    """
    # Full URL
    tier_from_url = source_registry_service.get_tier("https://pib.gov.in/PressReleasePage.aspx?PRID=205128")
    assert tier_from_url == 1

    # Mixed uppercase with www and trailing path
    tier_from_www = source_registry_service.get_tier("HTTP://WWW.EGAZETTE.GOV.IN/circ/2026/moe-14")
    assert tier_from_www == 1

    # Subdomain resolution (e.g. press.pib.gov.in -> pib.gov.in)
    rank_subdomain = source_registry_service.rank_source("press.pib.gov.in")
    assert rank_subdomain.tier == 1
    assert rank_subdomain.publisher == "Press Information Bureau (PIB)"


def test_register_and_block_source_methods():
    """
    Tests dynamic registration and blocking methods on SourceRegistryService.
    """
    service = SourceRegistryService()

    # Register new Tier 2 source
    service.register_source(
        SourceRecord(
            domain="custom-factcheck.org",
            publisher="Custom Fact Check Lab",
            tier=SourceTierLevel.TIER_2_REPUTABLE,
            allowed=True,
            notes="Accredited fact-checking network",
        )
    )
    assert service.get_tier("custom-factcheck.org") == 2
    assert service.is_allowed("custom-factcheck.org") is True

    # Block an existing source
    service.block_source("custom-factcheck.org", notes="Revoked accreditation")
    assert service.is_allowed("custom-factcheck.org") is False
    assert service.get_tier("custom-factcheck.org") is None


def test_verdict_engine_rejects_untrusted_source_spoofing():
    """
    CRITICAL REQUIREMENT:
    Do not hardcode source trust logic inside the verdict engine.
    Ensures that an EvidenceItem claiming Tier 1 with an untrusted domain CANNOT verify a claim.
    """
    claim = ExtractedClaim(
        claim_number=1,
        claim_text="Government declared public holiday tomorrow.",
        language="en",
    )
    # Malicious attempt to spoof Tier-1 citation with an untrusted blog
    spoofed_evidence = [
        EvidenceItem(
            id="CIT-FAKE-01",
            publisher="Fake News Portal",
            domain="fake-untrusted-blog.xyz",
            title="Notification Tomorrow Holiday",
            publish_date="2026-10-07",
            tier=SourceTier.TIER_1_PRIMARY,  # Spoofed claim of Tier 1
            url="https://fake-untrusted-blog.xyz/news",
            exact_quote="Government declared holiday tomorrow.",
            confidence_score=0.99,
        )
    ]
    interpretation = EvidenceInterpretation(
        supports_claim=True,
        refutes_claim=False,
    )

    # Verdict engine must query SourceRegistryService and REJECT the spoofed evidence
    result = DeterministicRuleEngine.evaluate_claim(claim, spoofed_evidence, interpretation)
    # Since the source is untrusted, it cannot be verified under RULE-OFFICIAL-GAZETTE-CORROBORATION
    assert result.verdict != Verdict.VERIFIED
    assert result.rule_matched != "RULE-OFFICIAL-GAZETTE-CORROBORATION"


@pytest.mark.asyncio
async def test_fastapi_source_registry_endpoints():
    """
    Tests the FastAPI routes for the Source Registry:
    - GET /api/v1/sources
    - GET /api/v1/sources?tier=1
    - GET /api/v1/sources/rank?domain=...
    - GET /api/v1/sources/{domain}
    - POST /api/v1/sources
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. List all sources
        res = await client.get("/api/v1/sources")
        assert res.status_code == 200
        all_sources = res.json()
        assert len(all_sources) >= 20

        # 2. Filter by tier=1
        res_t1 = await client.get("/api/v1/sources?tier=1")
        assert res_t1.status_code == 200
        t1_sources = res_t1.json()
        assert all(s["tier"] == 1 for s in t1_sources)

        # 3. Rank known domain
        res_rank = await client.get("/api/v1/sources/rank?domain=pib.gov.in")
        assert res_rank.status_code == 200
        rank_data = res_rank.json()
        assert rank_data["tier"] == 1
        assert rank_data["is_authoritative"] is True
        assert rank_data["credibility_score"] == 1.0

        # 4. Rank untrusted domain
        res_rank_untrusted = await client.get("/api/v1/sources/rank?domain=random-unverified.com")
        assert res_rank_untrusted.status_code == 200
        untrusted_data = res_rank_untrusted.json()
        assert untrusted_data["tier"] is None
        assert untrusted_data["allowed"] is False
        assert untrusted_data["credibility_score"] == 0.0

        # 5. Get source by domain
        res_get = await client.get("/api/v1/sources/example.gov.in")
        assert res_get.status_code == 200
        source_data = res_get.json()
        assert source_data["domain"] == "example.gov.in"
        assert source_data["tier"] == 1

        # 6. Post new source
        new_source = {
            "domain": "test-registry-new.gov.in",
            "publisher": "Test New Ministry Portal",
            "tier": 1,
            "allowed": True,
            "notes": "Newly verified statutory agency",
        }
        res_post = await client.post("/api/v1/sources", json=new_source)
        assert res_post.status_code == 201
        created = res_post.json()
        assert created["domain"] == "test-registry-new.gov.in"
        assert created["tier"] == 1
