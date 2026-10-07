import pytest
from app.schemas.enums import SourceTier, TemporalStatus, Verdict
from app.schemas.claim import ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceInterpretation
from app.services.rule_engine import DeterministicRuleEngine


def test_realistic_verified_claim():
    """Realistic test: Claim verified by Tier-1 Official Gazette citation."""
    claim = ExtractedClaim(
        claim_number=1,
        claim_text="Ministry of Education has notified PM Higher Merit Scholarship for 2026.",
        language="en",
    )
    evidence = [
        EvidenceItem(
            id="CIT-01",
            publisher="The Gazette of India",
            domain="egazette.gov.in",
            title="Notification MoE/HE/2026/04",
            publish_date="2026-09-12",
            tier=SourceTier.TIER_1_PRIMARY,
            url="https://egazette.gov.in/circ/2026/moe-14",
            exact_quote="Central Sector Scheme of Scholarship continuation is officially notified.",
            confidence_score=0.99,
        )
    ]
    interpretation = EvidenceInterpretation(
        supports_claim=True,
        refutes_claim=False,
        is_temporal_mismatch=False,
    )

    result = DeterministicRuleEngine.evaluate_claim(claim, evidence, interpretation)
    assert result.verdict == Verdict.VERIFIED
    assert result.confidence > 98.0
    assert result.rule_matched == "RULE-OFFICIAL-GAZETTE-CORROBORATION"
    assert len(result.source_citations) == 1


def test_realistic_financial_discrepancy_claim():
    """Realistic test: Claim exaggerating scholarship amount (claimed ₹50,000 vs actual ₹12,000)."""
    claim = ExtractedClaim(
        claim_number=2,
        claim_text="Every undergraduate college student will receive ₹50,000 lump sum DBT grant.",
        language="en",
    )
    evidence = [
        EvidenceItem(
            id="CIT-02",
            publisher="National Scholarship Portal",
            domain="scholarships.gov.in",
            title="Operational Guidelines 2026",
            publish_date="2026-09-15",
            tier=SourceTier.TIER_1_PRIMARY,
            url="https://scholarships.gov.in/guidelines.pdf",
            exact_quote="The rate of scholarship is Rs. 12,000/- per annum.",
            confidence_score=0.99,
        )
    ]
    interpretation = EvidenceInterpretation(
        supports_claim=False,
        refutes_claim=True,
        claimed_amount=50000.0,
        actual_amount=12000.0,
        discrepancy_explanation="Sanctioned amount is ₹12,000, not ₹50,000.",
    )

    result = DeterministicRuleEngine.evaluate_claim(claim, evidence, interpretation)
    assert result.verdict == Verdict.FALSE
    assert result.rule_matched == "RULE-FINANCIAL-DISCREPANCY"
    assert "₹50,000" in result.summary


def test_realistic_outdated_recirculation_claim():
    """Realistic test: 2020 COVID railway lockdown circular recirculated in 2026."""
    claim = ExtractedClaim(
        claim_number=1,
        claim_text="Railways ordered suspension of all passenger trains starting tomorrow.",
        language="en",
    )
    evidence = [
        EvidenceItem(
            id="CIT-03",
            publisher="Ministry of Railways",
            domain="indianrailways.gov.in",
            title="Order No. 2020/Tele/15/4",
            publish_date="2020-03-22",
            tier=SourceTier.TIER_1_PRIMARY,
            url="https://indianrailways.gov.in/order-2020",
            exact_quote="Passenger train services suspended till 31st March 2020.",
            confidence_score=0.98,
        )
    ]
    interpretation = EvidenceInterpretation(
        supports_claim=False,
        is_temporal_mismatch=True,
        discrepancy_explanation="Historical circular from March 2020 lockdown.",
    )

    result = DeterministicRuleEngine.evaluate_claim(claim, evidence, interpretation)
    assert result.verdict == Verdict.OUTDATED
    assert result.temporal_status == TemporalStatus.OUTDATED
    assert result.rule_matched == "RULE-TEMPORAL-RECIRCULATION"


def test_phishing_domain_malicious_detection():
    """Realistic test: Fraudulent domain flagged by CERT-In."""
    claim = ExtractedClaim(
        claim_number=3,
        claim_text="Citizens must register on pmssy-gov.in.",
        language="en",
    )
    evidence = []
    interpretation = EvidenceInterpretation(
        domain_flagged_malicious=True,
        discrepancy_explanation="Domain flagged as credential-harvesting phishing portal.",
    )

    result = DeterministicRuleEngine.evaluate_claim(claim, evidence, interpretation)
    assert result.verdict == Verdict.FALSE
    assert result.confidence == 100.0
    assert result.rule_matched == "RULE-MALICIOUS-PHISHING-URL"


def test_edge_case_insufficient_evidence():
    """Edge case: Claim has zero documentary records in government registries."""
    claim = ExtractedClaim(
        claim_number=1,
        claim_text="Chemicals leaked into Ward 14 water supply tanker today.",
        language="hi",
    )
    evidence = []
    interpretation = EvidenceInterpretation(
        supports_claim=False,
        refutes_claim=False,
    )

    result = DeterministicRuleEngine.evaluate_claim(claim, evidence, interpretation)
    assert result.verdict == Verdict.CANNOT_BE_CONFIRMED
    assert result.rule_matched == "RULE-INSUFFICIENT-EVIDENCE"


def test_aggregate_verdicts_hierarchy():
    """Integration test: Multiple atomic claims aggregating into overall verdict."""
    claim1 = ExtractedClaim(claim_number=1, claim_text="Govt launched scheme.", language="en")
    claim2 = ExtractedClaim(claim_number=2, claim_text="Grant is ₹50,000 cash.", language="en")

    res1 = DeterministicRuleEngine.evaluate_claim(
        claim1,
        [EvidenceItem(id="1", publisher="Gazette", domain="egazette.gov.in", title="T", tier=SourceTier.TIER_1_PRIMARY, url="u", exact_quote="q")],
        EvidenceInterpretation(supports_claim=True),
    )
    res2 = DeterministicRuleEngine.evaluate_claim(
        claim2,
        [],
        EvidenceInterpretation(refutes_claim=True, claimed_amount=50000.0, actual_amount=12000.0),
    )

    assert res1.verdict == Verdict.VERIFIED
    assert res2.verdict == Verdict.FALSE

    overall_verdict, summary = DeterministicRuleEngine.aggregate_verdicts([res1, res2])
    assert overall_verdict == Verdict.FALSE
    assert "debunked" in summary


def test_edge_case_empty_claims_aggregate():
    """Edge case: Aggregating empty claim list gracefully returns CANNOT_BE_CONFIRMED."""
    overall_verdict, summary = DeterministicRuleEngine.aggregate_verdicts([])
    assert overall_verdict == Verdict.CANNOT_BE_CONFIRMED
