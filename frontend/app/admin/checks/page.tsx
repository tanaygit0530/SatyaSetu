'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { formatDate } from '@/lib/utils';
import { listChecks, adaptCheckToUi } from '@/lib/api';
import { VerificationResult } from '@/types';

export default function AdminLiveChecksPage() {
  const [search, setSearch] = useState('');
  const [filterVerdict, setFilterVerdict] = useState<string>('ALL');
  const [allChecks, setAllChecks] = useState<VerificationResult[]>([]);
  const [selectedCheckId, setSelectedCheckId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadChecks() {
      try {
        setLoading(true);
        const raw = await listChecks(100);
        if (!isMounted) return;

        const adapted = raw.map(adaptCheckToUi);
        setAllChecks(adapted);
        if (adapted.length > 0) {
          setSelectedCheckId(adapted[0].id);
        }
      } catch (err) {
        console.error('Failed to load checks stream:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadChecks();

    return () => {
      isMounted = false;
    };
  }, []);

  const filtered = allChecks.filter((c) => {
    const matchesVerdict = filterVerdict === 'ALL' || c.overallVerdict === filterVerdict;
    const matchesSearch =
      search === '' ||
      c.id.toLowerCase().includes(search.toLowerCase()) ||
      c.originalMessage.toLowerCase().includes(search.toLowerCase());
    return matchesVerdict && matchesSearch;
  });

  const activeCheck = allChecks.find((c) => c.id === selectedCheckId) || filtered[0] || null;

  return (
    <div className="space-y-space-lg">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-code-sm text-[12px] text-tertiary font-bold uppercase tracking-wider">
              REAL-TIME STREAM
            </span>
          </div>
          <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
            Live Evidentiary Ingestion & Deterministic Inspection
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Full diagnostic audit trail of forwarded messages, claim breakdowns, and rule execution trees.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row gap-space-sm items-stretch sm:items-center justify-between bg-surface-container-lowest p-space-md rounded-xl border border-outline-variant shadow-2xs">
        <div className="relative flex-1 max-w-md">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
            search
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search checks, claims, case IDs..."
            className="w-full h-10 pl-9 pr-4 rounded-xl bg-surface-container-low border border-outline-variant font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-primary"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto">
          {['ALL', 'VERIFIED', 'FALSE', 'OUTDATED', 'PARTLY_SUPPORTED', 'CANNOT_BE_CONFIRMED'].map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setFilterVerdict(v)}
              className={`px-2.5 py-1 rounded-lg text-label-sm font-semibold shrink-0 transition-colors ${
                filterVerdict === v
                  ? 'bg-primary text-on-primary font-bold shadow-xs'
                  : 'bg-surface-container-low text-on-surface-variant hover:text-on-surface border border-outline-variant'
              }`}
            >
              {v === 'ALL' ? 'All' : v.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="p-space-xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="font-body-sm text-on-surface-variant">Loading live verification stream from repository...</p>
        </div>
      )}

      {/* Main Split-Screen Audit Layout */}
      {!loading && allChecks.length === 0 ? (
        <div className="p-space-2xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
          <span className="material-symbols-outlined text-[36px] text-outline">fact_check</span>
          <h3 className="font-headline-sm text-lg font-bold text-on-surface">No Verification Checks Recorded Yet</h3>
          <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
            Once checks are submitted via WhatsApp tipline or the web app, their live audit records and rule traces will appear here.
          </p>
          <div className="pt-2">
            <Link href="/check" className="px-4 py-2 rounded-xl bg-primary text-on-primary font-label-md font-bold">
              Submit Test Check
            </Link>
          </div>
        </div>
      ) : (
        !loading && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-start">
            {/* Left Stream List (5 cols) */}
            <div className="lg:col-span-5 space-y-space-sm max-h-[750px] overflow-y-auto pr-1">
              {filtered.map((item) => {
                const isSelected = item.id === activeCheck?.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedCheckId(item.id)}
                    className={`p-space-md rounded-xl border transition-all cursor-pointer space-y-2 ${
                      isSelected
                        ? 'bg-surface-container-lowest border-primary ring-1 ring-primary/30 shadow-xs'
                        : 'bg-surface-container-lowest border-outline-variant hover:border-primary/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-code-sm text-[11px]">
                        <span className="font-bold text-primary bg-surface-container px-2 py-0.5 rounded">
                          #{item.id}
                        </span>
                        <span className="text-outline">{formatDate(item.submittedAt)}</span>
                      </div>
                      <VerdictBadge verdict={item.overallVerdict} size="sm" />
                    </div>

                    <p className="font-serif italic text-[14px] text-on-surface line-clamp-2">
                      "{item.originalMessage}"
                    </p>

                    <div className="flex items-center justify-between font-label-sm text-[11px] text-on-surface-variant pt-1 border-t border-outline-variant/60">
                      <span>{item.claims.length} claims</span>
                      <span>Channel: {item.inputType}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Right Detailed Inspector Panel (7 cols) */}
            <div className="lg:col-span-7 bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
              {activeCheck ? (
                <>
                  <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant">
                    <div>
                      <span className="font-code-sm text-[11px] text-outline font-bold uppercase">
                        Active Inspection Dossier
                      </span>
                      <h2 className="font-headline-md text-xl font-bold text-on-surface">
                        Case #{activeCheck.id}
                      </h2>
                    </div>

                    <div className="flex items-center gap-2">
                      <VerdictBadge verdict={activeCheck.overallVerdict} size="md" />
                      <Link
                        href={`/check/${encodeURIComponent(activeCheck.id)}`}
                        className="px-3 py-1.5 rounded-lg bg-surface-container-low hover:bg-surface-container border border-outline-variant font-label-sm text-primary font-bold inline-flex items-center gap-1"
                      >
                        <span>Full Dossier</span>
                        <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                      </Link>
                    </div>
                  </div>

                  {/* Summary & Original Quote */}
                  <div className="space-y-2">
                    <span className="font-label-sm text-[11px] font-bold uppercase text-outline">
                      Citizen Message:
                    </span>
                    <blockquote className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant font-serif italic text-on-surface text-[15px]">
                      "{activeCheck.originalMessage}"
                    </blockquote>
                  </div>

                  {/* Claims Breakdown & Rule Traces */}
                  <div className="space-y-3 pt-2">
                    <span className="font-label-sm text-[11px] font-bold uppercase text-outline">
                      Atomic Claims & Rule Traces:
                    </span>

                    <div className="space-y-2">
                      {activeCheck.claims.map((clm) => (
                        <div
                          key={clm.id}
                          className="p-space-md rounded-xl bg-surface-container-low/50 border border-outline-variant space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-code-sm text-[11px] font-bold text-primary">
                              Claim #{clm.claimNumber}
                            </span>
                            <VerdictBadge verdict={clm.verdict} size="sm" />
                          </div>

                          <p className="font-body-sm text-on-surface font-medium">
                            "{clm.claimText}"
                          </p>

                          <p className="font-body-sm text-[12px] text-on-surface-variant">
                            {clm.summary}
                          </p>

                          {clm.ruleMatched && (
                            <div className="pt-1 font-code-sm text-[11px] text-tertiary">
                              Rule trace: {clm.ruleMatched}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="p-space-xl text-center text-on-surface-variant">
                  Select a check from the left stream to inspect its forensic trace.
                </div>
              )}
            </div>
          </div>
        )
      )}
    </div>
  );
}
