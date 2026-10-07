import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.claim import ExtractedClaim
from app.schemas.enums import SourceTier, TemporalStatus, Verdict
from app.schemas.evidence import EvidenceInterpretation, EvidenceItem, LockedEvidenceItem
from app.schemas.judge import (
    EvidenceAssessmentLevel,
    EvidenceJudgeAssessment,
    EvidenceStance,
)
from app.services.rule_engine import DeterministicRuleEngine


client = TestClient(app)


# Helper to build mock evidence
def make_evidence(id="ev_001", publisher="PIB", tier=SourceTier.TIER_1_PRIMARY, quote="Quote", url=None, domain=None):
    if tier == SourceTier.TIER_1_PRIMARY:
        d = domain or "pib.gov.in"
    elif tier == SourceTier.TIER_2_SECONDARY:
        d = domain or "regulatory.org.in"
    else:
        d = domain or "newsblog.com"
    u = url or f"https://{d}/doc"
    return EvidenceItem(
        id=id,
        publisher=publisher,
        domain=d,
        title=f"Doc {id}",
        tier=tier,
        url=u,
        exact_quote=quote,
    )


# ==============================================================================
# SECTION 1: 10 VERIFIED CASES
# ==============================================================================

def test_verified_case_1_tier1_gazette():
    """Case 1: Tier 1 Official Gazette notification corroborates claim."""
    claim = "Ministry of Education notified PM Higher Merit Scholarship for 2026."
    ev = [make_evidence(quote="Continuation of PM Higher Merit Scholarship is officially notified.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        temporal_status=TemporalStatus.CURRENT,
        agreement=1.0,
    )
    assert res.verdict == Verdict.VERIFIED
    assert "TIER_1_SOURCE_PRESENT" in res.rule_trace
    assert "CREDIBLE_CORROBORATION" in res.rule_trace


def test_verified_case_2_historical_true():
    """Case 2: Historical claim verified by historical evidence."""
    claim = "Government announced Scheme X in 2024."
    ev = [make_evidence(quote="Government announced Scheme X on June 4, 2024.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.SUPPORTS, reason="Confirms announcement")]
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        evidence_judgments=judgments,
        temporal_status=TemporalStatus.HISTORICAL_TRUE,
    )
    assert res.verdict == Verdict.VERIFIED
    assert "HISTORICAL_TRUE_EVIDENCE" in res.rule_trace


def test_verified_case_3_tier2_regulatory_confirmation():
    """Case 3: Tier 2 IFCN Fact Checker confirms policy announcement."""
    claim = "State Government announced new scholarship scheme for diploma students."
    ev = [make_evidence(publisher="BOOM Live", tier=SourceTier.TIER_2_SECONDARY, domain="boomlive.in", quote="BOOM fact check confirms state education department circular is genuine.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        source_tiers=[2],
        temporal_status=TemporalStatus.CURRENT,
        agreement=1.0,
    )
    assert res.verdict == Verdict.VERIFIED
    assert "TIER_2_SOURCE_PRESENT" in res.rule_trace


def test_verified_case_4_multiple_concurring_tier1_sources():
    """Case 4: Two concurring Tier-1 statutory sources."""
    ev = [
        make_evidence(id="ev_01", publisher="The Gazette of India", quote="Act officially passed and gazetted."),
        make_evidence(id="ev_02", publisher="PIB Fact Check", quote="PIB confirms gazette issuance."),
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim="New Consumer Protection Rules have been notified.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.CURRENT,
        agreement=1.0,
    )
    assert res.verdict == Verdict.VERIFIED
    assert res.confidence >= 98.0


def test_verified_case_5_judicial_decree():
    """Case 5: Supreme Court decree corroborates legal entitlement."""
    ev = [make_evidence(publisher="Supreme Court of India", domain="sci.gov.in", quote="The Court directs immediate implementation of pension parity.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.SUPPORTS, reason="Court directive confirms")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Supreme Court ordered pension parity for retired employees.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.VERIFIED


def test_verified_case_6_high_agreement_score():
    """Case 6: High agreement score (0.95) with recent evidence."""
    ev = [make_evidence(quote="State portal confirms drought relief disbursed.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Drought relief funds released to affected farmers.",
        validated_evidence=ev,
        agreement=0.95,
        recency="RECENT",
    )
    assert res.verdict == Verdict.VERIFIED


def test_verified_case_7_pib_fact_check_corroboration():
    """Case 7: PIB Fact Check confirming genuine notification."""
    ev = [make_evidence(publisher="PIB Fact Check", domain="pib.gov.in", quote="Notice issued by Indian Railways is genuine and verified.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.SUPPORTS, reason="Fact checker confirms genuine circular")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Railways issued notice regarding concession forms.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.VERIFIED


def test_verified_case_8_ugc_academic_circular():
    """Case 8: UGC circular confirming curriculum guideline."""
    ev = [make_evidence(publisher="University Grants Commission", tier=SourceTier.TIER_2_SECONDARY, domain="ugc.ac.in", quote="UGC notifies National Higher Education Qualifications Framework guidelines.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.SUPPORTS, reason="UGC guidelines confirmed")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="UGC approved new qualifications framework guidelines.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.VERIFIED


def test_verified_case_9_railway_press_bulletin():
    """Case 9: Railways press release confirming special trains."""
    ev = [make_evidence(publisher="Ministry of Railways", domain="indianrailways.gov.in", quote="Northern Railway will run 150 festival special trains.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.SUPPORTS, reason="Confirmed by Railways")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Railways announced festival special trains for Diwali.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.VERIFIED


def test_verified_case_10_high_retrieval_quality():
    """Case 10: High retrieval quality (0.95) with verified evidence citation."""
    ev = [make_evidence(quote="Department confirms sanction of 500 electric buses.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.SUPPORTS, reason="Sanction confirmed")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Cabinet sanctioned 500 electric buses for urban transit.",
        validated_evidence=ev,
        evidence_judgments=judgments,
        retrieval_quality=0.95,
    )
    assert res.verdict == Verdict.VERIFIED
    assert "QUOTE_VALIDATED" in res.rule_trace


# ==============================================================================
# SECTION 2: 10 FALSE CASES
# ==============================================================================

def test_false_case_1_spec_example_npci():
    """Case 1: Spec example - NPCI has not announced nationwide shutdown."""
    claim = "UPI is banned tomorrow."
    ev = [make_evidence(publisher="NPCI", domain="npci.org.in", quote="NPCI has not announced a nationwide shutdown.")]
    judgments = [
        EvidenceJudgeAssessment(
            evidence_id="ev_001",
            stance=EvidenceStance.CONTRADICTS,
            strength=EvidenceAssessmentLevel.HIGH,
            relevance=EvidenceAssessmentLevel.HIGH,
            reason="NPCI clarifies UPI remains fully operational.",
        )
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        evidence_judgments=judgments,
        contradiction_strength="HIGH",
        temporal_status=TemporalStatus.CURRENT,
    )
    assert res.verdict == Verdict.FALSE
    # Verify exact rule trace from spec
    assert res.rule_trace == ["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION", "QUOTE_VALIDATED", "CURRENT_EVIDENCE"]


def test_false_case_2_financial_discrepancy():
    """Case 2: Claim ₹50,000 vs actual ₹12,000."""
    claim = "Every student receives ₹50,000 lump sum DBT grant."
    ev = [make_evidence(quote="The rate of scholarship is Rs. 12,000 per annum.")]
    interp = EvidenceInterpretation(
        supports_claim=False,
        refutes_claim=True,
        claimed_amount=50000.0,
        actual_amount=12000.0,
    )
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        interpretation=interp,
    )
    assert res.verdict == Verdict.FALSE
    assert "STRONG_CONTRADICTION" in res.rule_trace


def test_false_case_3_malicious_phishing_link():
    """Case 3: Malicious fake scholarship website."""
    claim = "Apply for ₹50,000 scholarship at bit.ly/scholarship-2026."
    ev = [make_evidence(publisher="CERT-In", domain="cert-in.org.in", quote="Fraudulent phishing site mimicking National Scholarship Portal.")]
    interp = EvidenceInterpretation(
        supports_claim=False,
        refutes_claim=True,
        domain_flagged_malicious=True,
        discrepancy_explanation="CERT-In alert: fraudulent phishing link.",
    )
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        interpretation=interp,
    )
    assert res.verdict == Verdict.FALSE
    assert "MALICIOUS_DOMAIN_FLAGGED" in res.rule_trace


def test_false_case_4_currency_demonetization_hoax():
    """Case 4: RBI circular directly refutes currency withdrawal hoax."""
    ev = [make_evidence(publisher="RBI", domain="rbi.org.in", quote="RBI has not issued any instructions withdrawing ₹500 currency notes.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.CONTRADICTS, strength=EvidenceAssessmentLevel.HIGH, reason="RBI denies rumour")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="RBI is withdrawing 500 rupee notes from next Monday.",
        validated_evidence=ev,
        evidence_judgments=judgments,
        contradiction_strength="HIGH",
    )
    assert res.verdict == Verdict.FALSE


def test_false_case_5_direct_contradiction_param():
    """Case 5: Contradiction strength explicitly set to HIGH."""
    ev = [make_evidence(quote="Ministry clarifies no exam cancellation order was issued.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Board exams cancelled nationwide due to heatwave.",
        validated_evidence=ev,
        contradiction_strength="HIGH",
    )
    assert res.verdict == Verdict.FALSE
    assert "STRONG_CONTRADICTION" in res.rule_trace


def test_false_case_6_fake_recruitment_debunked():
    """Case 6: Indian Railways debunking fake recruitment notice."""
    ev = [make_evidence(publisher="PIB Fact Check", domain="pib.gov.in", quote="PIB Fact Check confirms the viral 50,000 railway vacancy circular is completely fake.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.CONTRADICTS, strength=EvidenceAssessmentLevel.HIGH, reason="PIB debunked fake job circular")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Railways released recruitment for 50,000 positions.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.FALSE


def test_false_case_7_disputed_fee_hike_denial():
    """Case 7: Official registrar denies university fee hike."""
    ev = [make_evidence(publisher="Delhi University", tier=SourceTier.TIER_2_SECONDARY, domain="du.ac.in", quote="University clarifies no proposal to hike tuition fees by 40% has been accepted.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.CONTRADICTS, strength=EvidenceAssessmentLevel.HIGH, reason="Registrar refutes fee hike")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Delhi University hiked undergraduate fees by 40%.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.FALSE


def test_false_case_8_election_schedule_hoax():
    """Case 8: Election Commission press note refuting fake polling dates."""
    ev = [make_evidence(publisher="Election Commission of India", domain="eci.gov.in", quote="ECI has not finalized poll dates; viral schedule on social media is fake.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.CONTRADICTS, strength=EvidenceAssessmentLevel.HIGH, reason="ECI confirms dates are fake")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Election Commission declared voting starts on 12th April.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.FALSE


def test_false_case_9_concurring_tier1_tier2_refutation():
    """Case 9: Concurring primary records debunking tax rumour."""
    ev = [
        make_evidence(id="ev_01", publisher="Ministry of Finance", quote="No transaction tax introduced on UPI transactions."),
        make_evidence(id="ev_02", publisher="NPCI", quote="UPI payments remain zero MDR for citizens."),
    ]
    judgments = [
        EvidenceJudgeAssessment(evidence_id="ev_01", stance=EvidenceStance.CONTRADICTS, reason="Finance Ministry refutes"),
        EvidenceJudgeAssessment(evidence_id="ev_02", stance=EvidenceStance.CONTRADICTS, reason="NPCI refutes"),
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Government imposed 5% tax on all UPI transactions.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.FALSE


def test_false_case_10_date_unknown_contradiction():
    """Case 10: Contradicted assertion with DATE_UNKNOWN temporal status."""
    ev = [make_evidence(quote="Primary statutory decree strictly denies this provision.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.CONTRADICTS, strength=EvidenceAssessmentLevel.HIGH, reason="Refuted")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Mandatory retirement age reduced to 55.",
        validated_evidence=ev,
        evidence_judgments=judgments,
        temporal_status=TemporalStatus.DATE_UNKNOWN,
    )
    assert res.verdict == Verdict.FALSE
    assert "DATE_UNKNOWN" in res.rule_trace


# ==============================================================================
# SECTION 3: 10 OUTDATED CASES
# ==============================================================================

def test_outdated_case_1_spec_example_discontinued():
    """Case 1: Spec example - Scheme discontinued in 2025."""
    claim = "Scheme X currently gives ₹10,000."
    ev = [
        make_evidence(id="ev_01", quote="Scheme X was discontinued in 2025 by subsequent gazette."),
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        temporal_status=TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE,
    )
    assert res.verdict == Verdict.OUTDATED
    assert "OUTDATED_SUPERSEDED" in res.rule_trace


def test_outdated_case_2_covid_lockdown_recirculation():
    """Case 2: 2020 COVID railway lockdown circular recirculated in 2026."""
    claim = "Railways ordered suspension of all passenger trains starting tomorrow."
    ev = [make_evidence(quote="Passenger train services suspended till 31st March 2020.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        temporal_status=TemporalStatus.EXPIRED,
    )
    assert res.verdict == Verdict.OUTDATED
    assert "EXPIRED_EVIDENCE" in res.rule_trace


def test_outdated_case_3_expired_tax_deadline():
    """Case 3: 2021 tax exemption deadline expired."""
    ev = [make_evidence(quote="One-time compliance window open till 31 December 2021.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Citizens can avail tax amnesty window right now.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.OUTDATED,
    )
    assert res.verdict == Verdict.OUTDATED


def test_outdated_case_4_superseded_building_code():
    """Case 4: Superseded 2016 building norms replaced by 2024 code."""
    ev = [make_evidence(quote="National Building Code 2016 repealed by Gazette notification 2024.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Builders only require self-certification under 2016 code.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE,
    )
    assert res.verdict == Verdict.OUTDATED


def test_outdated_case_5_historical_curfew_order():
    """Case 5: 2022 flood curfew order shared out of context in 2026."""
    ev = [make_evidence(quote="Curfew imposed across district from August 10 to August 14, 2022.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Curfew imposed across district starting tomorrow.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.OUTDATED,
    )
    assert res.verdict == Verdict.OUTDATED


def test_outdated_case_6_sunset_subsidy():
    """Case 6: FAME-II EV subsidy expired on March 31, 2024."""
    ev = [make_evidence(quote="FAME India Phase II subsidy concluded on 31 March 2024.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Government currently provides ₹25,000 FAME-II subsidy on two-wheelers.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.EXPIRED,
    )
    assert res.verdict == Verdict.OUTDATED


def test_outdated_case_7_interpretation_temporal_mismatch():
    """Case 7: EvidenceInterpretation with is_temporal_mismatch = True."""
    ev = [make_evidence(quote="Order issued in March 2020.")]
    interp = EvidenceInterpretation(
        supports_claim=False,
        is_temporal_mismatch=True,
        discrepancy_explanation="Archived 2020 order shared misleadingly.",
    )
    res = DeterministicRuleEngine.compute_verdict(
        claim="Schools shut down for nationwide lockdown.",
        validated_evidence=ev,
        interpretation=interp,
    )
    assert res.verdict == Verdict.OUTDATED


def test_outdated_case_8_exam_postponement_old_schedule():
    """Case 8: Old exam postponement notification superseded by fresh dates."""
    ev = [make_evidence(quote="UPSC examination postponed from May to September 2021.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Civil Services prelims exam postponed indefinitely.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.OUTDATED,
    )
    assert res.verdict == Verdict.OUTDATED


def test_outdated_case_9_telecom_advisory_superseded():
    """Case 9: 2019 telecom SIM limit advisory replaced by 2024 regulations."""
    ev = [make_evidence(quote="2019 DoT guidelines superseded by TAFCOP 2024 norms.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="DoT permits only 4 SIM cards per citizen under 2019 rules.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE,
    )
    assert res.verdict == Verdict.OUTDATED


def test_outdated_case_10_tier2_source_outdated():
    """Case 10: Tier 2 source circular expired."""
    ev = [make_evidence(tier=SourceTier.TIER_2_SECONDARY, publisher="CBSE", quote="Special term-1 board examination format restricted to academic year 2021-22.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="CBSE conducts bifurcated two-term board examinations.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.EXPIRED,
    )
    assert res.verdict == Verdict.OUTDATED
    assert "TIER_2_SOURCE_PRESENT" in res.rule_trace


# ==============================================================================
# SECTION 4: 10 PARTLY_SUPPORTED CASES
# ==============================================================================

def test_partly_supported_case_1_conditional_travel():
    """Case 1: Metro travel free for women, but not all citizens."""
    ev = [make_evidence(quote="Delhi metro free concession is applicable only for women and children under 5.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.MIXED, reason="Concession applies to women only, not everyone")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Delhi Metro is free for all commuters.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED
    assert "PARTIAL_SUPPORT" in res.rule_trace


def test_partly_supported_case_2_exaggerated_numbers():
    """Case 2: Core scheme exists, but claimed coverage is exaggerated."""
    ev = [make_evidence(quote="Scheme covers 50 lakh beneficiaries across 8 states.")]
    interp = EvidenceInterpretation(
        supports_claim=True,
        discrepancy_explanation="Scheme sanctioned for 50 lakh people, not entire population of 10 crore.",
    )
    res = DeterministicRuleEngine.compute_verdict(
        claim="Government launched universal income scheme for 10 crore citizens.",
        validated_evidence=ev,
        interpretation=interp,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED


def test_partly_supported_case_3_conflicting_agreement_ratio():
    """Case 3: Agreement ratio is 0.5 (50% agree, 50% disagree)."""
    ev = [make_evidence(quote="Independent review notes split findings across state units.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="New uniform power tariff adopted across all states.",
        validated_evidence=ev,
        agreement=0.5,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED
    assert "CONFLICTING_SOURCES" in res.rule_trace


def test_partly_supported_case_4_pilot_project_claimed_nationwide():
    """Case 4: Pilot project in 2 districts claimed as nationwide launch."""
    ev = [make_evidence(quote="Digital rupee trial launched as pilot in Mumbai and Bengaluru.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.MIXED, reason="Pilot trial only, not full launch")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Digital Rupee completely replaced cash nationwide.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED


def test_partly_supported_case_5_proposal_not_yet_funded():
    """Case 5: Cabinet approved in-principle, but funding not yet allocated."""
    ev = [make_evidence(quote="Cabinet granted in-principle approval subject to budget allocation next fiscal.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.MIXED, reason="In-principle approval only")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Government disbursed funds for high-speed rail corridor.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED


def test_partly_supported_case_6_selective_state_implementation():
    """Case 6: Implemented in 3 states, but claimed as all-India."""
    ev = [make_evidence(quote="Old pension scheme restored in Rajasthan, Chhattisgarh, and Himachal Pradesh.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.MIXED, reason="Restored in selected states only")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Old Pension Scheme restored for all central government employees.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED


def test_partly_supported_case_7_loan_waiver_limited_to_cooperatives():
    """Case 7: Loan waiver restricted to small cooperative banks, not nationalized banks."""
    ev = [make_evidence(quote="Farm loan waiver applies to loans up to ₹1 lakh from primary agricultural cooperative societies.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.MIXED, reason="Cooperative society loans only, capped at 1 lakh")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="All farmer loans in all banks completely waived.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED


def test_partly_supported_case_8_agreement_40_percent():
    """Case 8: Moderate agreement (0.4) indicating contested assertions."""
    ev = [make_evidence(quote="Data yields mixed outcomes.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="All EV charging stations offer free charging on weekends.",
        validated_evidence=ev,
        agreement=0.4,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED


def test_partly_supported_case_9_age_bracket_restricted():
    """Case 9: Senior citizen train concession restored only for 75+."""
    ev = [make_evidence(quote="Concession restored on select classes solely for super-senior citizens aged 75 and above.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.MIXED, reason="Restricted to 75+ age bracket")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Railways restored all senior citizen concessions for 60+ travelers.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED


def test_partly_supported_case_10_tier2_partial_support():
    """Case 10: Tier 2 source confirming partial elements."""
    ev = [make_evidence(tier=SourceTier.TIER_2_SECONDARY, publisher="AICTE", quote="Approval granted for hybrid learning in diploma courses, not undergraduate degrees.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.MIXED, reason="Applies to diploma only")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="AICTE approved online engineering degrees everywhere.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED
    assert "TIER_2_SOURCE_PRESENT" in res.rule_trace


# ==============================================================================
# SECTION 5: 10 CANNOT_BE_CONFIRMED CASES
# ==============================================================================

def test_cannot_confirm_case_1_empty_evidence():
    """Case 1: Zero evidence items retrieved."""
    res = DeterministicRuleEngine.compute_verdict(
        claim="Local municipal ward committee met yesterday.",
        validated_evidence=[],
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert "BELOW_EVIDENCE_THRESHOLD" in res.rule_trace
    assert "INSUFFICIENT_EVIDENCE" in res.rule_trace


def test_cannot_confirm_case_2_poor_retrieval_quality_str():
    """Case 2: Retrieval quality is 'POOR'."""
    ev = [make_evidence(quote="Unsubstantiated blog post.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Secret cabinet reshuffle announced.",
        validated_evidence=ev,
        retrieval_quality="POOR",
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED


def test_cannot_confirm_case_3_poor_retrieval_quality_numeric():
    """Case 3: Numeric retrieval quality score below threshold (0.2)."""
    ev = [make_evidence(quote="Vague fragment.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="New tax on cryptocurrency transactions.",
        validated_evidence=ev,
        retrieval_quality=0.2,
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED


def test_cannot_confirm_case_4_all_judgments_irrelevant():
    """Case 4: All evidence assessments evaluated as IRRELEVANT."""
    ev = [make_evidence(quote="Weather forecast indicates moderate rain.")]
    judgments = [EvidenceJudgeAssessment(evidence_id="ev_001", stance=EvidenceStance.IRRELEVANT, reason="Irrelevant topic")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Railways introduced bullet train on Mumbai route.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert "ALL_EVIDENCE_IRRELEVANT" in res.rule_trace


def test_cannot_confirm_case_5_failed_evidence_locking():
    """Case 5: All citations rejected by Evidence Locking grounding check."""
    ev = [make_evidence(quote="Fabricated quote not found in source text.")]
    source_texts = {"https://pib.gov.in/doc": "Completely different text without the quote."}
    res = DeterministicRuleEngine.compute_verdict(
        claim="Cabinet announced special bonus for postal employees.",
        validated_evidence=ev,
        source_texts=source_texts,
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert "QUOTE_VALIDATION_FAILED" in res.rule_trace


def test_cannot_confirm_case_6_no_authoritative_trail():
    """Case 6: No primary or secondary statutory records corroborate or refute."""
    claim = "Private company X will build a factory in town Y."
    ev = [make_evidence(tier=SourceTier.TIER_3_REPUTABLE, publisher="Local Blog", quote="Rumour heard at tea stall.")]
    res = DeterministicRuleEngine.compute_verdict(
        claim=claim,
        validated_evidence=ev,
        retrieval_quality="LOW",
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED


def test_cannot_confirm_case_7_unsubstantiated_whisper():
    """Case 7: Unsubstantiated whisper without documentary citations."""
    res = DeterministicRuleEngine.compute_verdict(
        claim="Chief Minister will resign before weekend.",
        validated_evidence=[],
        temporal_status=TemporalStatus.DATE_UNKNOWN,
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert res.confidence == 0.0


def test_cannot_confirm_case_8_all_evidence_below_threshold():
    """Case 8: Evidence items present but all marked low quality."""
    ev = [make_evidence(quote="Snippet")]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Unregistered scheme Z gives free bicycles.",
        validated_evidence=ev,
        retrieval_quality="INSUFFICIENT",
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED


def test_cannot_confirm_case_9_multiple_irrelevant_citations():
    """Case 9: Multiple retrieved sources, all irrelevant."""
    ev = [
        make_evidence(id="ev_1", quote="Cricket match scores."),
        make_evidence(id="ev_2", quote="Cinema box office update."),
    ]
    judgments = [
        EvidenceJudgeAssessment(evidence_id="ev_1", stance=EvidenceStance.IRRELEVANT, reason="Cricket"),
        EvidenceJudgeAssessment(evidence_id="ev_2", stance=EvidenceStance.IRRELEVANT, reason="Cinema"),
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Parliament passed amendment to tenancy act.",
        validated_evidence=ev,
        evidence_judgments=judgments,
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED


def test_cannot_confirm_case_10_do_not_guess():
    """Case 10: Rule engine strictly withholds judgment rather than guessing."""
    res = DeterministicRuleEngine.compute_verdict(
        claim="Speculative prediction about future policy next decade.",
        validated_evidence=[],
    )
    assert res.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert "BELOW_EVIDENCE_THRESHOLD" in res.rule_trace


# ==============================================================================
# SECTION 6: CONFLICTING SOURCES
# ==============================================================================

def test_conflicting_sources_tier1_overrides_tier3():
    """
    Conflicting Sources: Tier 1 government refutation overrides Tier 3 blog claiming support.
    Precedence rule: statutory truth dominates unverified claims.
    """
    ev = [
        make_evidence(id="ev_t1", publisher="NPCI", tier=SourceTier.TIER_1_PRIMARY, quote="NPCI categorically denies UPI shutdown reports."),
        make_evidence(id="ev_t3", publisher="Viral News Blog", tier=SourceTier.TIER_3_REPUTABLE, quote="Viral message claims UPI is shutting down tomorrow."),
    ]
    judgments = [
        EvidenceJudgeAssessment(evidence_id="ev_t1", stance=EvidenceStance.CONTRADICTS, strength=EvidenceAssessmentLevel.HIGH, reason="NPCI official refutation"),
        EvidenceJudgeAssessment(evidence_id="ev_t3", stance=EvidenceStance.SUPPORTS, strength=EvidenceAssessmentLevel.LOW, reason="Blog repeats forward"),
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim="UPI is banned tomorrow.",
        validated_evidence=ev,
        evidence_judgments=judgments,
        source_tiers=[1, 3],
        contradiction_strength="HIGH",
    )
    assert res.verdict == Verdict.FALSE
    assert "TIER_1_SOURCE_PRESENT" in res.rule_trace
    assert "STRONG_CONTRADICTION" in res.rule_trace


def test_conflicting_sources_equal_tiers_yields_partly_supported():
    """
    Conflicting Sources: Equal Tier 2 regulatory sources dispute implementation details.
    Agreement is 0.5. Verdict must be PARTLY_SUPPORTED.
    """
    ev = [
        make_evidence(id="ev_a", publisher="State Regulator A", tier=SourceTier.TIER_2_SECONDARY, quote="Tariff reduction approved for domestic category."),
        make_evidence(id="ev_b", publisher="State Regulator B", tier=SourceTier.TIER_2_SECONDARY, quote="Tariff reduction withheld pending review."),
    ]
    judgments = [
        EvidenceJudgeAssessment(evidence_id="ev_a", stance=EvidenceStance.SUPPORTS, reason="Regulator A confirms"),
        EvidenceJudgeAssessment(evidence_id="ev_b", stance=EvidenceStance.CONTRADICTS, reason="Regulator B denies"),
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim="State electricity tariffs reduced by 20% across all boards.",
        validated_evidence=ev,
        evidence_judgments=judgments,
        source_tiers=[2, 2],
        agreement=0.5,
    )
    assert res.verdict == Verdict.PARTLY_SUPPORTED
    assert "CONFLICTING_SOURCES" in res.rule_trace


def test_conflicting_sources_newer_tier1_supersedes_older_tier2():
    """
    Conflicting Sources: Older Tier 2 says true in 2024, newer Tier 1 in 2026 says discontinued.
    Verdict must be OUTDATED.
    """
    ev = [
        make_evidence(id="ev_old", publisher="Nodal Agency", tier=SourceTier.TIER_2_SECONDARY, quote="Subsidy active in 2024."),
        make_evidence(id="ev_new", publisher="Ministry Gazette", tier=SourceTier.TIER_1_PRIMARY, quote="Subsidy discontinued with effect from 2025."),
    ]
    res = DeterministicRuleEngine.compute_verdict(
        claim="Subsidy currently available for rooftop solar installations.",
        validated_evidence=ev,
        temporal_status=TemporalStatus.CONTRADICTED_BY_NEWER_EVIDENCE,
        source_tiers=[1, 2],
    )
    assert res.verdict == Verdict.OUTDATED
    assert "OUTDATED_SUPERSEDED" in res.rule_trace


# ==============================================================================
# SECTION 7: FASTAPI ENDPOINT TEST
# ==============================================================================

def test_api_compute_verdict_endpoint():
    """Test POST /api/v1/claims/compute-verdict with rule trace response."""
    payload = {
        "claim": "UPI is banned tomorrow.",
        "validated_evidence": [
            {
                "evidence_id": "ev_001",
                "publisher": "NPCI",
                "source_tier": 1,
                "domain": "npci.org.in",
                "exact_quote": "NPCI has not announced a nationwide shutdown.",
            }
        ],
        "evidence_judgments": [
            {
                "evidence_id": "ev_001",
                "stance": "CONTRADICTS",
                "strength": "HIGH",
                "relevance": "HIGH",
                "reason": "NPCI denies ban rumours.",
            }
        ],
        "contradiction_strength": "HIGH",
        "temporal_status": "CURRENT",
    }

    response = client.post("/api/v1/claims/compute-verdict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["verdict"] == "FALSE"
    assert "rule_trace" in data
    assert data["rule_trace"] == ["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION", "QUOTE_VALIDATED", "CURRENT_EVIDENCE"]
    assert data["confidence"] > 95.0
