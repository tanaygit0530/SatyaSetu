import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.core.logging import logger
from app.schemas.enums import TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem, LockedEvidenceItem
from app.schemas.judge import EvidenceJudgeAssessment, EvidenceStance
from app.schemas.temporal import (
    ExtractedTemporalDates,
    TemporalEvidenceItem,
    TemporalVerificationResult,
)


class TemporalVerificationService:
    """
    Temporal Verification Service.

    Distinguishes:
        TRUE THEN from TRUE NOW.

    Extracts:
        - claim date
        - evidence date
        - effective date
        - expiry date
        - current date

    Rules:
    - Example 1:
        Claim: "Scheme X currently gives ₹10,000."
        Evidence 2024: "Scheme X gives ₹10,000."
        Evidence 2026: "Scheme X was discontinued in 2025."
        -> Result: OUTDATED, TemporalStatus: CONTRADICTED_BY_NEWER_EVIDENCE (not VERIFIED).
    - Example 2:
        Claim: "Government announced X in 2024."
        Evidence confirms announcement in 2024.
        -> Result: VERIFIED, TemporalStatus: HISTORICAL_TRUE (because claim itself is historical).
    - Does NOT assume every date is current.
    """

    DISCONTINUATION_KEYWORDS: Set[str] = {
        "discontinued",
        "scrapped",
        "terminated",
        "repealed",
        "revoked",
        "withdrawn",
        "no longer in effect",
        "rescinded",
    }

    SUNSET_KEYWORDS: Set[str] = {
        "suspended till",
        "suspended until",
        "valid till",
        "valid until",
        "valid through",
        "expired",
        "sunset",
        "ended on",
        "concluded on",
    }

    PRESENT_INDICATORS: Set[str] = {
        "currently",
        "presently",
        "active now",
        "today",
        "tomorrow",
        "starting tomorrow",
        "as of today",
        "at present",
        "right now",
        "ongoing",
        "is active",
    }

    HISTORICAL_VERBS: Set[str] = {
        "announced",
        "launched",
        "notified",
        "introduced",
        "passed",
        "ordered",
        "declared",
        "enacted",
    }

    def __init__(self) -> None:
        pass

    def extract_dates(
        self,
        claim_text: str,
        evidence_items: List[Union[TemporalEvidenceItem, EvidenceItem, LockedEvidenceItem, Dict[str, Any], str]],
        current_date_str: Optional[str] = None,
    ) -> ExtractedTemporalDates:
        """
        Extracts claim date, evidence date, effective date, expiry date, and current date.
        Never assumes every date is current.
        """
        now_date = current_date_str or date.today().isoformat()
        current_year_num = int(self._extract_year_number(now_date) or 2026)

        # 1. Extract from claim
        claim_lower = claim_text.lower()
        claim_years = re.findall(r"\b(19\d\d|20\d\d)\b", claim_text)
        claim_date = claim_years[0] if claim_years else None

        # Check if historical claim (e.g. "Government announced X in 2024")
        is_historical = False
        if claim_date:
            claim_year_num = int(self._extract_year_number(claim_date) or 0)
            if claim_year_num < current_year_num:
                # Prior year claim
                for verb in self.HISTORICAL_VERBS:
                    if f"{verb} in {claim_date}" in claim_lower or f"{verb} x in {claim_date}" in claim_lower or f"{verb}" in claim_lower:
                        is_historical = True
                        break
                if f"in {claim_date}" in claim_lower or f"during {claim_date}" in claim_lower:
                    is_historical = True

        # Check if present claim (e.g. "currently gives", "starting tomorrow")
        is_present = any(ind in claim_lower for ind in self.PRESENT_INDICATORS)
        if not is_historical and not is_present:
            # Present tense verb forms default to present scope if not explicit historical
            if any(w in claim_lower for w in ["currently", "gives", "is", "provides", "tomorrow"]) or not claim_date:
                is_present = True

        # 2. Extract from evidence items
        parsed_evidence = [self._normalize_evidence_item(e) for e in evidence_items]

        evidence_dates: List[str] = []
        effective_dates: List[str] = []
        expiry_dates: List[str] = []

        for item in parsed_evidence:
            text_lower = item.text.lower()

            # Date of document
            if item.date:
                evidence_dates.append(str(item.date))
            else:
                doc_years = re.findall(r"\b(19\d\d|20\d\d)\b", item.text)
                if doc_years:
                    evidence_dates.append(doc_years[0])

            # Effective date
            if item.effective_date:
                effective_dates.append(str(item.effective_date))
            else:
                eff_match = re.search(r"(?:effective from|with effect from|notified on|launched on)\s+([A-Za-z0-9, /-]+)", text_lower)
                if eff_match:
                    eff_val = self._extract_first_year_or_date(eff_match.group(1))
                    if eff_val:
                        effective_dates.append(eff_val)

            # Expiry or discontinuation date
            if item.expiry_date:
                expiry_dates.append(str(item.expiry_date))
            else:
                for disc_word in (self.DISCONTINUATION_KEYWORDS | self.SUNSET_KEYWORDS):
                    if disc_word in text_lower:
                        disc_match = re.search(rf"{re.escape(disc_word)}\s+(?:in|on|till|until)?\s*([A-Za-z0-9, /-]+)", text_lower)
                        if disc_match:
                            disc_val = self._extract_first_year_or_date(disc_match.group(1))
                            if disc_val:
                                expiry_dates.append(disc_val)
                                break
                        years = re.findall(r"\b(19\d\d|20\d\d)\b", item.text)
                        if years:
                            expiry_dates.append(years[-1])
                            break

        # Primary evidence date (highest / latest publication date)
        latest_ev_date = sorted(evidence_dates, key=self._date_sort_key)[-1] if evidence_dates else None
        earliest_eff_date = sorted(effective_dates, key=self._date_sort_key)[0] if effective_dates else None
        latest_exp_date = sorted(expiry_dates, key=self._date_sort_key)[-1] if expiry_dates else None

        return ExtractedTemporalDates(
            claim_date=claim_date,
            evidence_date=latest_ev_date,
            effective_date=earliest_eff_date,
            expiry_date=latest_exp_date,
            current_date=now_date,
            is_historical_claim=is_historical,
            is_present_claim=is_present,
        )

    def verify_temporality(
        self,
        claim_text: str,
        evidence_items: List[Union[TemporalEvidenceItem, EvidenceItem, LockedEvidenceItem, Dict[str, Any], str]],
        current_date_str: Optional[str] = None,
    ) -> TemporalVerificationResult:
        """
        Executes complete temporal verification.
        Distinguishes TRUE THEN from TRUE NOW.
        """
        now_date = current_date_str or date.today().isoformat()
        current_year = int(self._extract_year_number(now_date) or 2026)

        parsed_items = [self._normalize_evidence_item(e) for e in evidence_items]
        dates = self.extract_dates(claim_text, parsed_items, now_date)

        # 1. No evidence provided -> DATE_UNKNOWN
        if not parsed_items:
            return TemporalVerificationResult(
                temporal_status=TemporalStatus.DATE_UNKNOWN,
                verdict=Verdict.CANNOT_BE_CONFIRMED,
                true_then=False,
                true_now=False,
                dates=dates,
                explanation="No evidence records available to verify timeline.",
            )

        # 2. Check if claim itself is HISTORICAL (Example 2)
        # Claim: "Government announced X in 2024."
        # Evidence confirms announcement in 2024.
        # -> VERIFIED, HISTORICAL_TRUE
        if dates.is_historical_claim and dates.claim_date:
            claim_year = int(self._extract_year_number(dates.claim_date) or 0)
            # Find evidence confirming the historical event in that year
            matching_historical = [
                item for item in parsed_items
                if self._extract_year_number(item.date or item.text) == str(claim_year)
                or f"in {claim_year}" in item.text.lower()
                or f"{claim_year}" in item.text
            ]
            if matching_historical:
                return TemporalVerificationResult(
                    temporal_status=TemporalStatus.HISTORICAL_TRUE,
                    verdict=Verdict.VERIFIED,
                    true_then=True,
                    true_now=True,
                    dates=dates,
                    explanation=(
                        f"Claim specifically asserts a historical occurrence in {dates.claim_date}. "
                        f"Authoritative records confirm the event transpired in {dates.claim_date}. "
                        "The assertion is factually verified as historical truth."
                    ),
                )

        # 3. Check for Chronological Timeline Contradiction / Supersession (Example 1)
        # Evidence 2024: "Scheme X gives ₹10,000."
        # Evidence 2026: "Scheme X was discontinued in 2025."
        # Claim: "Scheme X currently gives ₹10,000."
        # -> OUTDATED, CONTRADICTED_BY_NEWER_EVIDENCE
        # Does NOT apply to permanent origin/immutable facts (e.g. "UPI was developed by NPCI")
        origin_relation_words = {
            "developed", "founded", "created", "invented", "designed",
            "national animal", "established by", "origin",
        }
        is_immutable_fact = any(r in claim_text.lower() for r in origin_relation_words)

        has_discontinuation = False
        discontinuation_year: Optional[int] = None
        discontinuation_text = ""

        supporting_older_evidence = False
        older_year: Optional[int] = None

        if not is_immutable_fact:
            for item in parsed_items:
                item_year_str = self._extract_year_number(item.date or item.text)
                item_year = int(item_year_str) if item_year_str else None
                text_lower = item.text.lower()

                # Check if this item reports discontinuation / repeal of the specific subject
                if any(k in text_lower for k in self.DISCONTINUATION_KEYWORDS):
                    has_discontinuation = True
                    disc_years = re.findall(r"\b(19\d\d|20\d\d)\b", item.text)
                    discontinuation_year = int(disc_years[-1]) if disc_years else item_year
                    discontinuation_text = item.text
                else:
                    # Corroborating older record
                    if item_year and item_year < current_year:
                        supporting_older_evidence = True
                        older_year = item_year

        if has_discontinuation and (supporting_older_evidence or len(parsed_items) >= 2):
            # True then (in older year), but False now!
            exp_str = str(discontinuation_year) if discontinuation_year else "subsequent circular"
            return TemporalVerificationResult(
                temporal_status=TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE,
                verdict=Verdict.OUTDATED,
                true_then=True,
                true_now=False,
                dates=dates,
                explanation=(
                    f"Policy was authentic in {older_year or 'earlier records'} (TRUE THEN), "
                    f"but was discontinued/superseded in {exp_str} according to newer evidence (NOT TRUE NOW). "
                    "Claim asserting ongoing currency is OUTDATED."
                ),
            )

        # 4. Check for Expiry / Sunset threshold
        if dates.expiry_date:
            exp_year = int(self._extract_year_number(dates.expiry_date) or 0)
            if exp_year and exp_year < current_year:
                return TemporalVerificationResult(
                    temporal_status=TemporalStatus.EXPIRED,
                    verdict=Verdict.OUTDATED,
                    true_then=True,
                    true_now=False,
                    dates=dates,
                    explanation=(
                        f"Order or policy had a designated validity period that expired in {dates.expiry_date}. "
                        f"It is no longer in force as of reference date {dates.current_date}."
                    ),
                )

        # 5. Check for Historical Recirculation Mismatch (Older order with no ongoing proof)
        # E.g. Claim asserts "Railways ordered suspension starting tomorrow", but evidence date is 2020
        # Does NOT apply to timeless facts, permanent attributes, or origin relations (e.g. "UPI was developed by NPCI")
        temporary_order_words = {
            "tomorrow", "starting tomorrow", "today", "effective from tomorrow",
            "curfew", "lockdown", "holiday", "shutdown", "shut down", "suspension",
            "suspended", "trains cancelled", "cancelled", "postponed", "banned from tomorrow",
            "closed tomorrow", "banned tomorrow",
        }
        claim_asserts_temporary_order = any(w in claim_text.lower() for w in temporary_order_words)

        if dates.evidence_date and claim_asserts_temporary_order:
            ev_year = int(self._extract_year_number(dates.evidence_date) or 0)
            if ev_year and (current_year - ev_year >= 2):
                return TemporalVerificationResult(
                    temporal_status=TemporalStatus.EXPIRED,
                    verdict=Verdict.OUTDATED,
                    true_then=True,
                    true_now=False,
                    dates=dates,
                    explanation=(
                        f"Authentic document originated in {dates.evidence_date} (TRUE THEN), "
                        f"but is being deceptively recirculated in {current_year} out of context. "
                        "No such order is active for the current calendar period."
                    ),
                )

        # 6. Current active policy / fact
        if dates.evidence_date:
            return TemporalVerificationResult(
                temporal_status=TemporalStatus.CURRENT,
                verdict=Verdict.VERIFIED,
                true_then=True,
                true_now=True,
                dates=dates,
                explanation=(
                    f"Verified against active statutory records (issuance {dates.evidence_date}). "
                    "No newer revoking circulars or expiration triggers detected."
                ),
            )

        # 7. Fallback if no dates detected
        return TemporalVerificationResult(
            temporal_status=TemporalStatus.DATE_UNKNOWN,
            verdict=Verdict.CANNOT_BE_CONFIRMED,
            true_then=False,
            true_now=False,
            dates=dates,
            explanation="Could not establish chronological alignment due to absent temporal metadata.",
        )

    def _normalize_evidence_item(
        self,
        evidence: Union[TemporalEvidenceItem, EvidenceItem, LockedEvidenceItem, Dict[str, Any], str],
    ) -> TemporalEvidenceItem:
        """Converts diverse evidence inputs into a standardized TemporalEvidenceItem."""
        if isinstance(evidence, TemporalEvidenceItem):
            return evidence

        if isinstance(evidence, EvidenceItem):
            return TemporalEvidenceItem(
                evidence_id=evidence.id,
                text=evidence.exact_quote,
                date=evidence.publish_date,
            )

        if isinstance(evidence, LockedEvidenceItem):
            return TemporalEvidenceItem(
                evidence_id="ev_locked",
                text=evidence.exact_quote,
                date=evidence.published_date,
            )

        if isinstance(evidence, dict):
            return TemporalEvidenceItem(
                evidence_id=str(evidence.get("evidence_id") or evidence.get("id") or "ev_001"),
                text=str(evidence.get("text") or evidence.get("exact_quote") or evidence.get("quote") or ""),
                date=evidence.get("date") or evidence.get("published_date") or evidence.get("publish_date"),
                effective_date=evidence.get("effective_date"),
                expiry_date=evidence.get("expiry_date"),
            )

        return TemporalEvidenceItem(
            text=str(evidence),
            date=None,
        )

    def _extract_year_number(self, text: Optional[str]) -> Optional[str]:
        """Extracts 4-digit year string."""
        if not text:
            return None
        years = re.findall(r"\b(19\d\d|20\d\d)\b", str(text))
        return years[0] if years else None

    def _extract_first_year_or_date(self, text: str) -> Optional[str]:
        """Extracts first year or date token."""
        years = re.findall(r"\b(19\d\d|20\d\d)\b", text)
        if years:
            return years[0]
        dates = re.findall(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", text)
        return dates[0] if dates else None

    def _date_sort_key(self, date_str: str) -> str:
        """Key for chronological string sorting."""
        year = self._extract_year_number(date_str)
        return year if year else date_str


# Default singleton instance
temporal_verification_service = TemporalVerificationService()
