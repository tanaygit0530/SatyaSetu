'use client';

import React from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { QuoteBlock } from '@/components/evidence/QuoteBlock';
import { MOCK_VERIFICATION_RESULTS, DEFAULT_CHECK } from '@/lib/mock/checks';
import { formatDate } from '@/lib/utils';

export default function PublicShareableVerdictPage() {
  const params = useParams();
  const publicId = (params?.publicId as string) || 'SC-2026-8941';

  const check = MOCK_VERIFICATION_RESULTS[publicId] || DEFAULT_CHECK;

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-lg space-y-space-lg">
        {/* Top Civic Meta Strip */}
        <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm bg-surface-container-lowest p-space-md rounded-xl border border-outline-variant shadow-2xs">
          <div className="flex flex-wrap items-center gap-space-xs text-on-surface-variant font-code-sm text-code-sm">
            <span className="inline-flex items-center gap-1 text-primary font-bold">
              <span className="material-symbols-outlined text-[16px]">account_balance</span>
              CIVIC AUDIT RECORD
            </span>
            <span className="text-outline-variant font-bold">/</span>
            <span className="text-on-surface select-all font-semibold">{check.id}</span>
            <span className="text-outline-variant font-bold">/</span>
            <span className="text-on-surface-variant">sachcheck.in/c/{check.id}</span>
          </div>

          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-low text-primary font-label-sm text-[12px] font-semibold border border-outline-variant/60">
            <span className="material-symbols-outlined text-[14px]">lock</span>
            Official Dossier • Verified Read-Only
          </div>
        </section>

        {/* Shareable Masthead Card */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-md">
            <div>
              <span className="font-code-sm text-[11px] text-outline font-bold uppercase tracking-wider">
                Audited WhatsApp Forward
              </span>
              <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface mt-1">
                {check.verdictSummary}
              </h1>
            </div>

            <VerdictBadge verdict={check.overallVerdict} size="lg" />
          </div>

          {/* Forward Quote */}
          <div className="pt-2">
            <span className="font-label-sm text-[11px] font-bold uppercase tracking-wider text-outline">
              Message Received by Citizens:
            </span>
            <QuoteBlock
              quote={check.originalMessage}
              sourceTitle="Viral WhatsApp Broadcast"
              variant="forwarded"
              className="mt-1"
            />
          </div>

          <div className="pt-space-sm border-t border-outline-variant flex flex-wrap items-center justify-between gap-space-sm font-code-sm text-[12px] text-on-surface-variant">
            <span>Verified on: {formatDate(check.submittedAt)}</span>
            <span>Audited against: eGazette & PIB Fact Check</span>
          </div>
        </div>

        {/* Atomic Claims List */}
        <div className="space-y-space-md">
          <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
            Atomic Claims Dissected
          </h2>

          <div className="space-y-space-sm">
            {check.claims.map((claim) => (
              <div
                key={claim.id}
                className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-2 shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-code-sm text-[11px] font-bold text-outline">
                    CLAIM #{claim.claimNumber}
                  </span>
                  <VerdictBadge verdict={claim.verdict} size="sm" />
                </div>
                <p className="font-serif italic text-on-surface text-[15px]">
                  "{claim.claimText}"
                </p>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  {claim.summary}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* WhatsApp Forward Share Banner */}
        <div className="rounded-2xl bg-surface-container-low border border-outline-variant p-space-lg text-center space-y-space-sm">
          <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
            Stop this fake forward in your WhatsApp groups.
          </h3>
          <p className="font-body-sm text-body-sm text-on-surface-variant max-w-md mx-auto">
            Share this tamper-proof verification page with proof from official Government records.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <a
              href={`https://wa.me/?text=SachCheck%20Official%20Verification%20Report:%20${encodeURIComponent(
                check.verdictSummary
              )}%20Read%20proof:%20https://sachcheck.in/c/${check.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-5 py-2.5 rounded-xl bg-[#1E8E4E] text-white font-label-md text-label-md font-bold hover:bg-[#146336] transition-colors flex items-center gap-2 shadow-xs"
            >
              <span className="material-symbols-outlined text-[18px]">chat</span>
              <span>Share to WhatsApp</span>
            </a>
            <Link
              href="/check"
              className="px-4 py-2.5 rounded-xl bg-surface-container-lowest border border-outline-variant text-on-surface font-label-md text-label-md hover:bg-surface-container"
            >
              Check Another Forward
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
