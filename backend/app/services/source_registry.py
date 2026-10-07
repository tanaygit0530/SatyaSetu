import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from app.core.logging import logger
from app.schemas.source import SourceRankResult, SourceRecord, SourceTierLevel


class SourceRegistryService:
    """
    Authoritative Source Registry Service.

    Maintains source precedence tiers:
    - Tier 1: Official government sources, official agencies, official organizations.
    - Tier 2: Reputable fact-checking organizations, high-quality established news sources.
    - Tier 3: Other useful sources.

    Crucial Guarantee:
    Unknown/untrusted sources must not automatically become strong evidence.
    Source trust logic is fully encapsulated here and NOT hardcoded inside the verdict engine.
    """

    # Official statutory apex / second-level domains managed strictly by government
    GOVERNMENT_TLD_PATTERNS = (
        ".gov.in",
        ".nic.in",
        ".mil.in",
        ".judiciary.gov.in",
    )

    def __init__(self, repository: Optional[Any] = None) -> None:
        self.repository = repository
        self._registry: Dict[str, SourceRecord] = {}
        self._seed_authoritative_sources()

    @staticmethod
    def normalize_domain(domain_or_url: str) -> str:
        """
        Normalizes any domain, hostname, or full URL to a clean lowercase canonical domain.
        Handles schemas, ports, paths, query params, and leading 'www.'.
        """
        if not domain_or_url:
            return ""

        raw = str(domain_or_url).strip().lower()

        # If it looks like a URL with scheme, parse with urlparse
        if "://" in raw:
            try:
                parsed = urlparse(raw)
                host = parsed.netloc or parsed.path
            except Exception:
                host = raw.split("://", 1)[1]
        else:
            host = raw

        # Strip path, parameters, fragments if leftover
        host = host.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]

        # Strip port if present
        if ":" in host:
            host = host.split(":", 1)[0]

        # Strip leading 'www.'
        if host.startswith("www."):
            host = host[4:]

        return host.strip(".")

    def _seed_authoritative_sources(self) -> None:
        """
        Seeds the in-memory registry with verified Indian and international sources.
        """
        seed_data: List[Dict[str, Any]] = [
            # Specification Example
            {
                "domain": "example.gov.in",
                "publisher": "Example Government Department",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Official government gazette and department portal",
                "country": "IN",
                "language": "all",
            },
            # ==================================================================
            # TIER 1: Official Government Sources, Official Agencies & Regulators
            # ==================================================================
            {
                "domain": "egazette.gov.in",
                "publisher": "The Gazette of India (eGazette)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Directorate of Printing, official statutory gazette",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "pib.gov.in",
                "publisher": "Press Information Bureau (PIB)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Government of India official press bureau & PIB Fact Check",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "scholarships.gov.in",
                "publisher": "National Scholarship Portal (NSP)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Ministry of Electronics & IT, DBT scholarship registry",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "indianrailways.gov.in",
                "publisher": "Ministry of Railways (Railway Board)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Official notices and operational railway circulars",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "rbi.org.in",
                "publisher": "Reserve Bank of India (RBI)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Central Bank notifications and statutory monetary directives",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "cert-in.org.in",
                "publisher": "Indian Computer Emergency Response Team (CERT-In)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "National nodal cyber security agency and vulnerability alerts",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "uidai.gov.in",
                "publisher": "Unique Identification Authority of India (UIDAI)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Statutory authority for Aadhaar",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "incometax.gov.in",
                "publisher": "Income Tax Department (CBDT)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Central Board of Direct Taxes official portal",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "eci.gov.in",
                "publisher": "Election Commission of India (ECI)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Constitutional election authority circulars",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "sci.gov.in",
                "publisher": "Supreme Court of India",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Apex judicial rulings and daily orders",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "supremecourtofindia.nic.in",
                "publisher": "Supreme Court of India (NIC Portal)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Supreme Court order repository",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "npci.org.in",
                "publisher": "National Payments Corporation of India (NPCI)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Statutory umbrella organization for retail payments (UPI, IMPS, RuPay)",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "cbse.gov.in",
                "publisher": "Central Board of Secondary Education (CBSE)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Official board exam datesheets and notifications",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "nta.ac.in",
                "publisher": "National Testing Agency (NTA)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Statutory premier testing agency (JEE, NEET, UGC-NET)",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "ugc.ac.in",
                "publisher": "University Grants Commission (UGC)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Statutory university higher education regulator",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "sebi.gov.in",
                "publisher": "Securities and Exchange Board of India (SEBI)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Statutory securities market regulator",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "upsc.gov.in",
                "publisher": "Union Public Service Commission (UPSC)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Constitutional recruiting commission notifications",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "mohfw.gov.in",
                "publisher": "Ministry of Health and Family Welfare (MoHFW)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Health advisories and clinical protocols",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "mha.gov.in",
                "publisher": "Ministry of Home Affairs (MHA)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Internal security directives and statutory gazettes",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "who.int",
                "publisher": "World Health Organization (WHO)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Official United Nations global public health body",
                "country": "INT",
                "language": "all",
            },
            {
                "domain": "un.org",
                "publisher": "United Nations (UN)",
                "tier": SourceTierLevel.TIER_1_OFFICIAL,
                "allowed": True,
                "notes": "Official international multilateral agency",
                "country": "INT",
                "language": "all",
            },
            # ==================================================================
            # TIER 2: Reputable Fact-Checking Organizations & High-Quality News
            # ==================================================================
            # IFCN Certified Fact Checkers
            {
                "domain": "altnews.in",
                "publisher": "Alt News",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "IFCN signatory fact-checking organization",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "boomlive.in",
                "publisher": "BOOM Live",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "IFCN signatory fact-checking newsroom",
                "country": "IN",
                "language": "en,hi,bn",
            },
            {
                "domain": "thequint.com",
                "publisher": "The Quint (WebQoof)",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "IFCN signatory fact-check desk",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "vishvasnews.com",
                "publisher": "Vishvas News",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "IFCN signatory vernacular fact-checker",
                "country": "IN",
                "language": "hi,en,mr",
            },
            {
                "domain": "factly.in",
                "publisher": "Factly",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "IFCN signatory public data fact-checker",
                "country": "IN",
                "language": "en,te",
            },
            {
                "domain": "newschecker.in",
                "publisher": "Newschecker",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "IFCN signatory multilingual fact-checking portal",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "thip.media",
                "publisher": "The Healthy Indian Project (THIP)",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "IFCN signatory specialized health fact-checker",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "snopes.com",
                "publisher": "Snopes",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Established independent fact-checking archive",
                "country": "US",
                "language": "en",
            },
            {
                "domain": "politifact.com",
                "publisher": "PolitiFact",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Pulitzer Prize-winning fact-checking organization",
                "country": "US",
                "language": "en",
            },
            # Established High-Quality News Sources
            {
                "domain": "thehindu.com",
                "publisher": "The Hindu",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Established national record newspaper",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "indianexpress.com",
                "publisher": "The Indian Express",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Established national investigative daily",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "reuters.com",
                "publisher": "Reuters",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Global wire news agency",
                "country": "INT",
                "language": "en",
            },
            {
                "domain": "apnews.com",
                "publisher": "Associated Press (AP)",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Global cooperative news agency",
                "country": "INT",
                "language": "en",
            },
            {
                "domain": "bbc.com",
                "publisher": "BBC News",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Public service international broadcaster",
                "country": "GB",
                "language": "en,hi,mr",
            },
            {
                "domain": "bbc.co.uk",
                "publisher": "BBC",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "BBC core domain",
                "country": "GB",
                "language": "en",
            },
            {
                "domain": "ndtv.com",
                "publisher": "NDTV",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "National broadcast and digital network",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "hindustantimes.com",
                "publisher": "Hindustan Times",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "National English newspaper of record",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "indiatimes.com",
                "publisher": "Times of India Network",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "National media conglomerate",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "livemint.com",
                "publisher": "Mint",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Financial and public policy daily",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "business-standard.com",
                "publisher": "Business Standard",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Financial daily newspaper",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "theprint.in",
                "publisher": "ThePrint",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Digital policy and investigative newsroom",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "pti.in",
                "publisher": "Press Trust of India (PTI)",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "India's premier news wire agency",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "aniin.com",
                "publisher": "Asian News International (ANI)",
                "tier": SourceTierLevel.TIER_2_REPUTABLE,
                "allowed": True,
                "notes": "Broadcast news service agency",
                "country": "IN",
                "language": "en,hi",
            },
            # ==================================================================
            # TIER 3: Other Useful Sources
            # ==================================================================
            {
                "domain": "wikipedia.org",
                "publisher": "Wikipedia",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Community encyclopedia, useful secondary overview",
                "country": "INT",
                "language": "all",
            },
            {
                "domain": "scroll.in",
                "publisher": "Scroll.in",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Digital commentary and independent reporting",
                "country": "IN",
                "language": "en,hi",
            },
            {
                "domain": "thewire.in",
                "publisher": "The Wire",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Independent digital journalism portal",
                "country": "IN",
                "language": "en,hi,mr",
            },
            {
                "domain": "firstpost.com",
                "publisher": "Firstpost",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "News and commentary portal",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "news18.com",
                "publisher": "News18",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Regional broadcast and digital news",
                "country": "IN",
                "language": "all",
            },
            {
                "domain": "esakal.com",
                "publisher": "Sakal Media",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Regional Marathi daily newspaper",
                "country": "IN",
                "language": "mr",
            },
            {
                "domain": "lokmat.com",
                "publisher": "Lokmat",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Regional Marathi newspaper",
                "country": "IN",
                "language": "mr",
            },
            {
                "domain": "amarujala.com",
                "publisher": "Amar Ujala",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Regional Hindi daily newspaper",
                "country": "IN",
                "language": "hi",
            },
            {
                "domain": "jagran.com",
                "publisher": "Dainik Jagran",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": True,
                "notes": "Regional Hindi daily newspaper",
                "country": "IN",
                "language": "hi",
            },
            # ==================================================================
            # EXPLICITLY DISALLOWED / BLACKLISTED SOURCES (Security Blacklist)
            # ==================================================================
            {
                "domain": "pmssy-gov.in",
                "publisher": "Blacklisted Phishing Portal",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": False,
                "notes": "Blacklisted by CERT-In: Credential-harvesting scam impersonating PMSSY",
                "country": "IN",
                "language": "en",
            },
            {
                "domain": "free-recharge-offer.online",
                "publisher": "Fraudulent Link",
                "tier": SourceTierLevel.TIER_3_USEFUL,
                "allowed": False,
                "notes": "Viral WhatsApp phishing and lottery scam",
                "country": "IN",
                "language": "all",
            },
        ]

        for s in seed_data:
            record = SourceRecord(**s)
            self._registry[record.domain] = record

    def register_source(self, source: Union[SourceRecord, Dict[str, Any]]) -> SourceRecord:
        """
        Registers or updates a source in the registry.
        """
        record = source if isinstance(source, SourceRecord) else SourceRecord(**source)
        self._registry[record.domain] = record
        logger.info("Source registered: %s (Tier %d, allowed=%s)", record.domain, record.tier, record.allowed)
        return record

    def block_source(self, domain_or_url: str, notes: Optional[str] = None) -> Optional[SourceRecord]:
        """
        Explicitly marks a domain as disallowed / blacklisted.
        """
        norm_domain = self.normalize_domain(domain_or_url)
        existing = self.get_source(norm_domain)
        if existing:
            updated = existing.model_copy(update={
                "allowed": False,
                "notes": notes or existing.notes or "Blocked by administrative advisory",
            })
            self._registry[norm_domain] = updated
            return updated

        # Create new blocked record
        blocked = SourceRecord(
            domain=norm_domain,
            publisher=f"Blocked Domain ({norm_domain})",
            tier=SourceTierLevel.TIER_3_USEFUL,
            allowed=False,
            notes=notes or "Untrusted / Blocked domain",
        )
        self._registry[norm_domain] = blocked
        return blocked

    def get_source(self, domain_or_url: str) -> Optional[SourceRecord]:
        """
        Retrieves a registered SourceRecord for a given domain or URL.

        Resolution Strategy:
        1. Exact match in registry.
        2. Subdomain match (e.g. 'press.pib.gov.in' resolves to 'pib.gov.in').
        3. Dynamic official government domain recognition (*.gov.in, *.nic.in)
           unless explicitly registered or blocked.
        4. Returns None if domain is unknown / untrusted.
        """
        domain = self.normalize_domain(domain_or_url)
        if not domain:
            return None

        # 1. Exact match
        if domain in self._registry:
            return self._registry[domain]

        # 2. Check for parent registered subdomain
        parts = domain.split(".")
        if len(parts) > 2:
            for i in range(1, len(parts) - 1):
                parent_domain = ".".join(parts[i:])
                if parent_domain in self._registry:
                    parent_record = self._registry[parent_domain]
                    return parent_record

        # 3. Dynamic Statutory Government TLD Recognition
        # Government TLDs (.gov.in, .nic.in, .mil.in) in India are strictly restricted
        # and allocated exclusively to official Government ministries and agencies.
        if any(domain.endswith(pat) for pat in self.GOVERNMENT_TLD_PATTERNS):
            dynamic_gov_source = SourceRecord(
                domain=domain,
                publisher=f"Government of India ({domain})",
                tier=SourceTierLevel.TIER_1_OFFICIAL,
                allowed=True,
                notes="Statutory official government portal resolved via sovereign government registry.",
                country="IN",
                language="all",
            )
            return dynamic_gov_source

        # 4. Unknown / untrusted source
        return None

    def get_tier(self, domain_or_url: str) -> Optional[int]:
        """
        Returns the integer precedence tier (1, 2, or 3) of the source,
        or None if the source is unknown, untrusted, or disallowed.
        """
        source = self.get_source(domain_or_url)
        if source is None:
            return None
        if not source.allowed:
            return None
        return source.tier

    def is_allowed(self, domain_or_url: str) -> bool:
        """
        Determines whether a source is authorized for evidentiary citation.
        Unknown or explicitly blocked sources return False.
        """
        source = self.get_source(domain_or_url)
        if source is None:
            return False
        return bool(source.allowed)

    def rank_source(self, domain_or_url: str) -> SourceRankResult:
        """
        Evaluates and ranks a domain/URL based on the registry's strict tier precedence.

        Enforces that unknown / untrusted sources do NOT automatically become strong evidence:
        - Tier 1: credibility_score = 1.0, is_authoritative = True,  evidence_strength = STRONG
        - Tier 2: credibility_score = 0.8, is_authoritative = False, evidence_strength = MODERATE
        - Tier 3: credibility_score = 0.5, is_authoritative = False, evidence_strength = WEAK
        - Unknown or Disallowed: credibility_score = 0.0, allowed = False, evidence_strength = UNTRUSTED
        """
        domain = self.normalize_domain(domain_or_url)
        source = self.get_source(domain)

        # Case 1: Known registered source
        if source is not None:
            if not source.allowed:
                return SourceRankResult(
                    domain=domain,
                    publisher=source.publisher,
                    tier=source.tier,
                    allowed=False,
                    is_trusted=False,
                    is_authoritative=False,
                    credibility_score=0.0,
                    evidence_strength="UNTRUSTED",
                    tier_description=f"Disallowed / Blacklisted source ({source.notes or 'Untrusted'})",
                    notes=source.notes,
                )

            if source.tier == SourceTierLevel.TIER_1_OFFICIAL:
                return SourceRankResult(
                    domain=domain,
                    publisher=source.publisher,
                    tier=1,
                    allowed=True,
                    is_trusted=True,
                    is_authoritative=True,
                    credibility_score=1.0,
                    evidence_strength="STRONG",
                    tier_description="Tier 1: Official government source, official agency, or official organization",
                    notes=source.notes,
                )
            elif source.tier == SourceTierLevel.TIER_2_REPUTABLE:
                return SourceRankResult(
                    domain=domain,
                    publisher=source.publisher,
                    tier=2,
                    allowed=True,
                    is_trusted=True,
                    is_authoritative=False,
                    credibility_score=0.8,
                    evidence_strength="MODERATE",
                    tier_description="Tier 2: Reputable fact-checking organization or high-quality established news source",
                    notes=source.notes,
                )
            else:  # Tier 3
                return SourceRankResult(
                    domain=domain,
                    publisher=source.publisher,
                    tier=3,
                    allowed=True,
                    is_trusted=True,
                    is_authoritative=False,
                    credibility_score=0.5,
                    evidence_strength="WEAK",
                    tier_description="Tier 3: Other useful secondary source",
                    notes=source.notes,
                )

        # Case 2: Unknown / Untrusted source
        return SourceRankResult(
            domain=domain,
            publisher="Unknown / Unregistered Publisher",
            tier=None,
            allowed=False,
            is_trusted=False,
            is_authoritative=False,
            credibility_score=0.0,
            evidence_strength="UNTRUSTED",
            tier_description="Unknown / Untrusted source (not verified in authoritative registry)",
            notes="Unknown or unverified domain. Cannot be used as strong evidentiary support.",
        )

    def list_sources(
        self,
        tier: Optional[int] = None,
        allowed_only: bool = False,
    ) -> List[SourceRecord]:
        """
        Lists all registered sources, optionally filtered by tier and allowed status.
        """
        results = list(self._registry.values())
        if tier is not None:
            results = [s for s in results if s.tier == tier]
        if allowed_only:
            results = [s for s in results if s.allowed is True]
        return results


# Default singleton instance
source_registry_service = SourceRegistryService()
