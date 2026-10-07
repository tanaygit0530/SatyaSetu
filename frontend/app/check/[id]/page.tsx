'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { ClaimCard } from '@/components/verification/ClaimCard';
import { QuoteBlock } from '@/components/evidence/QuoteBlock';
import { MOCK_VERIFICATION_RESULTS, DEFAULT_CHECK } from '@/lib/mock/checks';
import { formatDate } from '@/lib/utils';
import { Verdict } from '@/types';

export default function VerificationResultPage() {
  const params = useParams();
  const requestedId = (params?.id as string) || 'SC-2026-8941';

  // State to toggle between mock records or view specific variants
  const [activeCheckId, setActiveCheckId] = useState<string>(
    MOCK_VERIFICATION_RESULTS[requestedId] ? requestedId : 'SC-2026-8941'
  );
  const [feedbackGiven, setFeedbackGiven] = useState<'UP' | 'DOWN' | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const check = MOCK_VERIFICATION_RESULTS[activeCheckId] || DEFAULT_CHECK;

  const handleCopyLink = () => {
    navigator.clipboard?.writeText?.(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop py-space-lg space-y-space-lg">
        {/* State Variant Demonstration Switcher */}
        <div className="bg-surface-container-low p-2.5 rounded-xl border border-outline-variant flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[18px]">tune</span>
            <span className="font-label-sm text-[12px] font-bold text-on-surface">
              Switch Test Case Variant:
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'SC-2026-8941', label: 'Case 1: Fake Scholarship (False)', verdict: 'FALSE' as Verdict },
              { id: 'SC-2026-9021', label: 'Case 2: 2020 Railway Circular (Outdated)', verdict: 'OUTDATED' as Verdict },
              { id: 'SC-2026-7712', label: 'Case 3: Unverified Water Pipeline', verdict: 'CANNOT_BE_CONFIRMED' as Verdict },
            ].map((variant) => (
              <button
                key={variant.id}
                type="button"
                onClick={() => setActiveCheckId(variant.id)}
                className={`px-2.5 py-1 rounded-lg text-label-sm font-semibold transition-colors flex items-center gap-1.5 ${
                  activeCheckId === variant.id
                    ? 'bg-surface-container-lowest text-primary shadow-xs border border-outline-variant font-bold'
                    : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                }`}
              >
                <span>{variant.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Top Breadcrumb & Metadata Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
          <div className="flex items-center gap-space-sm font-label-md text-label-md text-on-surface-variant">
            <Link href="/check" className="hover:text-primary transition-colors flex items-center gap-1">
              <span className="material-symbols-outlined text-[18px]">verified</span>
              <span>Check</span>
            </Link>
            <span className="text-outline-variant">/</span>
            <span className="font-code-sm text-code-sm bg-surface-container-high px-space-sm py-0.5 rounded text-primary font-bold">
              Record #{check.id}
            </span>
            {check.cacheHit && (
              <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[11px] font-bold flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px]">flash_on</span>
                Cache Hit (Rumour Memory)
              </span>
            )}
          </div>

          <div className="flex items-center gap-space-md text-on-surface-variant font-code-sm text-[12px]">
            <div className="flex items-center gap-1">
              <span className="material-symbols-outlined text-[15px] text-outline">schedule</span>
              <span>Checked: {formatDate(check.submittedAt)}</span>
            </div>
            <div className="hidden md:flex items-center gap-1.5 bg-surface-container px-2.5 py-1 rounded-full text-on-surface font-label-sm text-[12px]">
              <span className="w-2 h-2 rounded-full bg-tertiary"></span>
              <span>Repository: {check.repositoryId || '0x9AF...41B'}</span>
            </div>
          </div>
        </div>

        {/* Aggregate Verdict Masthead */}
        <section className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md">
            <div className="space-y-1">
              <span className="font-code-sm text-[11px] uppercase tracking-wider text-outline font-bold">
                Overall Aggregate Finding
              </span>
              <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
                {check.verdictSummary}
              </h1>
            </div>

            <div className="shrink-0">
              <VerdictBadge verdict={check.overallVerdict} size="lg" />
            </div>
          </div>

          {/* Original Message Display */}
          <div className="pt-2">
            <span className="font-label-sm text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">
              Forward Under Inspection:
            </span>
            <QuoteBlock
              quote={check.originalMessage}
              sourceTitle="Submitted WhatsApp Forward"
              variant="forwarded"
              className="mt-1"
            />
          </div>

          {/* Quick Stats Strip */}
          <div className="pt-space-sm border-t border-outline-variant grid grid-cols-2 sm:grid-cols-4 gap-space-md font-code-sm text-[12px]">
            <div>
              <span className="text-outline">CLAIMS ANALYZED:</span>
              <p className="font-bold text-on-surface text-[14px]">{check.claims.length} Atomic Statements</p>
            </div>
            <div>
              <span className="text-outline">PRIMARY SOURCES:</span>
              <p className="font-bold text-on-surface text-[14px]">
                {check.claims.reduce((acc, c) => acc + c.sourceCitations.length, 0)} Gazette Records
              </p>
            </div>
            <div>
              <span className="text-outline">LATENCY:</span>
              <p className="font-bold text-on-surface text-[14px]">{(check.processingDurationMs / 1000).toFixed(2)}s</p>
            </div>
            <div>
              <span className="text-outline">AUDIT STATUS:</span>
              <p className="font-bold text-tertiary text-[14px]">Deterministic Certified</p>
            </div>
          </div>
        </section>

        {/* Claim-by-Claim Detailed Dissection */}
        <div className="space-y-space-md">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-headline-md text-headline-md font-bold text-on-surface">
                Claim-by-Claim Evidential Breakdown
              </h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Every factual assertion is isolated and audited independently against primary registries.
              </p>
            </div>
            <span className="font-code-sm text-[12px] text-outline">
              {check.claims.length} claims extracted
            </span>
          </div>

          <div className="space-y-space-md">
            {check.claims.map((claim) => (
              <ClaimCard
                key={claim.id}
                claim={claim}
                checkId={check.id}
              />
            ))}
          </div>
        </div>

        {/* Share, Feedback & Dispute Action Card */}
        <section className="rounded-2xl bg-surface-container-low border border-outline-variant p-space-md md:p-space-lg flex flex-col md:flex-row items-center justify-between gap-space-md">
          <div className="space-y-1 text-center md:text-left">
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Help curb misinformation.
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Share this official audit link back into the WhatsApp group where you received the forward.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2.5">
            <Link
              href={`/c/${check.id}`}
              className="px-4 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant text-on-surface font-label-md text-label-md font-semibold hover:bg-surface-container transition-colors flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[18px]">visibility</span>
              <span>View Public Dossier</span>
            </Link>

            <button
              type="button"
              onClick={handleCopyLink}
              className="px-4 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant text-on-surface font-label-md text-label-md font-semibold hover:bg-surface-container transition-colors flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[18px]">
                {copiedLink ? 'check' : 'content_copy'}
              </span>
              <span>{copiedLink ? 'Link Copied!' : 'Copy Share Link'}</span>
            </button>

            <a
              href={`https://wa.me/?text=SachCheck%20Official%20Verification%20Report:%20${encodeURIComponent(
                check.verdictSummary
              )}%20Read%20proof:%20https://sachcheck.in/c/${check.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-xl bg-[#1E8E4E] text-white font-label-md text-label-md font-bold hover:bg-[#146336] transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <span className="material-symbols-outlined text-[18px]">chat</span>
              <span>Forward to WhatsApp</span>
            </a>
          </div>
        </section>

        {/* Feedback Widget */}
        <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant flex flex-wrap items-center justify-between gap-space-md">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-outline text-[18px]">rate_review</span>
            <span className="font-body-sm text-body-sm text-on-surface">
              Was this evidentiary analysis accurate and helpful?
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setFeedbackGiven('UP')}
              className={`px-3 py-1.5 rounded-lg border text-label-sm font-semibold flex items-center gap-1 transition-colors ${
                feedbackGiven === 'UP'
                  ? 'bg-emerald-100 text-[#146336] border-emerald-300'
                  : 'border-outline-variant text-on-surface-variant hover:bg-surface-container-low'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">thumb_up</span>
              <span>Yes, accurate</span>
            </button>

            <button
              type="button"
              onClick={() => setFeedbackGiven('DOWN')}
              className={`px-3 py-1.5 rounded-lg border text-label-sm font-semibold flex items-center gap-1 transition-colors ${
                feedbackGiven === 'DOWN'
                  ? 'bg-red-100 text-red-700 border-red-300'
                  : 'border-outline-variant text-on-surface-variant hover:bg-surface-container-low'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">thumb_down</span>
              <span>Dispute finding</span>
            </button>

            {feedbackGiven && (
              <span className="font-code-sm text-[12px] text-tertiary font-bold ml-2">
                Feedback logged into audit ledger.
              </span>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
