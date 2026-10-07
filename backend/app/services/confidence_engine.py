import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from app.schemas.enums import (
    ConfidenceLevel,
    ContradictionStrength,
    SourceTier,
    TemporalStatus,
)
from app.schemas.judge import EvidenceStance
from app.schemas.confidence import (
    ClaimConfidenceItem,
    ConfidenceFactorsBreakdown,
    ConfidenceInput,
    ConfidenceOutput,
    MessageConfidenceOutput,
)
from app.schemas.evidence import EvidenceItem, LockedEvidenceItem

logger = logging.getLogger("sachcheck.confidence_engine")

# Strict categorical ranking
CONFIDENCE_RANK = {
    ConfidenceLevel.LOW: 1,
    ConfidenceLevel.MEDIUM: 2,
    ConfidenceLevel.HIGH: 3,
}


class ConfidenceEngine:
    """
    Deterministic Confidence Engine for SachCheck.

    CRITICAL INVARIANTS:
    1. NEVER calls an LLM.
    2. Computes confidence purely from:
       - source credibility
       - source agreement
       - source relevance
       - recency
       - retrieval quality
       - contradiction strength
       - ambiguity
       - evidence quantity
    3. Output is strictly categorical: HIGH, MEDIUM, LOW.
    4. Does not expose fake precision (e.g. 0.9738421) to end users.
    5. The overall message confidence is limited by the weakest important claim.
    """

    def calculate_confidence(
        self,
        source_credibility: Optional[Union[float, str, SourceTier]] = None,
        source_agreement: Optional[Union[float, str]] = None,
        source_relevance: Optional[Union[float, str]] = None,
        recency: Optional[Union[float, str, TemporalStatus]] = None,
        retrieval_quality: Optional[Union[float, str]] = None,
        contradiction_strength: Optional[Union[float, str, ContradictionStrength]] = None,
        ambiguity: Optional[Union[float, str]] = None,
        evidence_quantity: Optional[int] = None,
        claim: Optional[Any] = None,
        evidence_list: Optional[List[Any]] = None,
        evidence_judgments: Optional[List[Any]] = None,
        temporal_status: Optional[Union[TemporalStatus, str]] = None,
    ) -> ConfidenceLevel:
        """
        Direct entry point returning strictly HIGH, MEDIUM, or LOW.
        """
        detailed = self.calculate_confidence_detailed(
            source_credibility=source_credibility,
            source_agreement=source_agreement,
            source_relevance=source_relevance,
            recency=recency or temporal_status,
            retrieval_quality=retrieval_quality,
            contradiction_strength=contradiction_strength,
            ambiguity=ambiguity,
            evidence_quantity=evidence_quantity,
            claim=claim,
            evidence_list=evidence_list,
            evidence_judgments=evidence_judgments,
            temporal_status=temporal_status,
        )
        return detailed.confidence

    def calculate_confidence_detailed(
        self,
        input_data: Optional[Union[ConfidenceInput, Dict[str, Any]]] = None,
        **kwargs,
    ) -> ConfidenceOutput:
        """
        Evaluates normalized factors and produces a deterministic ConfidenceOutput.
        Internal continuous score is computed for gating, but exposed rating is only HIGH/MEDIUM/LOW.
        """
        params = self._merge_params(input_data, kwargs)

        # 1. Parse / normalize each of the 8 factors to [0.0 - 1.0]
        s_cred = self._parse_source_credibility(
            params.get("source_credibility"),
            params.get("evidence_list"),
        )
        s_agree = self._parse_source_agreement(
            params.get("source_agreement"),
            params.get("evidence_judgments"),
            params.get("evidence_list"),
            s_cred,
        )
        s_rel = self._parse_source_relevance(
            params.get("source_relevance"),
            params.get("evidence_judgments"),
            params.get("evidence_list"),
        )
        s_rec = self._parse_recency(
            params.get("recency") or params.get("temporal_status"),
        )
        s_qual = self._parse_retrieval_quality(
            params.get("retrieval_quality"),
        )
        s_contra = self._parse_contradiction_strength(
            params.get("contradiction_strength"),
        )
        s_amb = self._parse_ambiguity(
            params.get("ambiguity"),
            params.get("claim"),
        )
        s_qty = self._parse_evidence_quantity(
            params.get("evidence_quantity"),
            params.get("evidence_list"),
            s_cred,
        )

        # 2. Apply Gating / Guardrail Rules
        # Hard Rule A: Zero evidence or all irrelevant evidence -> LOW
        raw_qty = (
            params.get("evidence_quantity")
            if params.get("evidence_quantity") is not None
            else (len(params.get("evidence_list")) if params.get("evidence_list") is not None else None)
        )
        if raw_qty == 0 or (s_qty == 0.0 and s_rel == 0.0):
            return self._build_output(
                ConfidenceLevel.LOW,
                0.0,
                s_cred, s_agree, s_rel, s_rec, s_qual, s_contra, s_amb, s_qty,
                "Zero valid evidence citations.",
            )

        # Hard Rule B: Poor retrieval quality (< 0.35) and lack of authoritative source -> LOW
        if s_qual < 0.35 and s_cred < 0.8:
            return self._build_output(
                ConfidenceLevel.LOW,
                0.20,
                s_cred, s_agree, s_rel, s_rec, s_qual, s_contra, s_amb, s_qty,
                "Poor retrieval quality below threshold without authoritative tier-1 source.",
            )

        # Hard Rule C: Conflicting evidence without authoritative override -> LOW
        if s_agree <= 0.50 and s_cred < 0.85:
            return self._build_output(
                ConfidenceLevel.LOW,
                0.28,
                s_cred, s_agree, s_rel, s_rec, s_qual, s_contra, s_amb, s_qty,
                "Severe source conflict without authoritative tier-1 adjudication.",
            )

        # Hard Rule D: Weak sources + old/expired evidence -> LOW
        if s_cred <= 0.40 and s_rec <= 0.35:
            return self._build_output(
                ConfidenceLevel.LOW,
                0.22,
                s_cred, s_agree, s_rel, s_rec, s_qual, s_contra, s_amb, s_qty,
                "Weak source credibility combined with old/outdated evidence.",
            )

        # 3. Deterministic Composite Scoring
        # Positive Weights: Credibility(0.25) + Agreement(0.20) + Relevance(0.15) + Recency(0.15) + Retrieval(0.10) + Quantity(0.15) = 1.00
        composite = (
            (0.25 * s_cred)
            + (0.20 * s_agree)
            + (0.15 * s_rel)
            + (0.15 * s_rec)
            + (0.10 * s_qual)
            + (0.15 * s_qty)
        )

        # Penalties: Ambiguity & Discordant Contradiction
        ambiguity_penalty = 0.20 * s_amb
        conflict_penalty = 0.15 * s_contra if (s_agree < 0.60 and s_cred < 0.85) else 0.0

        internal_score = max(0.0, min(1.0, composite - ambiguity_penalty - conflict_penalty))

        # 4. Threshold Evaluation for HIGH / MEDIUM / LOW
        # HIGH requires:
        # - internal_score >= 0.72
        # - High credibility (Tier 1 or strong Tier 2, s_cred >= 0.70)
        # - Strong quote relevance (s_rel >= 0.70)
        # - Current or historically established recency (s_rec >= 0.60)
        # - Good source agreement (s_agree >= 0.60)
        # - At least 1 validated evidence citation (s_qty >= 0.50)
        if (
            internal_score >= 0.72
            and s_cred >= 0.70
            and s_rel >= 0.70
            and s_rec >= 0.60
            and s_agree >= 0.60
            and s_qty >= 0.50
        ):
            confidence_level = ConfidenceLevel.HIGH
            reasoning = "Authoritative corroboration with strong relevance and high recency."
        elif internal_score >= 0.38:
            confidence_level = ConfidenceLevel.MEDIUM
            reasoning = "Moderate evidentiary basis; acceptable credibility with partial limitations."
        else:
            confidence_level = ConfidenceLevel.LOW
            reasoning = "Insufficient evidentiary weight or conflicting indicators."

        # High Ambiguity Cap: if ambiguity is high, cap at MEDIUM
        if s_amb >= 0.70 and confidence_level == ConfidenceLevel.HIGH:
            confidence_level = ConfidenceLevel.MEDIUM
            reasoning += " (Capped due to high assertion ambiguity)"

        return self._build_output(
            confidence_level,
            round(internal_score, 4),
            s_cred, s_agree, s_rel, s_rec, s_qual, s_contra, s_amb, s_qty,
            reasoning,
        )

    def calculate_message_confidence(
        self,
        claims: List[Any],
    ) -> ConfidenceLevel:
        """
        Computes overall message confidence.
        RULE: The overall message confidence must be limited by the weakest important claim.
        """
        detailed = self.calculate_message_confidence_detailed(claims)
        return detailed.overall_confidence

    def calculate_message_confidence_detailed(
        self,
        claims: List[Any],
    ) -> MessageConfidenceOutput:
        """
        Evaluates list of claims and returns structured message confidence output.
        """
        if not claims:
            return MessageConfidenceOutput(
                overall_confidence=ConfidenceLevel.LOW,
                weakest_claim_id=None,
                evaluated_claims_count=0,
                important_claims_count=0,
                rule_applied="NO_CLAIMS_PRESENT_DEFAULT_LOW",
            )

        evaluated_claims: List[Tuple[str, ConfidenceLevel, bool]] = []
        for claim in claims:
            claim_id, conf_lvl, is_important = self._extract_claim_confidence_info(claim)
            evaluated_claims.append((claim_id, conf_lvl, is_important))

        important_claims = [c for c in evaluated_claims if c[2]]

        # If no claims were marked check-worthy/important, consider all claims
        target_group = important_claims if important_claims else evaluated_claims

        # Find the weakest claim by rank
        weakest_tuple = min(target_group, key=lambda c: CONFIDENCE_RANK.get(c[1], 1))
        weakest_claim_id, weakest_level, _ = weakest_tuple

        return MessageConfidenceOutput(
            overall_confidence=weakest_level,
            weakest_claim_id=weakest_claim_id,
            evaluated_claims_count=len(evaluated_claims),
            important_claims_count=len(important_claims),
            rule_applied="WEAKEST_IMPORTANT_CLAIM_LIMITATION",
        )

    # -------------------------------------------------------------------------
    # Factor Normalizers
    # -------------------------------------------------------------------------

    def _parse_source_credibility(
        self,
        val: Optional[Union[float, str, SourceTier]],
        evidence_list: Optional[List[Any]],
    ) -> float:
        """Normalizes source credibility to [0.0 - 1.0]."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))

        if isinstance(val, SourceTier):
            if val == SourceTier.TIER_1_PRIMARY:
                return 1.0
            if val == SourceTier.TIER_2_SECONDARY:
                return 0.85
            if val == SourceTier.TIER_3_REPUTABLE:
                return 0.50
            return 0.20

        if isinstance(val, str):
            v_up = val.strip().upper()
            if "TIER_1" in v_up or "OFFICIAL" in v_up or "PRIMARY" in v_up:
                return 1.0
            if "TIER_2" in v_up or "SECONDARY" in v_up:
                return 0.85
            if "TIER_3" in v_up or "REPUTABLE" in v_up:
                return 0.50
            if v_up in ("HIGH", "EXCELLENT"):
                return 0.95
            if v_up in ("MEDIUM", "MODERATE"):
                return 0.65
            if v_up in ("LOW", "WEAK", "POOR", "UNTRUSTED"):
                return 0.25
            try:
                return max(0.0, min(1.0, float(val)))
            except ValueError:
                pass

        # Infer from evidence items
        if evidence_list:
            highest_tier = 4
            for ev in evidence_list:
                tier_val = getattr(ev, "tier", None) or getattr(ev, "source_tier", None)
                if tier_val == SourceTier.TIER_1_PRIMARY or tier_val == 1:
                    highest_tier = min(highest_tier, 1)
                elif tier_val == SourceTier.TIER_2_SECONDARY or tier_val == 2:
                    highest_tier = min(highest_tier, 2)
                elif tier_val == SourceTier.TIER_3_REPUTABLE or tier_val == 3:
                    highest_tier = min(highest_tier, 3)

            if highest_tier == 1:
                return 1.0
            if highest_tier == 2:
                return 0.85
            if highest_tier == 3:
                return 0.50
            return 0.25

        return 0.30

    def _parse_source_agreement(
        self,
        val: Optional[Union[float, str]],
        judgments: Optional[List[Any]],
        evidence_list: Optional[List[Any]],
        credibility: float,
    ) -> float:
        """Normalizes source agreement to [0.0 - 1.0]."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))

        if isinstance(val, str):
            v_up = val.strip().upper()
            if v_up in ("UNANIMOUS", "COMPLETE", "HIGH"):
                return 1.0
            if v_up in ("MODERATE", "FAIR", "MEDIUM"):
                return 0.70
            if v_up in ("CONFLICTING", "DISPUTED", "SPLIT", "LOW"):
                return 0.35
            try:
                return max(0.0, min(1.0, float(val)))
            except ValueError:
                pass

        if judgments and len(judgments) > 1:
            support_count = sum(1 for j in judgments if getattr(j, "stance", None) == EvidenceStance.SUPPORTS)
            contradict_count = sum(1 for j in judgments if getattr(j, "stance", None) == EvidenceStance.CONTRADICTS)
            total = support_count + contradict_count
            if total > 0:
                majority = max(support_count, contradict_count)
                ratio = majority / total
                # Ratio 1.0 -> unanimous (1.0), Ratio 0.5 -> split (0.35)
                return 0.35 + (0.65 * (ratio - 0.5) / 0.5) if ratio >= 0.5 else 0.35

        # Single evidence item or uncontested source
        if evidence_list and len(evidence_list) == 1:
            return 0.85 if credibility >= 0.85 else 0.70

        if not evidence_list:
            return 0.0

        return 0.75

    def _parse_source_relevance(
        self,
        val: Optional[Union[float, str]],
        judgments: Optional[List[Any]],
        evidence_list: Optional[List[Any]],
    ) -> float:
        """Normalizes source relevance to [0.0 - 1.0]."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))

        if isinstance(val, str):
            v_up = val.strip().upper()
            if v_up in ("HIGH", "EXACT_QUOTE", "STRONG_QUOTE", "DIRECT"):
                return 1.0
            if v_up in ("MEDIUM", "MODERATE", "PARTIAL"):
                return 0.65
            if v_up in ("LOW", "WEAK"):
                return 0.30
            if v_up in ("IRRELEVANT", "NONE"):
                return 0.0
            try:
                return max(0.0, min(1.0, float(val)))
            except ValueError:
                pass

        if judgments:
            # Check for IRRELEVANT stances
            all_irrelevant = all(getattr(j, "stance", None) == EvidenceStance.IRRELEVANT for j in judgments)
            if all_irrelevant:
                return 0.0
            has_high_rel = any(getattr(j, "relevance", None) in ("HIGH", 1.0) for j in judgments)
            if has_high_rel:
                return 1.0
            return 0.65

        if evidence_list:
            # Check exact quote presence
            has_exact = any(bool(getattr(ev, "exact_quote", None)) for ev in evidence_list)
            return 1.0 if has_exact else 0.60

        return 0.0

    def _parse_recency(
        self,
        val: Optional[Union[float, str, TemporalStatus]],
    ) -> float:
        """Normalizes recency score to [0.0 - 1.0]."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))

        if isinstance(val, TemporalStatus):
            if val == TemporalStatus.CURRENT:
                return 1.0
            if val == TemporalStatus.HISTORICAL_TRUE:
                return 0.90
            if val in (TemporalStatus.DATE_UNKNOWN, TemporalStatus.UNDATED):
                return 0.45
            if val in (TemporalStatus.EXPIRED, TemporalStatus.OUTDATED):
                return 0.25
            if val == TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE:
                return 0.15
            return 0.50

        if isinstance(val, str):
            v_up = val.strip().upper()
            if v_up in ("CURRENT", "RECENT", "FRESH", "NOW"):
                return 1.0
            if v_up in ("HISTORICAL", "HISTORICAL_TRUE"):
                return 0.90
            if v_up in ("DATE_UNKNOWN", "UNKNOWN", "UNDATED"):
                return 0.45
            if v_up in ("EXPIRED", "OUTDATED", "OLD", "SUPERSEDED"):
                return 0.25
            if v_up in ("CONTRADICTED_BY_NEWER_EVIDENCE", "NEWER_CONTRADICTS"):
                return 0.15
            try:
                return max(0.0, min(1.0, float(val)))
            except ValueError:
                pass

        return 0.80

    def _parse_retrieval_quality(
        self,
        val: Optional[Union[float, str]],
    ) -> float:
        """Normalizes retrieval quality score to [0.0 - 1.0]."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))

        if isinstance(val, str):
            v_up = val.strip().upper()
            if v_up in ("HIGH", "EXCELLENT", "GOOD"):
                return 1.0
            if v_up in ("MEDIUM", "MODERATE", "FAIR"):
                return 0.65
            if v_up in ("POOR", "LOW", "INSUFFICIENT"):
                return 0.20
            try:
                return max(0.0, min(1.0, float(val)))
            except ValueError:
                pass

        return 0.85

    def _parse_contradiction_strength(
        self,
        val: Optional[Union[float, str, ContradictionStrength]],
    ) -> float:
        """Normalizes contradiction strength to [0.0 - 1.0]."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))

        if isinstance(val, ContradictionStrength):
            if val == ContradictionStrength.STRONG:
                return 1.0
            if val == ContradictionStrength.MODERATE:
                return 0.50
            if val == ContradictionStrength.WEAK:
                return 0.20
            return 0.0

        if isinstance(val, str):
            v_up = val.strip().upper()
            if v_up in ("STRONG", "HIGH", "STRONG_CONTRADICTION", "EXPLICIT_DENIAL"):
                return 1.0
            if v_up in ("MODERATE", "MEDIUM"):
                return 0.50
            if v_up in ("WEAK", "LOW"):
                return 0.20
            if v_up in ("NONE", "NO_CONTRADICTION"):
                return 0.0
            try:
                return max(0.0, min(1.0, float(val)))
            except ValueError:
                pass

        return 0.0

    def _parse_ambiguity(
        self,
        val: Optional[Union[float, str]],
        claim: Optional[Any],
    ) -> float:
        """Normalizes ambiguity penalty to [0.0 - 1.0]. (0.0 = clear, 1.0 = ambiguous)."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))

        if isinstance(val, str):
            v_up = val.strip().upper()
            if v_up in ("LOW", "NONE", "UNAMBIGUOUS", "CLEAR"):
                return 0.0
            if v_up in ("MEDIUM", "MODERATE"):
                return 0.35
            if v_up in ("HIGH", "AMBIGUOUS", "VAGUE"):
                return 0.75
            try:
                return max(0.0, min(1.0, float(val)))
            except ValueError:
                pass

        return 0.0

    def _parse_evidence_quantity(
        self,
        val: Optional[int],
        evidence_list: Optional[List[Any]],
        credibility: float,
    ) -> float:
        """Normalizes evidence quantity to [0.0 - 1.0]."""
        count = val if val is not None else (len(evidence_list) if evidence_list is not None else 1)

        if count <= 0:
            return 0.0
        if count == 1:
            return 0.80 if credibility >= 0.85 else 0.65
        if count == 2:
            return 0.90
        return 1.0

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _merge_params(
        input_data: Optional[Union[ConfidenceInput, Dict[str, Any]]],
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Combines explicit input models, dicts, and keyword arguments."""
        res: Dict[str, Any] = {}
        if isinstance(input_data, ConfidenceInput):
            res.update(input_data.model_dump(exclude_none=True))
        elif isinstance(input_data, dict):
            res.update(input_data)
        res.update({k: v for k, v in kwargs.items() if v is not None})
        return res

    @staticmethod
    def _extract_claim_confidence_info(claim: Any) -> Tuple[str, ConfidenceLevel, bool]:
        """Extracts claim ID, ConfidenceLevel, and is_important flag from varied objects."""
        if isinstance(claim, ClaimConfidenceItem):
            return claim.claim_id, claim.confidence, claim.is_important

        claim_id = "CLM-1"
        confidence_val = ConfidenceLevel.LOW
        is_important = True

        if hasattr(claim, "id") or hasattr(claim, "claim_id"):
            claim_id = str(getattr(claim, "id", None) or getattr(claim, "claim_id", "CLM-1"))

        # Look for confidence or confidence_level attribute
        raw_conf = getattr(claim, "confidence_level", None) or getattr(claim, "confidence", None)
        if isinstance(raw_conf, ConfidenceLevel):
            confidence_val = raw_conf
        elif isinstance(raw_conf, str):
            c_up = raw_conf.strip().upper()
            if c_up in ConfidenceLevel.__members__:
                confidence_val = ConfidenceLevel(c_up)
            else:
                try:
                    num = float(c_up)
                    confidence_val = ConfidenceLevel.HIGH if num >= 75.0 else (ConfidenceLevel.MEDIUM if num >= 40.0 else ConfidenceLevel.LOW)
                except ValueError:
                    confidence_val = ConfidenceLevel.MEDIUM
        elif isinstance(raw_conf, (int, float)):
            # Numeric score (e.g. 98.0 or 0.95)
            num = float(raw_conf)
            if num <= 1.0:
                num *= 100.0
            confidence_val = ConfidenceLevel.HIGH if num >= 75.0 else (ConfidenceLevel.MEDIUM if num >= 40.0 else ConfidenceLevel.LOW)

        # Check importance / check-worthiness
        if hasattr(claim, "is_important"):
            is_important = bool(getattr(claim, "is_important"))
        elif hasattr(claim, "check_worthiness"):
            is_important = bool(getattr(claim, "check_worthiness"))

        if isinstance(claim, dict):
            claim_id = str(claim.get("claim_id") or claim.get("id") or "CLM-1")
            raw_c = claim.get("confidence") or claim.get("confidence_level")
            if isinstance(raw_c, ConfidenceLevel):
                confidence_val = raw_c
            elif isinstance(raw_c, str) and raw_c.upper() in ConfidenceLevel.__members__:
                confidence_val = ConfidenceLevel(raw_c.upper())
            elif isinstance(raw_c, (int, float)):
                n = float(raw_c)
                if n <= 1.0:
                    n *= 100.0
                confidence_val = ConfidenceLevel.HIGH if n >= 75.0 else (ConfidenceLevel.MEDIUM if n >= 40.0 else ConfidenceLevel.LOW)
            if "is_important" in claim:
                is_important = bool(claim["is_important"])
            elif "check_worthiness" in claim:
                is_important = bool(claim["check_worthiness"])

        return claim_id, confidence_val, is_important

    @staticmethod
    def _build_output(
        level: ConfidenceLevel,
        score: float,
        s_cred: float,
        s_agree: float,
        s_rel: float,
        s_rec: float,
        s_qual: float,
        s_contra: float,
        s_amb: float,
        s_qty: float,
        reasoning: str,
    ) -> ConfidenceOutput:
        """Constructs sanitized ConfidenceOutput."""
        factors = ConfidenceFactorsBreakdown(
            source_credibility=round(s_cred, 2),
            source_agreement=round(s_agree, 2),
            source_relevance=round(s_rel, 2),
            recency=round(s_rec, 2),
            retrieval_quality=round(s_qual, 2),
            contradiction_strength=round(s_contra, 2),
            ambiguity=round(s_amb, 2),
            evidence_quantity=round(s_qty, 2),
            composite_score=round(score, 2),
        )
        return ConfidenceOutput(
            confidence=level,
            internal_score=score,
            factors_breakdown=factors,
            reasoning=reasoning,
        )


# Singleton instance
confidence_engine = ConfidenceEngine()
