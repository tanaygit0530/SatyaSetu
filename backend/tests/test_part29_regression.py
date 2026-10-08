import pytest
from app.services.verification_orchestrator import VerificationOrchestrator
from app.schemas.enums import Verdict

def test_part29_core_suite():
    orc = VerificationOrchestrator()
    
    test_cases = [
        ("UPI was developed by NPCI.", Verdict.VERIFIED),
        ("UPI was developed by NASA.", Verdict.FALSE),
        ("IMPS is available 24 hours a day.", Verdict.VERIFIED),
        ("IMPS only works during bank working hours.", Verdict.FALSE),
        ("India's national animal is the Bengal tiger.", Verdict.VERIFIED),
        ("India's national animal is the lion.", Verdict.FALSE),
    ]
    
    results = []
    for claim, expected in test_cases:
        res = orc.verify(content=claim)
        print(f"\n==========================================")
        print(f"Claim: {claim}")
        print(f"Expected: {expected.value} | Got: {res.overall_verdict.value}")
        print(f"Confidence: {res.confidence}")
        print(f"Timing ms: {res.timing_ms}")
        if res.claims:
            print(f"Rule trace: {res.claims[0].rule_trace}")
            print(f"Claim type: {res.claims[0].claim_type}")
        assert res.overall_verdict == expected, f"Failed for '{claim}': expected {expected}, got {res.overall_verdict}"
        results.append((claim, expected, res.overall_verdict, res.timing_ms.get("total_ms", 0)))
    
    print("\n\n=== SUMMARY OF ALL 6 TESTS ===")
    for claim, exp, got, dur in results:
        status = "PASSED" if exp == got else "FAILED"
        print(f"[{status}] '{claim}' -> {got.value} (in {dur}ms)")

if __name__ == "__main__":
    test_part29_core_suite()
