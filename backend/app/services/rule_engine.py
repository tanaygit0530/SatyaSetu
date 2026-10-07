from typing import Dict, List, Optional, Tuple
from app.schemas.enums import SourceTier, TemporalStatus, Verdict
from app.schemas.claim import ClaimResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceInterpretation
from app.services.source_registry import source_registry_service
from app.services.evidence_locking import evidence_locking_service
from app.core.logging import logger


class DeterministicRuleEngine:
    """
    Deterministic Verdict Engine for SachCheck.

    CRITICAL ARCHITECTURAL GUARANTEE:
    This pure-code deterministic engine computes the final verdict based on
    strict statutory evidence rules, source tiers, temporal thresholds, and
    logical contradictions. The LLM is never allowed to dictate verdicts.
    """

    @staticmethod
    def evaluate_claim(
        claim: ExtractedClaim,
        evidence_list: List[EvidenceItem],
        interpretation: EvidenceInterpretation,
        source_texts: Optional[Dict[str, str]] = None,
    ) -> ClaimResult:
        """
        Determines the verdict for a single atomic claim using pure deterministic rules.
        Runs Evidence Locking validation BEFORE verdict calculation.
        """
        claim_id = f"CLM-{claim.claim_number}"

        # 0. Evidence Locking Grounding Check (Runs BEFORE verdict calculation)
        if source_texts:
            grounded_evidence, rejected = evidence_locking_service.validate_and_filter_evidence(
                evidence_list, source_texts
            )
            evidence_list = grounded_evidence
            if rejected and not evidence_list:
                logger.warning("All evidence citations failed grounding validation [QUOTE_NOT_FOUND].")
                return ClaimResult(
                    id=claim_id,
                    claim_number=claim.claim_number,
                    claim_text=claim.claim_text,
                    original_language_text=claim.original_language_text,
                    language=claim.language,
                    verdict=Verdict.CANNOT_BE_CONFIRMED,
                    confidence=0.0,
                    summary="Evidence citation rejected: exact quote was not found in stored source text.",
                    detailed_analysis="Evidence Locking System rejected citations under strict anti-fabrication policy.",
                    temporal_status=TemporalStatus.UNDATED,
                    rule_matched="RULE-EVIDENCE-LOCKING-REJECTED",
                    source_citations=[],
                )

        # 1. Check for malicious/phishing domain or security alert
        if interpretation.domain_flagged_malicious:
            logger.info("Rule match: RULE-MALICIOUS-PHISHING-URL on claim %d", claim.claim_number)
            return ClaimResult(
                id=claim_id,
                claim_number=claim.claim_number,
                claim_text=claim.claim_text,
                original_language_text=claim.original_language_text,
                language=claim.language,
                verdict=Verdict.FALSE,
                confidence=100.0,
                summary="Malicious phishing or fraudulent link. Blacklisted by cybersecurity advisory.",
                detailed_analysis=(
                    interpretation.discrepancy_explanation
                    or "Domain records confirm unauthorized third-party phishing site masquerading as official portal."
                ),
                temporal_status=TemporalStatus.CURRENT,
                rule_matched="RULE-MALICIOUS-PHISHING-URL",
                counter_evidence_summary="Flagged phishing domain; genuine portal is scholarships.gov.in / nic.in",
                source_citations=evidence_list,
            )

        # 2. Check for Temporal Recirculation / Outdated Notice
        if interpretation.is_temporal_mismatch:
            logger.info("Rule match: RULE-TEMPORAL-RECIRCULATION on claim %d", claim.claim_number)
            return ClaimResult(
                id=claim_id,
                claim_number=claim.claim_number,
                claim_text=claim.claim_text,
                original_language_text=claim.original_language_text,
                language=claim.language,
                verdict=Verdict.OUTDATED,
                confidence=96.5,
                summary="Authentic historical order misleadingly recirculated out of chronological context.",
                detailed_analysis=(
                    interpretation.discrepancy_explanation
                    or "Historical records match this circular to an earlier year (e.g. 2020 lockdown). No such order is in effect for current year."
                ),
                temporal_status=TemporalStatus.OUTDATED,
                rule_matched="RULE-TEMPORAL-RECIRCULATION",
                counter_evidence_summary="Archived historical notice recirculated without original publication timestamp.",
                source_citations=evidence_list,
            )

        # 3. Check for Financial / Numerical Discrepancy
        if interpretation.claimed_amount is not None and interpretation.actual_amount is not None:
            if abs(interpretation.claimed_amount - interpretation.actual_amount) > 0.01:
                logger.info(
                    "Rule match: RULE-FINANCIAL-DISCREPANCY (claimed: %s vs actual: %s)",
                    interpretation.claimed_amount,
                    interpretation.actual_amount,
                )
                return ClaimResult(
                    id=claim_id,
                    claim_number=claim.claim_number,
                    claim_text=claim.claim_text,
                    original_language_text=claim.original_language_text,
                    language=claim.language,
                    verdict=Verdict.FALSE,
                    confidence=98.8,
                    summary=f"Financial amount discrepancy: Claimed ₹{interpretation.claimed_amount:,.0f} vs Sanctioned ₹{interpretation.actual_amount:,.0f}.",
                    detailed_analysis=(
                        interpretation.discrepancy_explanation
                        or f"Gazette records sanction ₹{interpretation.actual_amount:,.0f}, directly refuting the claimed ₹{interpretation.claimed_amount:,.0f} figure."
                    ),
                    temporal_status=TemporalStatus.CURRENT,
                    rule_matched="RULE-FINANCIAL-DISCREPANCY",
                    counter_evidence_summary=f"Claimed figure ₹{interpretation.claimed_amount:,.0f} contradicts official gazetted rate of ₹{interpretation.actual_amount:,.0f}.",
                    source_citations=evidence_list,
                )

        # 4. Check for Direct Refutation
        if interpretation.refutes_claim:
            logger.info("Rule match: RULE-DIRECT-REFUTATION on claim %d", claim.claim_number)
            return ClaimResult(
                id=claim_id,
                claim_number=claim.claim_number,
                claim_text=claim.claim_text,
                original_language_text=claim.original_language_text,
                language=claim.language,
                verdict=Verdict.FALSE,
                confidence=98.5,
                summary="Claim is factually false and directly contradicted by authoritative public records.",
                detailed_analysis=(
                    interpretation.discrepancy_explanation
                    or "Primary statutory records and official gazettes refute this assertion."
                ),
                temporal_status=TemporalStatus.CURRENT,
                rule_matched="RULE-DIRECT-REFUTATION",
                counter_evidence_summary="Contradicted by primary statutory record.",
                source_citations=evidence_list,
            )

        # 5. Check for Official Corroboration (Tier-1 Primary Confirmation)
        # Source trust is evaluated strictly via SourceRegistryService; no hardcoded trust logic in verdict engine.
        tier1_sources = [
            e for e in evidence_list
            if source_registry_service.is_allowed(e.domain or e.url)
            and (source_registry_service.get_tier(e.domain or e.url) == 1 or e.tier == SourceTier.TIER_1_PRIMARY)
            and source_registry_service.rank_source(e.domain or e.url).is_authoritative
        ]
        if interpretation.supports_claim and len(tier1_sources) >= 1:
            logger.info("Rule match: RULE-OFFICIAL-GAZETTE-CORROBORATION on claim %d", claim.claim_number)
            return ClaimResult(
                id=claim_id,
                claim_number=claim.claim_number,
                claim_text=claim.claim_text,
                original_language_text=claim.original_language_text,
                language=claim.language,
                verdict=Verdict.VERIFIED,
                confidence=99.2,
                summary="Corroborated by official gazette notification and statutory records.",
                detailed_analysis=(
                    f"Verified against {tier1_sources[0].publisher} ({tier1_sources[0].domain}). "
                    f"Quotation: '{tier1_sources[0].exact_quote}'"
                ),
                temporal_status=TemporalStatus.CURRENT,
                rule_matched="RULE-OFFICIAL-GAZETTE-CORROBORATION",
                source_citations=evidence_list,
            )

        # 6. Check for Partly Supported Evidence
        if interpretation.supports_claim and (interpretation.discrepancy_explanation or len(tier1_sources) == 0):
            logger.info("Rule match: RULE-PARTIALLY-SUPPORTED on claim %d", claim.claim_number)
            return ClaimResult(
                id=claim_id,
                claim_number=claim.claim_number,
                claim_text=claim.claim_text,
                original_language_text=claim.original_language_text,
                language=claim.language,
                verdict=Verdict.PARTLY_SUPPORTED,
                confidence=78.5,
                summary="Partially supported: core premise has factual basis but secondary details remain unverified.",
                detailed_analysis=(
                    interpretation.discrepancy_explanation
                    or "Available sources confirm partial elements of this claim but cannot substantiate all particulars."
                ),
                temporal_status=TemporalStatus.CURRENT,
                rule_matched="RULE-PARTIALLY-SUPPORTED",
                source_citations=evidence_list,
            )

        # 7. Insufficient Evidence / Uncorroborated Assertion
        logger.info("Rule match: RULE-INSUFFICIENT-EVIDENCE on claim %d", claim.claim_number)
        return ClaimResult(
            id=claim_id,
            claim_number=claim.claim_number,
            claim_text=claim.claim_text,
            original_language_text=claim.original_language_text,
            language=claim.language,
            verdict=Verdict.CANNOT_BE_CONFIRMED,
            confidence=48.0,
            summary="Cannot be confirmed due to lack of authoritative primary documentary trail.",
            detailed_analysis=(
                "No official gazette, court order, or ministry bulletin corroborates or refutes this claim. "
                "SachCheck strictly withholds judgment rather than speculating."
            ),
            temporal_status=TemporalStatus.UNDATED,
            rule_matched="RULE-INSUFFICIENT-EVIDENCE",
            source_citations=evidence_list,
        )

    @staticmethod
    def aggregate_verdicts(claims: List[ClaimResult]) -> Tuple[Verdict, str]:
        """
        Aggregates individual atomic claim verdicts into the overall dossier verdict.

        Hierarchy:
        - If any claim is FALSE -> Overall verdict is FALSE (or deceptive package)
        - Else if any claim is OUTDATED -> Overall verdict is OUTDATED
        - Else if any claim is PARTLY_SUPPORTED -> Overall verdict is PARTLY_SUPPORTED
        - Else if all claims are VERIFIED -> Overall verdict is VERIFIED
        - Else if all claims are CANNOT_BE_CONFIRMED -> Overall verdict is CANNOT_BE_CONFIRMED
        """
        if not claims:
            return Verdict.CANNOT_BE_CONFIRMED, "No atomic claims could be extracted to verify."

        verdicts = [c.verdict for c in claims]

        if Verdict.FALSE in verdicts:
            false_count = verdicts.count(Verdict.FALSE)
            summary = (
                f"Contains fabricated or contradicted information ({false_count} of {len(claims)} claims debunked). "
                "Official records refute the assertion."
            )
            return Verdict.FALSE, summary

        if Verdict.OUTDATED in verdicts:
            return (
                Verdict.OUTDATED,
                "Notice is authentic but historical; misleadingly shared out of chronological context.",
            )

        if Verdict.PARTLY_SUPPORTED in verdicts:
            return (
                Verdict.PARTLY_SUPPORTED,
                "Contains factual elements mixed with exaggerated or unconfirmed details.",
            )

        if all(v == Verdict.VERIFIED for v in verdicts):
            return (
                Verdict.VERIFIED,
                "All statements in this forward are fully corroborated by official public records.",
            )

        if all(v == Verdict.CANNOT_BE_CONFIRMED for v in verdicts):
            return (
                Verdict.CANNOT_BE_CONFIRMED,
                "Insufficient documentary proof found across authoritative government repositories.",
            )

        return (
            Verdict.PARTLY_SUPPORTED,
            "Mixed findings across extracted claims. Consult the individual claim audit cards.",
        )
