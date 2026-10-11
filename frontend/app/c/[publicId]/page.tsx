'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { QuoteBlock } from '@/components/evidence/QuoteBlock';
import { formatDate } from '@/lib/utils';
import { getCheckDetail, adaptCheckToUi } from '@/lib/api';
import { VerificationResult } from '@/types';

export default function PublicShareableVerdictPage() {
  const params = useParams();
  const publicId = (params?.publicId as string) || '';

  const [check, setCheck] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!publicId) return;

    let isMounted = true;

    async function loadPublicCheck() {
      try {
        setLoading(true);
        setError(null);
        const raw = await getCheckDetail(publicId);

        if (!isMounted) return;

        const adapted = adaptCheckToUi(raw);
        setCheck(adapted);
      } catch (err: any) {
        if (!isMounted) return;
        setError(err?.message || 'Public verification dossier could not be found.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadPublicCheck();

    return () => {
      isMounted = false;
    };
  }, [publicId]);

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-2xl text-center">
          <div className="p-space-xl rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-4">
            <div className="w-10 h-10 border-3 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="font-body-md text-on-surface-variant">Loading civic audit record #{publicId}...</p>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error || !check) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-2xl text-center space-y-4">
          <div className="p-space-2xl rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-4 shadow-sm">
            <h1 className="font-headline-lg text-2xl font-bold text-on-surface">Record Not Found</h1>
            <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
              {error || `No public verification record found with ID #${publicId}.`}
            </p>
            <div className="pt-2">
              <Link href="/check" className="px-4 py-2 rounded-xl bg-primary text-on-primary font-label-md font-semibold">
                Submit a Claim to Verify
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

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
                Audited WhatsApp Forward / Statement
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
              text={check.originalMessage}
              source="Forwarded WhatsApp Message"
              highlightType="neutral"
            />
          </div>

          {/* Audit Timestamp & Channel */}
          <div className="pt-space-sm border-t border-outline-variant flex flex-wrap items-center justify-between gap-2 text-body-sm font-code-sm text-[12px] text-on-surface-variant">
            <span>Verified: <strong className="text-on-surface">{formatDate(check.completedAt)}</strong></span>
            <span>Channel: <strong className="text-on-surface">{check.inputType}</strong></span>
            {check.cacheHit && (
              <span className="text-tertiary font-bold">✓ Shared Rumour Memory Verified</span>
            )}
          </div>
        </div>

        {/* Atomic Claims List */}
        <div className="space-y-space-md">
          <h2 className="font-headline-md text-xl font-bold text-on-surface">
            Atomic Fact Findings ({check.claims.length})
          </h2>

          <div className="space-y-space-md">
            {check.claims.map((claim) => (
              <div
                key={claim.id}
                className="p-space-lg rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3 shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-code-sm text-[11px] font-bold text-outline">
                    CLAIM #{claim.claimNumber}
                  </span>
                  <VerdictBadge verdict={claim.verdict} size="sm" />
                </div>

                <p className="font-serif italic text-[16px] text-on-surface">
                  "{claim.claimText}"
                </p>

                <p className="font-body-md text-body-md text-on-surface-variant">
                  {claim.summary}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
