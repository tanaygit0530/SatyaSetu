'use client';

import React from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';

export default function HowWeDecidePage() {
  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-2xl">
        {/* Editorial Masthead */}
        <div className="space-y-3 border-b border-outline-variant pb-space-lg">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-high text-primary font-code-sm text-[12px] font-bold">
            <span className="material-symbols-outlined text-[16px]">menu_book</span>
            <span>OPEN METHODOLOGY & CIVIC AUDIT CHARTER</span>
          </div>
          <h1 className="font-headline-xl text-3xl sm:text-4xl md:text-5xl font-extrabold text-on-surface">
            We show our evidence. <br />
            We don't ask you to trust us.
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-3xl">
            Fact-checking platforms often demand blind faith in their editorial authority. SachCheck is built on open statutory proof, verifiable gazette citations, and auditable deterministic logic.
          </p>
        </div>

        {/* Section 1: The 5 Verdict Definitions */}
        <section className="space-y-space-md">
          <div className="space-y-1">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Section 01
            </span>
            <h2 className="font-headline-lg text-headline-lg font-bold text-on-surface">
              The Standard 5 Verdicts
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Every claim evaluated by SachCheck resolves into exactly one of five standardized categories:
            </p>
          </div>

          <div className="space-y-space-md">
            {[
              {
                verdict: 'VERIFIED' as const,
                title: 'Verified Record',
                criteria:
                  'Corroborated by authentic primary statutory gazettes, official ministry portal circulars, or direct regulatory announcements.',
                example:
                  'Notification MoE/HE/2026/04 confirming continuation of CSS merit scholarship.',
              },
              {
                verdict: 'FALSE' as const,
                title: 'False / Fabricated Assertion',
                criteria:
                  'Directly refuted by primary records, containing fabricated financial quantities, nonexistent scheme names, or counterfeit phishing domains.',
                example:
                  'Universal ₹50,000 cash grant claiming to require registration on pmssy-gov.in.',
              },
              {
                verdict: 'OUTDATED' as const,
                title: 'Outdated / Temporal Mismatch',
                criteria:
                  'Genuinely authentic historical documents or orders recirculated deceptively to mimic current announcements.',
                example:
                  'COVID-19 passenger train suspension order from March 2020 shared as 2026 lockdown.',
              },
              {
                verdict: 'PARTLY_SUPPORTED' as const,
                title: 'Partly Supported',
                criteria:
                  'The core premise has factual backing, but secondary claims, numbers, eligibility criteria, or deadlines are inflated or inaccurate.',
                example:
                  'Scholarship exists, but amount is ₹12,000 rather than claimed ₹50,000.',
              },
              {
                verdict: 'CANNOT_BE_CONFIRMED' as const,
                title: 'Cannot Be Confirmed',
                criteria:
                  'Insufficient authoritative primary records available, hyper-local uncorroborated assertions, or non-falsifiable subjective opinions.',
                example:
                  'Unverified voice memo alleging pipeline chemical leaks without official municipal water testing record.',
              },
            ].map((v) => (
              <div
                key={v.verdict}
                className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-2 shadow-2xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <VerdictBadge verdict={v.verdict} size="md" />
                    <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                      {v.title}
                    </h3>
                  </div>
                  <span className="font-code-sm text-[11px] text-outline">
                    Rule Protocol #{v.verdict}
                  </span>
                </div>
                <p className="font-body-md text-body-md text-on-surface">
                  <b>Audit Criterion:</b> {v.criteria}
                </p>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  <b>Canonical Example:</b> {v.example}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Section 2: Authoritative Source Hierarchy */}
        <section id="precedence" className="space-y-space-md pt-space-lg border-t border-outline-variant">
          <div className="space-y-1">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Section 02
            </span>
            <h2 className="font-headline-lg text-headline-lg font-bold text-on-surface">
              Source Precedence Matrix
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              We never treat all internet sources as equal. When sources conflict, precedence is strictly enforced:
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
            <div className="p-space-md rounded-xl bg-primary-fixed/20 border border-primary/20 space-y-2">
              <span className="px-2 py-0.5 rounded-full bg-primary text-on-primary font-code-sm text-[11px] font-bold">
                TIER-1 PRIMARY STATUTORY
              </span>
              <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                Gazettes & NIC Portals
              </h3>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                The Gazette of India (egazette.gov.in), Press Information Bureau (PIB), Supreme Court & High Court orders, Reserve Bank of India circulars.
              </p>
              <div className="font-code-sm text-[11px] text-primary font-bold pt-1">
                Highest Precedence • Overrides All Secondary Claims
              </div>
            </div>

            <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
              <span className="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface font-code-sm text-[11px] font-bold">
                TIER-2 REGULATORY BODIES
              </span>
              <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                Statutory Authorities
              </h3>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                University Grants Commission (UGC), AICTE, CBSE, Municipal Corporation bulletins, CERT-In cybersecurity advisories.
              </p>
              <div className="font-code-sm text-[11px] text-on-surface-variant font-bold pt-1">
                Authoritative in Specific Domain
              </div>
            </div>

            <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
              <span className="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface font-code-sm text-[11px] font-bold">
                TIER-3 REPUTABLE ACCREDITED
              </span>
              <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                IFCN Fact-Checkers
              </h3>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Signatories to the International Fact-Checking Network (IFCN), PTI, ANI, and accredited national press archives.
              </p>
              <div className="font-code-sm text-[11px] text-on-surface-variant font-bold pt-1">
                Secondary Corroboration Only
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: Human Review & Dispute Resolution */}
        <section className="p-space-lg rounded-2xl bg-surface-container-low border border-outline-variant space-y-3">
          <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
            Citizens Can Dispute Any Finding
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            If you possess primary documentation that refutes an automated verdict, our Auditor Desk maintains a public dispute queue. Every challenge is audited by human investigators within 24 hours.
          </p>
          <div className="pt-1 flex gap-3">
            <Link
              href="/admin/login"
              className="font-label-md text-label-md text-secondary font-bold hover:underline"
            >
              Auditor Desk Review Portal →
            </Link>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
