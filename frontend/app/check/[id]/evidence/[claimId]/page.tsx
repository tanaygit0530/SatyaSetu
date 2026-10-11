'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { SourceTierBadge } from '@/components/evidence/SourceTierBadge';
import { QuoteBlock } from '@/components/evidence/QuoteBlock';
import { ConfidenceBand } from '@/components/verdict/ConfidenceBand';
import { getCheckDetail, adaptCheckToUi } from '@/lib/api';
import { VerificationResult, Claim } from '@/types';

export default function ForensicEvidencePage() {
  const params = useParams();
  const checkId = (params?.id as string) || '';
  const claimId = (params?.claimId as string) || '';

  const [check, setCheck] = useState<VerificationResult | null>(null);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checkId) return;

    let isMounted = true;

    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const raw = await getCheckDetail(checkId);

        if (!isMounted) return;

        const adapted = adaptCheckToUi(raw);
        setCheck(adapted);

        const foundClaim =
          adapted.claims.find((c) => c.id === claimId) ||
          adapted.claims.find((c) => String(c.claimNumber) === claimId) ||
          adapted.claims[0];

        setClaim(foundClaim || null);
      } catch (err: any) {
        if (!isMounted) return;
        setError(err?.message || 'Evidence record could not be loaded.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [checkId, claimId]);

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-6xl mx-auto px-margin md:px-margin-desktop py-space-xl text-center">
          <div className="p-space-xl rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-4">
            <div className="w-10 h-10 border-3 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="font-body-md text-on-surface-variant">Loading forensic evidence audit trail...</p>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error || !check || !claim) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-2xl text-center space-y-4">
          <div className="p-space-2xl rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-4 shadow-sm">
            <h1 className="font-headline-lg text-2xl font-bold text-on-surface">Evidence Dossier Not Found</h1>
            <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
              {error || 'No claim matching this identifier was located in the verification database.'}
            </p>
            <div className="pt-2">
              <Link href={`/check/${checkId}`} className="px-4 py-2 rounded-xl bg-primary text-on-primary font-label-md font-semibold">
                Back to Case #{checkId}
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

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
                {claim.ruleMatched && (
                  <span className="font-code-sm text-[11px] text-outline">
                    Rule: {claim.ruleMatched}
                  </span>
                )}
              </div>
              <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
                Forensic Claim Audit & Source Inspection
              </h1>
            </div>

            <VerdictBadge verdict={claim.verdict} size="lg" />
          </div>

          {/* Investigated Proposition Block */}
          <div className="pt-2">
            <span className="font-label-sm text-[11px] font-bold uppercase tracking-wider text-outline">
              Isolated Statement Under Audit:
            </span>
            <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant mt-1 font-serif text-[17px] text-on-surface italic">
              "{claim.claimText}"
            </div>
          </div>

          {/* Confidence and Diagnostic Ratings */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md pt-2 border-t border-outline-variant">
            <ConfidenceBand score={claim.confidence} showMetric={true} />
            <div className="flex items-center justify-end font-code-sm text-[12px] text-on-surface-variant">
              <span>Channel: <strong className="text-on-surface">{check.inputType}</strong></span>
              <span className="mx-2">•</span>
              <span>Grounding: <strong className="text-tertiary">Deterministic</strong></span>
            </div>
          </div>
        </div>

        {/* Primary Grounding Evidence Records */}
        <section className="space-y-space-md">
          <div>
            <h2 className="font-headline-md text-xl font-bold text-on-surface">
              Corroborating & Refuting Evidence Citations ({claim.sourceCitations.length})
            </h2>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Exclusively certified statutory records, verified gazettes, and official public statements.
            </p>
          </div>

          {claim.sourceCitations.length === 0 ? (
            <div className="p-space-lg rounded-xl bg-surface-container-lowest border border-outline-variant text-center space-y-2">
              <span className="material-symbols-outlined text-[32px] text-outline">search_off</span>
              <p className="font-body-md text-on-surface-variant">
                No direct citations found for this claim. Classified under {claim.verdict}.
              </p>
            </div>
          ) : (
            <div className="space-y-space-md">
              {claim.sourceCitations.map((citation) => (
                <div
                  key={citation.id}
                  className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-md md:p-space-lg space-y-space-md shadow-2xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm">
                    <div className="flex items-center gap-space-sm">
                      <SourceTierBadge tier={citation.tier} />
                      <div>
                        <h3 className="font-label-lg font-bold text-on-surface">
                          {citation.publisher}
                        </h3>
                        <span className="font-code-sm text-[11px] text-outline">
                          Domain: {citation.domain}
                        </span>
                      </div>
                    </div>
                  </div>

                  {citation.exactQuote && (
                    <QuoteBlock
                      text={citation.exactQuote}
                      source={citation.title || citation.publisher}
                      highlightType={claim.verdict === 'VERIFIED' ? 'supporting' : 'counter'}
                    />
                  )}

                  {citation.url && (
                    <div className="pt-2 flex items-center justify-between text-body-sm">
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
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
