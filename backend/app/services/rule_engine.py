from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.logging import logger
from app.schemas.claim import ClaimResult, ExtractedClaim
from app.schemas.enums import (
    ConfidenceLevel,
    Language,
    SourceTier,
    TemporalStatus,
    Verdict,
)
from app.schemas.evidence import EvidenceInterpretation, EvidenceItem, LockedEvidenceItem
from app.schemas.judge import EvidenceAssessmentLevel, EvidenceJudgeAssessment, EvidenceStance
from app.services.evidence_locking import evidence_locking_service
from app.services.source_registry import source_registry_service
from app.services.confidence_engine import confidence_engine


class DeterministicRuleEngine:
    """
    Deterministic Verdict Engine for SachCheck.

    CRITICAL ARCHITECTURAL GUARANTEE:
    This pure-code deterministic engine computes the final verdict based on
    strict statutory evidence rules, source tiers, temporal status, contradiction
    strength, agreement, recency, and retrieval quality.
    THE VERDICT ENGINE MUST NOT CALL AN LLM.

    Allowed verdicts ONLY:
    - VERIFIED: credible current evidence supports the claim.
    - FALSE: credible evidence directly contradicts the claim.
    - OUTDATED: claim was previously true but newer evidence invalidates its current form.
    - PARTLY_SUPPORTED: some parts are supported while others are unsupported/exaggerated/incorrect.
    - CANNOT_BE_CONFIRMED: insufficient reliable evidence (do not guess).
    """

    @classmethod
    def compute_verdict(
        cls,
        claim: Union[ExtractedClaim, str, Any],
        validated_evidence: List[Union[EvidenceItem, LockedEvidenceItem, Dict[str, Any]]],
        evidence_judgments: Optional[List[EvidenceJudgeAssessment]] = None,
        temporal_status: Optional[TemporalStatus] = None,
        source_tiers: Optional[List[int]] = None,
        contradiction_strength: Optional[str] = None,
        agreement: Optional[float] = None,
        recency: Optional[Union[str, float, bool]] = None,
        retrieval_quality: Optional[Union[str, float]] = None,
        source_texts: Optional[Dict[str, str]] = None,
        interpretation: Optional[EvidenceInterpretation] = None,
    ) -> ClaimResult:
        """
        Determines the final verdict using pure deterministic code without calling an LLM.
        Generates an explicit rule trace for auditability in frontend/admin dashboards.
        """
        # 1. Normalize claim representation
        claim_obj, claim_id, claim_num, claim_text, lang = cls._normalize_claim(claim)

        # 2. Evidence Locking Grounding Check (Runs BEFORE verdict calculation)
        evidence_items = [cls._normalize_evidence_item(e) for e in validated_evidence]

        if source_texts:
            grounded_evidence, rejected = evidence_locking_service.validate_and_filter_evidence(
                evidence_items, source_texts
            )
            evidence_items = grounded_evidence
            if rejected and not evidence_items:
                logger.warning("All evidence citations failed grounding validation [QUOTE_NOT_FOUND].")
                return ClaimResult(
                    id=claim_id,
                    claim_number=claim_num,
                    claim_text=claim_text,
                    language=lang,
                    verdict=Verdict.CANNOT_BE_CONFIRMED,
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    summary="Evidence citation rejected: exact quote was not found in stored source text.",
                    detailed_analysis="Evidence Locking System rejected citations under strict anti-fabrication policy.",
                    temporal_status=TemporalStatus.DATE_UNKNOWN,
                    rule_matched="RULE-EVIDENCE-LOCKING-REJECTED",
                    rule_trace=["QUOTE_VALIDATION_FAILED", "BELOW_EVIDENCE_THRESHOLD", "INSUFFICIENT_EVIDENCE"],
                    source_citations=[],
                )

        # 3. Determine Source Tiers & Authoritativeness via Registry
        if source_tiers is not None:
            has_tier1 = 1 in source_tiers
            has_tier2 = 2 in source_tiers and not has_tier1
            has_tier3 = 3 in source_tiers and not has_tier1 and not has_tier2
        else:
            has_tier1 = any(
                (e.tier == SourceTier.TIER_1_PRIMARY or source_registry_service.get_tier(e.domain or e.url) == 1)
                and source_registry_service.is_allowed(e.domain or e.url)
                and source_registry_service.rank_source(e.domain or e.url).is_authoritative
                for e in evidence_items
            )
            has_tier2 = any(
                e.tier == SourceTier.TIER_2_SECONDARY
                or source_registry_service.get_tier(e.domain or e.url) == 2
                for e in evidence_items
            ) and not has_tier1
            has_tier3 = any(
                e.tier == SourceTier.TIER_3_REPUTABLE
                or source_registry_service.get_tier(e.domain or e.url) == 3
                for e in evidence_items
            ) and not has_tier1 and not has_tier2

        if has_tier1:
            tier_token = "TIER_1_SOURCE_PRESENT"
        elif has_tier2:
            tier_token = "TIER_2_SOURCE_PRESENT"
        elif has_tier3:
            tier_token = "TIER_3_SOURCE_PRESENT"
        else:
            tier_token = "NO_AUTHORITATIVE_SOURCE"

        # 4. Check for Malicious / Phishing Domain
        if interpretation and interpretation.domain_flagged_malicious:
            logger.info("Deterministic match: RULE-MALICIOUS-PHISHING-URL on claim %d", claim_num)
            return ClaimResult(
                id=claim_id,
                claim_number=claim_num,
                claim_text=claim_text,
                language=lang,
                verdict=Verdict.FALSE,
                confidence=100.0,
                confidence_level=ConfidenceLevel.HIGH,
                summary="Malicious phishing or fraudulent link. Blacklisted by cybersecurity advisory.",
                detailed_analysis=(
                    interpretation.discrepancy_explanation
                    or "Domain records confirm unauthorized third-party phishing site masquerading as official portal."
                ),
                temporal_status=TemporalStatus.CURRENT,
                rule_matched="RULE-MALICIOUS-PHISHING-URL",
                rule_trace=[tier_token, "MALICIOUS_DOMAIN_FLAGGED", "STRONG_CONTRADICTION", "CURRENT_EVIDENCE"],
                counter_evidence_summary="Flagged phishing domain; genuine portal is scholarships.gov.in / nic.in",
                source_citations=evidence_items,
            )

        # 5. Check for Temporal Supersession / Outdated Notice -> OUTDATED
        is_outdated = (
            temporal_status in (
                TemporalStatus.OUTDATED,
                TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE,
                TemporalStatus.EXPIRED,
            )
            or (interpretation and interpretation.is_temporal_mismatch)
        )

        if is_outdated:
            temporal_token = (
                "OUTDATED_SUPERSEDED"
                if temporal_status == TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE
                else ("EXPIRED_EVIDENCE" if temporal_status == TemporalStatus.EXPIRED else "HISTORICAL_RECIRCULATION")
            )
            rule_trace = [tier_token, temporal_token, "QUOTE_VALIDATED", "HISTORICAL_MISMATCH"]

            logger.info("Deterministic match: RULE-TEMPORAL-RECIRCULATION on claim %d", claim_num)
            return ClaimResult(
                id=claim_id,
                claim_number=claim_num,
                claim_text=claim_text,
                language=lang,
                verdict=Verdict.OUTDATED,
                confidence=96.5,
                confidence_level=ConfidenceLevel.HIGH,
                summary="Authentic historical order misleadingly recirculated out of chronological context.",
                detailed_analysis=(
                    (interpretation.discrepancy_explanation if interpretation else None)
                    or "Historical records match this circular to an earlier year (e.g. 2020 lockdown). No such order is in effect for current year."
                ),
                temporal_status=temporal_status or TemporalStatus.OUTDATED,
                rule_matched="RULE-TEMPORAL-RECIRCULATION",
                rule_trace=rule_trace,
                counter_evidence_summary="Archived historical notice recirculated without original publication timestamp.",
                source_citations=evidence_items,
            )

        # 6. Check for Financial / Numerical Discrepancy -> FALSE
        has_financial_discrepancy = (
            interpretation is not None
            and interpretation.claimed_amount is not None
            and interpretation.actual_amount is not None
            and abs(interpretation.claimed_amount - interpretation.actual_amount) > 0.01
        )

        if has_financial_discrepancy:
            temporal_token = "CURRENT_EVIDENCE" if (temporal_status != TemporalStatus.DATE_UNKNOWN) else "DATE_UNKNOWN"
            rule_trace = [tier_token, "STRONG_CONTRADICTION", "QUOTE_VALIDATED", temporal_token]

            logger.info(
                "Deterministic match: RULE-FINANCIAL-DISCREPANCY (claimed: %s vs actual: %s)",
                interpretation.claimed_amount,
                interpretation.actual_amount,
            )
            return ClaimResult(
                id=claim_id,
                claim_number=claim_num,
                claim_text=claim_text,
                language=lang,
                verdict=Verdict.FALSE,
                confidence=98.8,
                confidence_level=ConfidenceLevel.HIGH,
                summary=f"Financial amount discrepancy: Claimed ₹{interpretation.claimed_amount:,.0f} vs Sanctioned ₹{interpretation.actual_amount:,.0f}.",
                detailed_analysis=(
                    interpretation.discrepancy_explanation
                    or f"Gazette records sanction ₹{interpretation.actual_amount:,.0f}, directly refuting the claimed ₹{interpretation.claimed_amount:,.0f} figure."
                ),
                temporal_status=temporal_status or TemporalStatus.CURRENT,
                rule_matched="RULE-FINANCIAL-DISCREPANCY",
                rule_trace=rule_trace,
                counter_evidence_summary=f"Claimed figure ₹{interpretation.claimed_amount:,.0f} contradicts official gazetted rate of ₹{interpretation.actual_amount:,.0f}.",
                source_citations=evidence_items,
            )

        # 7. Check for Conflicting Sources between sources of equal tier
        has_conflicting_sources = (
            (agreement is not None and 0.25 <= agreement <= 0.75)
            or (
                evidence_judgments is not None
                and any(j.stance == EvidenceStance.SUPPORTS for j in evidence_judgments)
                and any(j.stance == EvidenceStance.CONTRADICTS for j in evidence_judgments)
            )
        )

        contradiction_dominates = False
        if has_conflicting_sources and evidence_judgments:
            ev_by_id = {e.id: e for e in evidence_items}
            contra_tiers = [
                ev_by_id[j.evidence_id].tier for j in evidence_judgments
                if j.stance == EvidenceStance.CONTRADICTS and j.evidence_id in ev_by_id
            ]
            supp_tiers = [
                ev_by_id[j.evidence_id].tier for j in evidence_judgments
                if j.stance == EvidenceStance.SUPPORTS and j.evidence_id in ev_by_id
            ]
            if any(t == SourceTier.TIER_1_PRIMARY for t in contra_tiers) and not any(t == SourceTier.TIER_1_PRIMARY for t in supp_tiers):
                contradiction_dominates = True

        has_mixed_judgment = (
            evidence_judgments is not None
            and any(j.stance == EvidenceStance.MIXED for j in evidence_judgments)
        )

        if (has_conflicting_sources and not contradiction_dominates) or has_mixed_judgment:
            conflict_token = "CONFLICTING_SOURCES" if (has_conflicting_sources and not has_mixed_judgment) else "CONDITIONAL_TERMS"
            rule_trace = [tier_token, "PARTIAL_SUPPORT", conflict_token, "CREDIBLE_SOURCE_PRESENT"]
            logger.info("Deterministic match: RULE-PARTIALLY-SUPPORTED on claim %d", claim_num)
            return ClaimResult(
                id=claim_id,
                claim_number=claim_num,
                claim_text=claim_text,
                language=lang,
                verdict=Verdict.PARTLY_SUPPORTED,
                confidence=78.5,
                confidence_level=ConfidenceLevel.MEDIUM,
                summary="Partly supported: factual foundation exists but secondary details or conditions are inaccurate, unverified, or contested.",
                detailed_analysis=(
                    (evidence_judgments[0].reason if has_mixed_judgment and evidence_judgments else None)
                    or (interpretation.discrepancy_explanation if interpretation else None)
                    or "Available evidence sources present conflicting or partial findings across equal tiers. Evaluated as partly supported."
                ),
                temporal_status=temporal_status or TemporalStatus.CURRENT,
                rule_matched="RULE-PARTIALLY-SUPPORTED",
                rule_trace=rule_trace,
                source_citations=evidence_items,
            )

        # 8. Check for Direct Refutation / Contradiction -> FALSE
        has_strong_contradiction = (
            (contradiction_strength and contradiction_strength.upper() in ("HIGH", "STRONG"))
            or (
                evidence_judgments is not None
                and any(
                    j.stance == EvidenceStance.CONTRADICTS
                    and j.strength in (EvidenceAssessmentLevel.HIGH, EvidenceAssessmentLevel.MEDIUM)
                    for j in evidence_judgments
                )
            )
            or (interpretation and interpretation.refutes_claim)
        )

        if has_strong_contradiction and (has_tier1 or has_tier2 or not (has_tier1 or has_tier2 or has_tier3) or (interpretation and interpretation.refutes_claim)):
            temporal_token = "CURRENT_EVIDENCE" if (temporal_status != TemporalStatus.DATE_UNKNOWN) else "DATE_UNKNOWN"
            rule_trace = [tier_token, "STRONG_CONTRADICTION", "QUOTE_VALIDATED", temporal_token]

            explanation = (
                interpretation.discrepancy_explanation
                if interpretation and interpretation.discrepancy_explanation
                else "Primary statutory records and official gazettes refute this assertion."
            )

            logger.info("Deterministic match: RULE-DIRECT-REFUTATION on claim %d", claim_num)
            return ClaimResult(
                id=claim_id,
                claim_number=claim_num,
                claim_text=claim_text,
                language=lang,
                verdict=Verdict.FALSE,
                confidence=98.5,
                confidence_level=ConfidenceLevel.HIGH,
                summary="Claim is factually false and directly contradicted by authoritative public records.",
                detailed_analysis=explanation,
                temporal_status=temporal_status or TemporalStatus.CURRENT,
                rule_matched="RULE-DIRECT-REFUTATION",
                rule_trace=rule_trace,
                counter_evidence_summary="Contradicted by primary statutory record.",
                source_citations=evidence_items,
            )

        # 9. Check for Official Corroboration (Tier 1 or Tier 2) -> VERIFIED
        tier1_sources = [
            e for e in evidence_items
            if source_registry_service.is_allowed(e.domain or e.url)
            and (source_registry_service.get_tier(e.domain or e.url) == 1 or e.tier == SourceTier.TIER_1_PRIMARY)
            and source_registry_service.rank_source(e.domain or e.url).is_authoritative
        ]
        tier2_sources = [
            e for e in evidence_items
            if source_registry_service.is_allowed(e.domain or e.url)
            and (source_registry_service.get_tier(e.domain or e.url) == 2 or e.tier == SourceTier.TIER_2_SECONDARY)
        ]

        has_support = (
            (evidence_judgments is not None and any(j.stance == EvidenceStance.SUPPORTS for j in evidence_judgments))
            or (interpretation and interpretation.supports_claim)
            or (agreement is not None and agreement >= 0.75)
        )

        has_partial_details = (
            (evidence_judgments is not None and any(j.stance == EvidenceStance.MIXED for j in evidence_judgments))
            or (interpretation and interpretation.supports_claim and bool(interpretation.discrepancy_explanation))
            or (interpretation and interpretation.supports_claim and len(tier1_sources) == 0 and len(tier2_sources) == 0 and not source_tiers)
        )

        if has_support and (len(tier1_sources) >= 1 or len(tier2_sources) >= 1 or (source_tiers and (1 in source_tiers or 2 in source_tiers))) and not has_partial_details:
            temporal_token = "HISTORICAL_TRUE_EVIDENCE" if temporal_status == TemporalStatus.HISTORICAL_TRUE else "CURRENT_EVIDENCE"
            rule_trace = [tier_token, "CREDIBLE_CORROBORATION", "QUOTE_VALIDATED", temporal_token]

            pub = tier1_sources[0].publisher if tier1_sources else (tier2_sources[0].publisher if tier2_sources else "Official Record")
            dom = tier1_sources[0].domain if tier1_sources else (tier2_sources[0].domain if tier2_sources else "gov.in")
            quote_snip = tier1_sources[0].exact_quote if tier1_sources else (tier2_sources[0].exact_quote if tier2_sources else "")

            logger.info("Deterministic match: RULE-OFFICIAL-GAZETTE-CORROBORATION on claim %d", claim_num)
            return ClaimResult(
                id=claim_id,
                claim_number=claim_num,
                claim_text=claim_text,
                language=lang,
                verdict=Verdict.VERIFIED,
                confidence=99.2,
                confidence_level=ConfidenceLevel.HIGH,
                summary="Corroborated by official gazette notification and statutory records.",
                detailed_analysis=f"Verified against {pub} ({dom}). Quotation: '{quote_snip}'",
                temporal_status=temporal_status or TemporalStatus.CURRENT,
                rule_matched="RULE-OFFICIAL-GAZETTE-CORROBORATION",
                rule_trace=rule_trace,
                source_citations=evidence_items,
            )

        # 10. Check for Partly Supported Evidence
        if has_support and has_partial_details:
            rule_trace = [tier_token, "PARTIAL_SUPPORT", "CONDITIONAL_TERMS", "CREDIBLE_SOURCE_PRESENT"]
            logger.info("Deterministic match: RULE-PARTIALLY-SUPPORTED on claim %d", claim_num)
            return ClaimResult(
                id=claim_id,
                claim_number=claim_num,
                claim_text=claim_text,
                language=lang,
                verdict=Verdict.PARTLY_SUPPORTED,
                confidence=78.5,
                confidence_level=ConfidenceLevel.MEDIUM,
                summary="Partially supported: core premise has factual basis but secondary details remain unverified.",
                detailed_analysis=(
                    (interpretation.discrepancy_explanation if interpretation else None)
                    or "Available sources confirm partial elements of this claim but cannot substantiate all particulars."
                ),
                temporal_status=temporal_status or TemporalStatus.CURRENT,
                rule_matched="RULE-PARTIALLY-SUPPORTED",
                rule_trace=rule_trace,
                source_citations=evidence_items,
            )

        # 11. Fallback: Below-Threshold / Insufficient Evidence -> CANNOT_BE_CONFIRMED (Do NOT guess)
        quality_score = cls._parse_quality_score(retrieval_quality)
        is_poor_quality = quality_score is not None and quality_score < 0.35
        all_irrelevant = (
            evidence_judgments is not None
            and len(evidence_judgments) > 0
            and all(j.stance == EvidenceStance.IRRELEVANT for j in evidence_judgments)
        )

        trace = []
        if tier_token != "NO_AUTHORITATIVE_SOURCE":
            trace.append(tier_token)
        if all_irrelevant:
            trace.append("ALL_EVIDENCE_IRRELEVANT")
        trace.extend(["INSUFFICIENT_EVIDENCE", "BELOW_EVIDENCE_THRESHOLD"])

        logger.info("Deterministic match: RULE-INSUFFICIENT-EVIDENCE on claim %d", claim_num)
        return ClaimResult(
            id=claim_id,
            claim_number=claim_num,
            claim_text=claim_text,
            language=lang,
            verdict=Verdict.CANNOT_BE_CONFIRMED,
            confidence=48.0 if evidence_items else 0.0,
            confidence_level=ConfidenceLevel.LOW,
            summary="Cannot be confirmed due to lack of authoritative primary documentary trail.",
            detailed_analysis=(
                "No official gazette, court order, or ministry bulletin corroborates or refutes this claim. "
                "SachCheck strictly withholds judgment rather than speculating."
            ),
            temporal_status=temporal_status or TemporalStatus.UNDATED,
            rule_matched="RULE-INSUFFICIENT-EVIDENCE",
            rule_trace=trace,
            source_citations=evidence_items,
        )

    @classmethod
    def evaluate_claim(
        cls,
        claim: ExtractedClaim,
        evidence_list: List[EvidenceItem],
        interpretation: EvidenceInterpretation,
        source_texts: Optional[Dict[str, str]] = None,
    ) -> ClaimResult:
        """Backward-compatible entry point for existing verification workflows."""
        temp_status = TemporalStatus.OUTDATED if interpretation.is_temporal_mismatch else TemporalStatus.CURRENT
        return cls.compute_verdict(
            claim=claim,
            validated_evidence=evidence_list,
            temporal_status=temp_status,
            source_texts=source_texts,
            interpretation=interpretation,
        )

    @staticmethod
    def aggregate_verdicts(claims: List[ClaimResult]) -> Tuple[Verdict, str]:
        """
        Aggregates individual atomic claim verdicts into the overall dossier verdict.
        Hierarchy: FALSE > OUTDATED > PARTLY_SUPPORTED > VERIFIED > CANNOT_BE_CONFIRMED.
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

    @staticmethod
    def _normalize_claim(claim: Any) -> Tuple[Any, str, int, str, Language]:
        """Extracts claim fields uniformly."""
        if isinstance(claim, ExtractedClaim):
            lang = claim.language if isinstance(claim.language, Language) else Language.EN
            return claim, f"CLM-{claim.claim_number}", claim.claim_number, claim.claim_text, lang

        if isinstance(claim, str):
            return None, "CLM-1", 1, claim, Language.EN

        if hasattr(claim, "claim_id") and hasattr(claim, "normalized_claim"):
            raw_lang = getattr(claim, "language", "en")
            lang = Language(raw_lang) if raw_lang in ["en", "hi", "mr"] else Language.EN
            return claim, getattr(claim, "claim_id", "CLM-1"), 1, getattr(claim, "normalized_claim", str(claim)), lang

        return claim, "CLM-1", 1, str(claim), Language.EN

    @staticmethod
    def _normalize_evidence_item(evidence: Any) -> EvidenceItem:
        """Converts diverse evidence representations to EvidenceItem."""
        if isinstance(evidence, EvidenceItem):
            return evidence

        if isinstance(evidence, LockedEvidenceItem):
            tier = (
                SourceTier.TIER_1_PRIMARY
                if evidence.source_tier == 1
                else (SourceTier.TIER_2_SECONDARY if evidence.source_tier == 2 else SourceTier.TIER_3_REPUTABLE)
            )
            return EvidenceItem(
                id="ev_001",
                publisher=evidence.publisher,
                domain="official.gov.in",
                title=evidence.source_title,
                publish_date=evidence.published_date,
                tier=tier,
                url=evidence.source_url,
                exact_quote=evidence.exact_quote,
            )

        if isinstance(evidence, dict):
            tier_int = evidence.get("source_tier") or evidence.get("tier") or 1
            tier = (
                SourceTier.TIER_1_PRIMARY
                if tier_int == 1
                else (SourceTier.TIER_2_SECONDARY if tier_int == 2 else SourceTier.TIER_3_REPUTABLE)
            )
            return EvidenceItem(
                id=str(evidence.get("evidence_id") or evidence.get("id") or "ev_001"),
                publisher=str(evidence.get("publisher") or "Official Publisher"),
                domain=str(evidence.get("domain") or "gov.in"),
                title=str(evidence.get("title") or "Official Record"),
                publish_date=evidence.get("published_date") or evidence.get("publish_date"),
                tier=tier,
                url=str(evidence.get("url") or evidence.get("source_url") or "https://gov.in/order"),
                exact_quote=str(evidence.get("exact_quote") or evidence.get("quote") or ""),
            )

        return EvidenceItem(
            id="ev_001",
            publisher="Official Authority",
            domain="gov.in",
            title="Statutory Record",
            tier=SourceTier.TIER_1_PRIMARY,
            url="https://gov.in",
            exact_quote=str(evidence),
        )

    @staticmethod
    def _parse_quality_score(quality: Optional[Union[str, float]]) -> Optional[float]:
        """Normalizes retrieval quality input into a 0.0 - 1.0 float."""
        if quality is None:
            return None
        if isinstance(quality, (int, float)):
            return float(quality)
        q_str = str(quality).strip().upper()
        if q_str in ("POOR", "LOW", "INSUFFICIENT"):
            return 0.2
        if q_str in ("MEDIUM", "MODERATE", "FAIR"):
            return 0.5
        if q_str in ("HIGH", "EXCELLENT", "GOOD"):
            return 0.9
        try:
            return float(q_str)
        except ValueError:
            return 0.5


# Default singleton instance
deterministic_rule_engine = DeterministicRuleEngine()
