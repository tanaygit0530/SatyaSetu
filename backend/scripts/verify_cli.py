#!/usr/bin/env python3
"""
CLI utility to test SachCheck verification pipeline directly.
Usage:
    python backend/scripts/verify_cli.py "Forwarded text goes here"
"""
import asyncio
import sys
from app.schemas.verification import VerificationRequest
from app.services.verification_service import verification_service


async def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = (
            "URGENT: Ministry of Education offers ₹50,000 scholarship cash grant for 2026. "
            "Apply immediately on pmssy-gov.in."
        )

    print(f"\n[SachCheck CLI] Ingesting Forward:\n'{text}'\n")
    req = VerificationRequest(content=text, is_demo=True)
    res = await verification_service.verify_forward(req)

    print(f"==================================================")
    print(f"CASE ID: {res.id}")
    print(f"OVERALL VERDICT: {res.overall_verdict.value}")
    print(f"SUMMARY: {res.verdict_summary}")
    print(f"CLAIMS EXTRACTED: {len(res.claims)}")
    print(f"==================================================")
    for c in res.claims:
        print(f"\n- CLAIM #{c.claim_number}: '{c.claim_text}'")
        print(f"  VERDICT: {c.verdict.value} (Confidence: {c.confidence}%)")
        print(f"  RULE: {c.rule_matched}")
        print(f"  SUMMARY: {c.summary}")
        if c.source_citations:
            print(f"  CITATIONS ({len(c.source_citations)}):")
            for cit in c.source_citations:
                print(f"    * [{cit.tier.value}] {cit.publisher} ({cit.domain})")
                print(f"      Quote: \"{cit.exact_quote}\"")
    print(f"\n==================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
