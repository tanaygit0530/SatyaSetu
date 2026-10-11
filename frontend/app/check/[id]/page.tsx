'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { ClaimCard } from '@/components/verification/ClaimCard';
import { QuoteBlock } from '@/components/evidence/QuoteBlock';
import { formatDate } from '@/lib/utils';
import { getCheckDetail, adaptCheckToUi } from '@/lib/api';
import { VerificationResult } from '@/types';

export default function VerificationResultPage() {
  const params = useParams();
  const router = useRouter();
  const checkId = (params?.id as string) || '';

  const [check, setCheck] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (!checkId) return;

    let isMounted = true;

    async function loadRecord() {
      try {
        setLoading(true);
        setError(null);
        const raw = await getCheckDetail(checkId);

        if (!isMounted) return;

        // If the backend indicates verification is still in progress, redirect to processing page
        if (raw.status && raw.status !== 'COMPLETED' && !raw.result) {
          router.replace(`/check/${encodeURIComponent(checkId)}/processing`);
          return;
        }

        const adapted = adaptCheckToUi(raw);
        setCheck(adapted);
      } catch (err: any) {
        if (!isMounted) return;
        console.error('Failed to load check record:', err);
        setError(err?.message || 'Verification record could not be found.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadRecord();

    return () => {
      isMounted = false;
    };
  }, [checkId, router]);

  const handleCopyLink = () => {
    if (typeof window !== 'undefined') {
      navigator.clipboard?.writeText?.(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  // Loading state
  if (loading) {
    return (
      <AppShell>
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-lg">
          {/* Audit Verification Header Skeleton */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-outline-variant/60">
            <div className="flex items-center gap-3">
              <span className="relative flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-primary"></span>
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-headline-sm text-xl sm:text-2xl font-bold text-on-surface">
                    Auditing Verification Dossier
                  </h1>
                  <span className="px-2.5 py-0.5 rounded-full bg-surface-container font-code-sm text-[12px] font-bold text-primary">
                    #{checkId}
                  </span>
                </div>
                <p className="font-body-sm text-[13px] text-on-surface-variant flex items-center gap-2 mt-0.5">
                  <span className="material-symbols-outlined text-[15px] text-primary animate-spin">sync</span>
                  <span>Fetching cryptographic grounding and evidence citations from backend...</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="h-9 w-28 rounded-xl bg-surface-container animate-pulse"></div>
              <div className="h-9 w-24 rounded-xl bg-surface-container animate-pulse"></div>
            </div>
          </div>

          {/* Shimmering Linear Progress Bar */}
          <div className="w-full h-1.5 rounded-full bg-surface-container overflow-hidden">
            <div className="h-full bg-gradient-to-r from-primary via-tertiary to-primary animate-[pulse_1.5s_infinite] w-2/3 rounded-full"></div>
          </div>

          {/* Main Verdict Card Skeleton */}
          <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg sm:p-space-xl space-y-space-md shadow-xs relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary/60 via-tertiary to-primary/60 animate-pulse"></div>
            
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-md pb-space-md border-b border-outline-variant">
              <div className="space-y-2 w-full max-w-md">
                <div className="h-4 w-40 rounded bg-surface-container-high animate-pulse"></div>
                <div className="h-7 w-64 rounded-lg bg-surface-container-high animate-pulse"></div>
              </div>
              <div className="h-10 w-36 rounded-xl bg-surface-container-high animate-pulse shrink-0"></div>
            </div>

            {/* Quote Block Skeleton */}
            <div className="p-space-md rounded-xl bg-surface-container-low border-l-4 border-l-primary/40 space-y-2">
              <div className="h-3 w-32 rounded bg-surface-container animate-pulse"></div>
              <div className="h-5 w-full rounded bg-surface-container-high animate-pulse"></div>
              <div className="h-5 w-4/5 rounded bg-surface-container-high animate-pulse"></div>
            </div>

            {/* Audit Meta Bar */}
            <div className="flex items-center justify-between pt-2 border-t border-outline-variant/60">
              <div className="h-4 w-48 rounded bg-surface-container animate-pulse"></div>
              <div className="h-4 w-32 rounded bg-surface-container animate-pulse"></div>
            </div>
          </div>

          {/* Claims & Citations Skeleton Breakdown */}
          <div className="space-y-space-md pt-2">
            <div className="flex items-center justify-between">
              <div className="h-6 w-52 rounded bg-surface-container-high animate-pulse"></div>
              <div className="h-4 w-28 rounded bg-surface-container animate-pulse"></div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
              {[1, 2].map((i) => (
                <div key={i} className="rounded-xl border border-outline-variant bg-surface-container-lowest p-space-md space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="h-4 w-24 rounded bg-surface-container animate-pulse"></div>
                    <div className="h-5 w-20 rounded bg-surface-container-high animate-pulse"></div>
                  </div>
                  <div className="h-4 w-full rounded bg-surface-container animate-pulse"></div>
                  <div className="h-4 w-3/4 rounded bg-surface-container animate-pulse"></div>
                  <div className="pt-2 border-t border-outline-variant/60 flex items-center justify-between">
                    <div className="h-3 w-28 rounded bg-surface-container animate-pulse"></div>
                    <div className="h-3 w-20 rounded bg-surface-container animate-pulse"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  // Error / Not Found state
  if (error || !check) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-2xl space-y-space-lg text-center">
          <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-2xl space-y-4 shadow-sm">
            <div className="w-14 h-14 rounded-full bg-surface-container-high text-on-surface-variant flex items-center justify-center mx-auto">
              <span className="material-symbols-outlined text-[32px]">search_off</span>
            </div>
            <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
              Verification Record Not Found
            </h1>
            <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
              {error || `No verification dossier found with ID #${checkId}.`}
            </p>
            <div className="pt-2 flex justify-center gap-3">
              <Link
                href="/check"
                className="px-5 py-2.5 rounded-xl bg-primary text-on-primary font-label-md font-bold hover:bg-primary-container transition-colors"
              >
                Submit New Verification
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop py-space-lg space-y-space-lg">
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
                Cache Hit (Shared Rumour Memory)
              </span>
            )}
          </div>

          <div className="flex items-center gap-space-md text-on-surface-variant font-code-sm text-[12px]">
            <div className="flex items-center gap-1">
              <span className="material-symbols-outlined text-[15px] text-outline">schedule</span>
              <span>Checked: {formatDate(check.submittedAt)}</span>
            </div>
            {check.processingDurationMs > 0 && (
              <div className="flex items-center gap-1 bg-surface-container px-2 py-0.5 rounded">
                <span>Latency: </span>
                <span className="font-bold text-primary">{(check.processingDurationMs / 1000).toFixed(1)}s</span>
              </div>
            )}
          </div>
        </div>

        {/* Aggregate Verdict Masthead */}
        <section className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md">
            <div className="space-y-1">
              <span className="font-code-sm text-[11px] text-outline font-bold uppercase tracking-wider">
                Audited Claim • Multi-Source Evidence Determination
              </span>
              <h1 className="font-headline-xl text-2xl sm:text-3xl font-extrabold text-on-surface leading-tight">
                {check.verdictSummary}
              </h1>
            </div>

            <div className="self-start md:self-center shrink-0">
              <VerdictBadge verdict={check.overallVerdict} size="lg" />
            </div>
          </div>

          {/* Original Forward Quote Block */}
          <div className="pt-2">
            <span className="font-label-sm text-[11px] font-bold uppercase tracking-wider text-outline">
              Original Message Submitted by Citizen:
            </span>
            <QuoteBlock
              text={check.originalMessage}
              source={check.inputType === 'LINK' ? 'Submitted Web Link' : 'Citizen Submission'}
              highlightType="neutral"
            />
          </div>

          {/* Forensic Actions & Verification Meta */}
          <div className="pt-space-sm border-t border-outline-variant flex flex-wrap items-center justify-between gap-space-md">
            <div className="flex flex-wrap items-center gap-space-sm text-body-sm font-code-sm text-[12px] text-on-surface-variant">
              <span>Channel: <strong className="text-on-surface font-semibold">{check.inputType}</strong></span>
              <span>•</span>
              <span>Claims Dissected: <strong className="text-on-surface font-semibold">{check.claims.length}</strong></span>
              <span>•</span>
              <span>Evidence Engine: <strong className="text-tertiary font-semibold">IFCN Standard</strong></span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyLink}
                className="px-3 py-1.5 rounded-lg border border-outline-variant bg-surface-container-low hover:bg-surface-container font-label-sm text-label-sm text-on-surface flex items-center gap-1.5 transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">
                  {copiedLink ? 'check' : 'share'}
                </span>
                <span>{copiedLink ? 'Link Copied' : 'Share Dossier'}</span>
              </button>

              <Link
                href={`/c/${encodeURIComponent(check.id)}`}
                className="px-3 py-1.5 rounded-lg bg-primary text-on-primary font-label-sm text-label-sm font-semibold hover:bg-primary-container transition-colors flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                <span>Public Share View</span>
              </Link>
            </div>
          </div>
        </section>

        {/* Atomic Claims List Section */}
        <section className="space-y-space-md">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-headline-md text-xl font-bold text-on-surface">
                Atomic Claim Breakdown ({check.claims.length})
              </h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Every factual proposition is isolated, audited against primary records, and certified independently.
              </p>
            </div>
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
        </section>

        {/* Primary Evidence Citations Section */}
        {check.claims.some((c) => c.sourceCitations && c.sourceCitations.length > 0) && (
          <section className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-headline-md text-xl font-bold text-on-surface">
                  Authoritative Grounding Sources & Exact Quotes
                </h2>
                <p className="font-body-sm text-on-surface-variant">
                  Verbatim quotes extracted from authenticated sources and official gazettes.
                </p>
              </div>
            </div>

            <div className="space-y-space-md pt-2">
              {check.claims.flatMap((c) =>
                c.sourceCitations.map((citation) => (
                  <div
                    key={citation.id}
                    className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary text-[18px]">verified</span>
                        <span className="font-label-md font-bold text-on-surface">{citation.publisher}</span>
                        <span className="font-code-sm text-[11px] text-outline">({citation.domain})</span>
                      </div>
                      <span className="px-2 py-0.5 rounded-full bg-surface-container-high font-code-sm text-[11px] font-bold text-primary">
                        {citation.tier.replace('_', ' ')}
                      </span>
                    </div>

                    {citation.exactQuote && (
                      <blockquote className="font-serif italic text-on-surface text-[14px] bg-surface-container-lowest p-space-sm rounded-lg border border-outline-variant/60">
                        "{citation.exactQuote}"
                      </blockquote>
                    )}

                    {citation.url && (
                      <div className="pt-1">
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-code-sm text-[12px] text-primary hover:underline inline-flex items-center gap-1"
                        >
                          <span>{citation.url}</span>
                          <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                        </a>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
