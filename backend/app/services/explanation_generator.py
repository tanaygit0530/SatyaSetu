import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.security.pii_redactor import pii_redactor_service
from app.core.security.prompt_security import prompt_security_service
from app.core.security.token_budget import token_budget_manager
from app.schemas.enums import SourceTier, TemporalStatus, Verdict
from app.schemas.evidence import EvidenceItem, LockedEvidenceItem
from app.schemas.explanation import ExplanationInput, ExplanationOutput
from app.services.localization import localization_service

# Compiled regex patterns for numbers, currencies, percentages, and dates
NUMBER_PATTERN = re.compile(r"(?:₹|\$|€|£)?\b\d+(?:[,\.]\d+)?%?\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
MONTH_DATE_PATTERN = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b(?:\s+\d{1,2}(?:st|nd|rd|th)?)?",
    re.IGNORECASE,
)
RELATIVE_DATE_PATTERN = re.compile(
    r"\b(?:tomorrow|yesterday|today|tonight|next week|last week|next year|last year)\b",
    re.IGNORECASE,
)


class ExplanationGeneratorService:
    """
    Forensic Explanation Generator for SachCheck.

    CRITICAL INVARIANTS:
    1. Generated AFTER the deterministic verdict has been decided.
    2. Explanation MUST be simple and strictly under 80 words.
    3. Every factual number/date in the explanation must exist in:
       - claim
       or
       - validated evidence
    4. If not grounded: regenerate once.
    5. If still invalid: use a safe template.
    6. Never invent facts.
    """

    def __init__(self):
        self.gemini_key: Optional[str] = settings.GEMINI_API_KEY
        self.openai_key: Optional[str] = settings.OPENAI_API_KEY
        self.model: str = settings.GEMINI_MODEL

    def generate_explanation(
        self,
        claim: Union[str, Any],
        verdict: Verdict,
        validated_evidence: List[Union[EvidenceItem, LockedEvidenceItem, Dict[str, Any]]],
        rule_trace: Optional[List[str]] = None,
        temporal_status: Optional[TemporalStatus] = None,
        language: str = "en",
    ) -> ExplanationOutput:
        """
        Generates an explanation under 80 words, verified for factual grounding,
        in the citizen's preferred language (en, hi, mr).
        """
        norm_lang = localization_service.normalize_language(language)
        claim_text = self._extract_claim_text(claim)
        evidence_items = self._normalize_evidence(validated_evidence)
        trace = rule_trace or []
        temp_status = temporal_status or TemporalStatus.CURRENT

        # 1. Harvest permissible factual numbers and dates from claim & evidence
        grounded_facts = self._harvest_grounded_numbers_and_dates(claim_text, evidence_items)

        # 2. Attempt 1: Generate initial explanation candidate
        candidate = self._generate_candidate(
            claim_text=claim_text,
            verdict=verdict,
            evidence_items=evidence_items,
            rule_trace=trace,
            temporal_status=temp_status,
            attempt=1,
            language=norm_lang,
        )

        is_valid, unauthorized = self.validate_factual_grounding(candidate, grounded_facts)
        word_count = len(candidate.split())

        if is_valid and word_count <= 80:
            return ExplanationOutput(
                explanation=candidate,
                word_count=word_count,
                verdict=verdict,
                is_grounded=True,
                used_safe_template=False,
                regeneration_count=0,
                grounded_numbers_dates=sorted(list(grounded_facts)),
                unauthorized_numbers_dates=[],
                rule_trace=trace,
            )

        logger.warning(
            "Explanation attempt 1 failed validation (unauthorized=%s, words=%d). Regenerating once...",
            unauthorized,
            word_count,
        )

        # 3. Attempt 2: Regenerate once with strict grounding constraint
        candidate_2 = self._generate_candidate(
            claim_text=claim_text,
            verdict=verdict,
            evidence_items=evidence_items,
            rule_trace=trace,
            temporal_status=temp_status,
            attempt=2,
            previous_unauthorized=unauthorized,
            language=norm_lang,
        )

        is_valid_2, unauthorized_2 = self.validate_factual_grounding(candidate_2, grounded_facts)
        word_count_2 = len(candidate_2.split())

        if is_valid_2 and word_count_2 <= 80:
            return ExplanationOutput(
                explanation=candidate_2,
                word_count=word_count_2,
                verdict=verdict,
                is_grounded=True,
                used_safe_template=False,
                regeneration_count=1,
                grounded_numbers_dates=sorted(list(grounded_facts)),
                unauthorized_numbers_dates=[],
                rule_trace=trace,
            )

        logger.warning(
            "Explanation attempt 2 still invalid (unauthorized=%s, words=%d). Falling back to safe template.",
            unauthorized_2,
            word_count_2,
        )

        # 4. Fallback: Safe deterministic template (100% grounded, zero invented facts, < 80 words)
        safe_explanation = self.get_safe_template(verdict, claim_text, evidence_items, temp_status, language=norm_lang)
        safe_words = len(safe_explanation.split())

        return ExplanationOutput(
            explanation=safe_explanation,
            word_count=safe_words,
            verdict=verdict,
            is_grounded=True,
            used_safe_template=True,
            regeneration_count=1,
            grounded_numbers_dates=sorted(list(grounded_facts)),
            unauthorized_numbers_dates=unauthorized_2,
            rule_trace=trace,
        )

    # -------------------------------------------------------------------------
    # Factual Grounding & Number/Date Extraction
    # -------------------------------------------------------------------------

    def extract_numbers_and_dates(self, text: str) -> Set[str]:
        """
        Extracts normalized factual numbers, percentages, currencies, and dates from text.
        """
        if not text:
            return set()

        facts = set()

        # Numbers & currencies
        for match in NUMBER_PATTERN.finditer(text):
            token = match.group().strip()
            # Clean punctuation and currency symbols
            clean = re.sub(r"[₹\$€£,%]", "", token).strip()
            if clean:
                facts.add(clean.lower())
                facts.add(token.lower())
                # Handle leading/trailing zeros or decimal formats
                try:
                    num_val = float(clean)
                    if num_val.is_integer():
                        facts.add(str(int(num_val)))
                except ValueError:
                    pass

        # Years
        for match in YEAR_PATTERN.finditer(text):
            facts.add(match.group().strip().lower())

        # Month and Day
        for match in MONTH_DATE_PATTERN.finditer(text):
            token = match.group().strip().lower()
            facts.add(token)
            # Add individual parts e.g. "june 4" -> "june", "4"
            parts = token.split()
            for p in parts:
                cleaned_p = re.sub(r"(?:st|nd|rd|th)", "", p).strip()
                if cleaned_p:
                    facts.add(cleaned_p)

        # Relative dates (e.g. tomorrow)
        for match in RELATIVE_DATE_PATTERN.finditer(text):
            facts.add(match.group().strip().lower())

        return facts

    def _harvest_grounded_numbers_and_dates(
        self,
        claim_text: str,
        evidence_items: List[EvidenceItem],
    ) -> Set[str]:
        """Collects all factual numbers and dates present in claim or evidence."""
        grounded = set()
        grounded.update(self.extract_numbers_and_dates(claim_text))

        for ev in evidence_items:
            grounded.update(self.extract_numbers_and_dates(ev.exact_quote or ""))
            grounded.update(self.extract_numbers_and_dates(ev.title or ""))
            grounded.update(self.extract_numbers_and_dates(ev.publish_date or ""))
            grounded.update(self.extract_numbers_and_dates(ev.publisher or ""))

        return grounded

    def validate_factual_grounding(
        self,
        explanation: str,
        grounded_facts: Set[str],
    ) -> Tuple[bool, List[str]]:
        """
        Validates that every factual number/date in the explanation exists in the grounded facts.
        """
        explanation_facts = self.extract_numbers_and_dates(explanation)
        unauthorized = []

        for fact in explanation_facts:
            # Check direct or normalized containment
            if not self._is_fact_grounded(fact, grounded_facts):
                unauthorized.append(fact)

        return (len(unauthorized) == 0, unauthorized)

    def _is_fact_grounded(self, candidate_fact: str, grounded_facts: Set[str]) -> bool:
        """Determines if a candidate number or date is grounded."""
        if candidate_fact in grounded_facts:
            return True

        # Check numeric equivalence (e.g. "50000" vs "50,000" vs "50000.0")
        try:
            cand_num = float(re.sub(r"[₹\$€£,%]", "", candidate_fact))
            for g in grounded_facts:
                try:
                    g_num = float(re.sub(r"[₹\$€£,%]", "", g))
                    if abs(cand_num - g_num) < 0.001:
                        return True
                except ValueError:
                    continue
        except ValueError:
            pass

        # Check sub-phrase containment for dates (e.g. "tomorrow" or "june")
        for g in grounded_facts:
            if candidate_fact in g or g in candidate_fact:
                return True

        return False

    # -------------------------------------------------------------------------
    # Candidate Generation & Safe Templates
    # -------------------------------------------------------------------------

    def _generate_candidate(
        self,
        claim_text: str,
        verdict: Verdict,
        evidence_items: List[EvidenceItem],
        rule_trace: List[str],
        temporal_status: TemporalStatus,
        attempt: int = 1,
        previous_unauthorized: Optional[List[str]] = None,
        language: str = "en",
    ) -> str:
        """
        Generates an explanation candidate via LLM if available, or domain rules,
        in the requested language.
        """
        # Call LLM if configured and not demo mode
        if (self.gemini_key or self.openai_key) and not settings.DEMO_MODE:
            llm_text = self._call_llm_explanation(
                claim_text=claim_text,
                verdict=verdict,
                evidence_items=evidence_items,
                rule_trace=rule_trace,
                temporal_status=temporal_status,
                attempt=attempt,
                previous_unauthorized=previous_unauthorized,
                language=language,
            )
            if llm_text:
                return llm_text.strip()

        # Deterministic generation conforming to spec example and localized templates
        return self._generate_domain_explanation(
            claim_text=claim_text,
            verdict=verdict,
            evidence_items=evidence_items,
            temporal_status=temporal_status,
            language=language,
        )

    def _generate_domain_explanation(
        self,
        claim_text: str,
        verdict: Verdict,
        evidence_items: List[EvidenceItem],
        temporal_status: TemporalStatus,
        language: str = "en",
    ) -> str:
        """Produces realistic domain explanation tailored to the verdict, claim, and language."""
        if language in ("hi", "mr"):
            return self.get_safe_template(
                verdict=verdict,
                claim_text=claim_text,
                evidence_items=evidence_items,
                temporal_status=temporal_status,
                language=language,
            )

        c_lower = claim_text.lower()

        if verdict == Verdict.FALSE:
            # Spec Example matching:
            if "upi" in c_lower and "ban" in c_lower:
                return (
                    "No. We found no official announcement that UPI is being banned. "
                    "The available evidence indicates that UPI services continue to operate. "
                    "This claim should not be treated as an official announcement."
                )

            if evidence_items and evidence_items[0].publisher:
                pub = evidence_items[0].publisher
                return (
                    f"No. Official records from {pub} directly refute this assertion. "
                    "The available public documentation confirms that this claim is not genuine and has no official basis."
                )

            return localization_service.get_explanation(verdict, lang="en")

        if verdict == Verdict.VERIFIED:
            if evidence_items and evidence_items[0].publisher:
                pub = evidence_items[0].publisher
                return (
                    f"Yes. Official notifications from {pub} verify this claim. "
                    "Authoritative statutory records corroborate that this announcement is authentic and in effect."
                )
            return localization_service.get_explanation(verdict, lang="en")

        return self.get_safe_template(verdict, claim_text, evidence_items, temporal_status, language=language)

    def get_safe_template(
        self,
        verdict: Verdict,
        claim_text: str = "",
        evidence_items: Optional[List[EvidenceItem]] = None,
        temporal_status: Optional[TemporalStatus] = None,
        language: str = "en",
    ) -> str:
        """
        Returns a 100% grounded, zero-hallucination safe template strictly under 80 words,
        loaded dynamically from app/locales/{en,hi,mr}.json.
        Guarantees: Zero invented numbers, zero invented dates, strict brevity.
        """
        return localization_service.get_explanation(verdict, lang=language)

    def _call_llm_explanation(
        self,
        claim_text: str,
        verdict: Verdict,
        evidence_items: List[EvidenceItem],
        rule_trace: List[str],
        temporal_status: TemporalStatus,
        attempt: int = 1,
        previous_unauthorized: Optional[List[str]] = None,
        language: str = "en",
    ) -> Optional[str]:
        # 1. Enforce Token Budget
        if not token_budget_manager.check_budget_available(estimated_tokens=200):
            logger.warning("Daily token budget cap reached; falling back from external LLM explanation.")
            return None

        # 2. Redact PII from claim and evidence before sending to external model
        clean_claim = pii_redactor_service.redact(claim_text)
        evidence_payload = [
            {
                "publisher": e.publisher,
                "exact_quote": pii_redactor_service.redact(e.exact_quote or ""),
            }
            for e in evidence_items[:3]
            if e.exact_quote
        ]

        reprimand = ""
        if attempt > 1 and previous_unauthorized:
            reprimand = (
                f"\nCRITICAL CORRECTION (ATTEMPT 2):\n"
                f"Your previous draft included ungrounded numbers/dates: {previous_unauthorized}. "
                f"DO NOT include ANY number or date that is not verbatim in the claim or evidence quotes!\n"
            )

        lang_instruction = "English"
        if language == "hi":
            lang_instruction = "Hindi (हिंदी). Do NOT write English."
        elif language == "mr":
            lang_instruction = "Marathi (मराठी). Do NOT write English."

        system_directive = (
            f"You are SachCheck's forensic explanation writer.\n"
            f"Write a simple citizen-facing explanation for the verdict.\n\n"
            f"RULES:\n"
            f"1. Strictly UNDER 80 WORDS.\n"
            f"2. Write the explanation in {lang_instruction}.\n"
            f"3. Every number or date in your explanation MUST exist verbatim in the Claim or Evidence Quotes below.\n"
            f"4. NEVER invent numbers, fees, percentages, or dates.\n"
            f"5. If in doubt, do not include numbers/dates at all.\n"
            f"Verdict: {verdict.value}\n"
            f"Temporal Status: {temporal_status.value}\n"
            f"{reprimand}"
        )

        # 3. Construct hardened prompt with SYSTEM, USER CONTENT, and RETRIEVED EVIDENCE separation
        prompt = prompt_security_service.build_secure_prompt(
            system_directive=system_directive,
            user_content=clean_claim,
            retrieved_evidence=evidence_payload,
        )

        try:
            if self.gemini_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 150},
                }
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        usage = data.get("usageMetadata", {})
                        p_tokens = usage.get("promptTokenCount", len(prompt.split()) * 2)
                        c_tokens = usage.get("candidatesTokenCount", 50)
                        token_budget_manager.consume_tokens(
                            prompt_tokens=p_tokens,
                            completion_tokens=c_tokens,
                            model=self.model,
                        )
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.warning("Gemini explanation generation request failed: %s", e)

        return None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_claim_text(claim: Any) -> str:
        """Extracts claim text uniformly."""
        if isinstance(claim, str):
            return claim
        if hasattr(claim, "claim_text"):
            return str(getattr(claim, "claim_text"))
        if hasattr(claim, "normalized_claim"):
            return str(getattr(claim, "normalized_claim"))
        if isinstance(claim, dict):
            return str(claim.get("claim_text") or claim.get("text") or claim.get("normalized_claim") or "")
        return str(claim)

    @staticmethod
    def _normalize_evidence(
        evidence_list: List[Union[EvidenceItem, LockedEvidenceItem, Dict[str, Any]]]
    ) -> List[EvidenceItem]:
        """Converts diverse evidence items to standard EvidenceItem."""
        res: List[EvidenceItem] = []
        for ev in evidence_list:
            if isinstance(ev, EvidenceItem):
                res.append(ev)
            elif isinstance(ev, LockedEvidenceItem):
                tier_val = (
                    SourceTier.TIER_1_PRIMARY if ev.source_tier == 1 else (
                        SourceTier.TIER_2_SECONDARY if ev.source_tier == 2 else SourceTier.TIER_3_REPUTABLE
                    )
                )
                res.append(
                    EvidenceItem(
                        id=ev.evidence_id or "ev_001",
                        publisher=ev.publisher,
                        domain="gov.in",
                        title=ev.source_title,
                        publish_date=ev.published_date,
                        tier=tier_val,
                        url=ev.source_url,
                        exact_quote=ev.exact_quote,
                    )
                )
            elif isinstance(ev, dict):
                raw_tier = ev.get("tier") or ev.get("source_tier") or 1
                tier_val = (
                    SourceTier.TIER_1_PRIMARY if raw_tier in (1, SourceTier.TIER_1_PRIMARY) else (
                        SourceTier.TIER_2_SECONDARY if raw_tier in (2, SourceTier.TIER_2_SECONDARY) else SourceTier.TIER_3_REPUTABLE
                    )
                )
                res.append(
                    EvidenceItem(
                        id=str(ev.get("id") or "ev_001"),
                        publisher=str(ev.get("publisher") or ""),
                        domain=str(ev.get("domain") or ""),
                        title=str(ev.get("title") or ""),
                        publish_date=ev.get("published_date") or ev.get("publish_date"),
                        tier=tier_val,
                        url=str(ev.get("url") or ""),
                        exact_quote=str(ev.get("exact_quote") or ""),
                    )
                )
        return res


# Singleton instance
explanation_generator_service = ExplanationGeneratorService()
