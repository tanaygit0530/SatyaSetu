'use client';

import React from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { SourceTierBadge } from '@/components/evidence/SourceTierBadge';
import { QuoteBlock } from '@/components/evidence/QuoteBlock';
import { ConfidenceBand } from '@/components/verdict/ConfidenceBand';
import { MOCK_VERIFICATION_RESULTS, DEFAULT_CHECK } from '@/lib/mock/checks';

export default function ForensicEvidencePage() {
  const params = useParams();
  const checkId = (params?.id as string) || 'SC-2026-8941';
  const claimId = (params?.claimId as string) || 'CLM-8941-2';

  const check = MOCK_VERIFICATION_RESULTS[checkId] || DEFAULT_CHECK;
  const claim =
    check.claims.find((c) => c.id === claimId) || check.claims[1] || check.claims[0];

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto px-margin md:px-margin-desktop py-space-lg space-y-space-lg">
        {/* Breadcrumb Navigation */}
        <nav
          aria-label="Evidence Audit Trail"
          className="flex items-center flex-wrap gap-space-xs text-on-surface-variant font-label-sm text-label-sm pb-space-xs border-b border-outline-variant"
        >
          <Link href="/check" className="hover:text-primary transition-colors flex items-center gap-1">
            <span className="material-symbols-outlined text-[16px]">folder_supervised</span>
            <span>Check</span>
          </Link>
          <span className="text-outline-variant font-code-sm">/</span>
          <Link href={`/check/${check.id}`} className="hover:text-primary transition-colors font-code-sm">
            Result #{check.id}
          </Link>
          <span className="text-outline-variant font-code-sm">/</span>
          <span className="text-primary font-bold bg-surface-container-high px-space-xs py-0.5 rounded font-code-sm">
            Claim #{claim.claimNumber} Audit Dossier
          </span>
        </nav>

        {/* Header: Claim Audit Dossier */}
        <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-surface-container font-code-sm text-[11px] font-bold text-on-surface-variant">
                  DOSSIER ID: {claim.id}
                </span>
                <span className="font-code-sm text-[11px] text-outline">
                  Rule: {claim.ruleMatched || 'RULE-STATUTORY-CHECK'}
                </span>
              </div>
              <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
                Forensic Claim Audit & Source Inspection
              </h1>
            </div>

            <div className="shrink-0 flex items-center gap-2">
              <VerdictBadge verdict={claim.verdict} size="lg" />
            </div>
          </div>

          {/* Under Inspection Statement */}
          <div className="pt-2">
            <span className="font-label-sm text-[11px] font-bold uppercase tracking-wider text-outline">
              Exact Claim Statement Under Inspection:
            </span>
            <div className="mt-1 p-space-md rounded-xl bg-surface-container-low border border-outline-variant">
              <p className="font-serif italic text-on-surface text-[17px] leading-relaxed">
                "{claim.claimText}"
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md pt-2 border-t border-outline-variant font-code-sm text-[12px]">
            <div>
              <span className="text-outline">ALGORITHMIC CERTAINTY:</span>
              <p className="font-bold text-on-surface text-[14px]">{claim.confidence}% Verified</p>
            </div>
            <div>
              <span className="text-outline">PRECEDENCE TIER:</span>
              <p className="font-bold text-primary text-[14px]">Tier-1 Constitutional Gazette</p>
            </div>
            <div>
              <span className="text-outline">TEMPORAL VALIDITY:</span>
              <p className="font-bold text-tertiary text-[14px]">Active Statutory Law (2026)</p>
            </div>
          </div>
        </div>

        {/* Detailed Analysis Section */}
        <section className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
          <h2 className="font-headline-md text-headline-md font-bold text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">policy</span>
            <span>Evidential Reasoning & Discrepancy Breakdown</span>
          </h2>

          <div className="prose max-w-none text-on-surface font-body-md text-body-md space-y-3">
            <p>{claim.detailedAnalysis}</p>
            {claim.counterEvidenceSummary && (
              <div className="p-space-md rounded-xl bg-error-container/20 border border-error/30 text-error">
                <span className="font-bold block mb-1">Fatal Factual Conflict:</span>
                <p>{claim.counterEvidenceSummary}</p>
              </div>
            )}
          </div>
        </section>

        {/* Primary Statutory Records Accordion / List */}
        <div className="space-y-space-md">
          <div className="flex items-center justify-between">
            <h2 className="font-headline-md text-headline-md font-bold text-on-surface">
              Primary Documentary Records ({claim.sourceCitations.length})
            </h2>
            <span className="font-code-sm text-[12px] text-outline">
              IFCN Tier-1 Archival Standards
            </span>
          </div>

          <div className="space-y-space-md">
            {claim.sourceCitations.map((citation, idx) => (
              <div
                key={citation.id}
                className="p-space-lg rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-space-sm shadow-2xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-primary-fixed text-primary flex items-center justify-center font-code-sm text-[11px] font-bold">
                      {idx + 1}
                    </span>
                    <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                      {citation.title}
                    </h3>
                  </div>
                  <SourceTierBadge tier={citation.tier} />
                </div>

                <div className="flex flex-wrap items-center gap-4 text-on-surface-variant font-code-sm text-[12px]">
                  <span>Publisher: <b className="text-on-surface">{citation.publisher}</b></span>
                  <span>Domain: <b className="text-on-surface">{citation.domain}</b></span>
                  <span>Date: <b className="text-on-surface">{citation.date}</b></span>
                </div>

                <QuoteBlock
                  quote={citation.exactQuote}
                  sourcePublisher={citation.publisher}
                  sourceDate={citation.date}
                />

                <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-outline-variant font-code-sm text-[12px]">
                  <div className="flex items-center gap-1.5 text-tertiary font-bold">
                    <span className="material-symbols-outlined text-[16px]">verified</span>
                    <span>Direct Gazette Citation Match (Score: {citation.confidenceScore})</span>
                  </div>

                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline font-bold"
                  >
                    <span>Inspect Raw Statutory Record</span>
                    <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Back navigation */}
        <div className="pt-2 flex justify-between items-center">
          <Link
            href={`/check/${check.id}`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-outline-variant text-on-surface font-label-md text-label-md hover:bg-surface-container-low transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            <span>Return to Check Summary #{check.id}</span>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
