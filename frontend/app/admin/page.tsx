'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { formatDate } from '@/lib/utils';
import { listChecks, adaptCheckToUi } from '@/lib/api';
import { VerificationResult } from '@/types';

export default function AdminOverviewPage() {
  const [recentChecks, setRecentChecks] = useState<VerificationResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadOperationalData() {
      try {
        setLoading(true);
        const checksData = await listChecks(15);
        if (!isMounted) return;
        setRecentChecks(checksData.map(adaptCheckToUi));
      } catch (err) {
        console.error('Failed to load operational checks:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadOperationalData();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-space-lg">
      {/* Top Operations Desk Banner */}
      <div className="flex flex-wrap items-center justify-between gap-space-md bg-surface-container-lowest p-space-md rounded-xl border border-outline-variant shadow-2xs">
        <div className="flex flex-wrap items-center gap-space-md">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-emerald-100 text-[#146336] dark:bg-emerald-950 dark:text-emerald-300 font-code-sm text-[12px] font-bold">
              <span className="w-2 h-2 rounded-full bg-[#1E8E4E] animate-pulse mr-1.5"></span>
              Live Pipeline Active
            </span>
            <span className="font-code-sm text-[12px] text-on-surface-variant font-medium">
              Twilio Webhook & Deterministic Engine
            </span>
          </div>

          <div className="h-4 w-px bg-surface-container-highest hidden sm:block"></div>

          <div className="flex items-center gap-1.5 text-on-surface-variant font-body-sm text-body-sm">
            <span className="material-symbols-outlined text-primary text-[18px]">
              fingerprint
            </span>
            <span className="font-medium text-on-surface">Shared Rumour Memory:</span>
            <span className="font-code-sm text-code-sm text-primary font-bold">
              L1/L2 Cache Active
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/admin/checks"
            className="px-3.5 py-1.5 rounded-lg bg-primary text-on-primary font-label-sm text-label-sm font-semibold hover:bg-primary-container transition-colors flex items-center gap-1.5"
          >
            <span className="material-symbols-outlined text-[16px]">fact_check</span>
            <span>Live Audit Stream</span>
          </Link>
        </div>
      </div>

      {/* Operational Work Desk Tiles (No Analytics / Pure Operations) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
        {/* Review Queue */}
        <Link
          href="/admin/review"
          className="rounded-2xl bg-surface-container-lowest border border-outline-variant hover:border-primary/50 p-space-md space-y-2 transition-all shadow-2xs group"
        >
          <div className="flex items-center justify-between">
            <span className="p-2 rounded-xl bg-amber-500/10 text-amber-600 font-bold">
              <span className="material-symbols-outlined text-[22px]">rate_review</span>
            </span>
            <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-700 dark:text-amber-300 font-bold text-xs">
              14 Pending
            </span>
          </div>
          <div>
            <h3 className="font-headline-sm text-base font-bold text-on-surface group-hover:text-primary transition-colors">
              Human Review Queue
            </h3>
            <p className="text-xs text-on-surface-variant">
              Triage ambiguous forwards and review border cases.
            </p>
          </div>
        </Link>

        {/* Live Checks */}
        <Link
          href="/admin/checks"
          className="rounded-2xl bg-surface-container-lowest border border-outline-variant hover:border-primary/50 p-space-md space-y-2 transition-all shadow-2xs group"
        >
          <div className="flex items-center justify-between">
            <span className="p-2 rounded-xl bg-primary/10 text-primary font-bold">
              <span className="material-symbols-outlined text-[22px]">history_edu</span>
            </span>
            <span className="text-xs font-semibold text-outline">Real-time</span>
          </div>
          <div>
            <h3 className="font-headline-sm text-base font-bold text-on-surface group-hover:text-primary transition-colors">
              Ingestion Audit Stream
            </h3>
            <p className="text-xs text-on-surface-variant">
              Inspect raw statements, extracted claims, and rule traces.
            </p>
          </div>
        </Link>

        {/* Rumour Memory */}
        <Link
          href="/admin/rumours"
          className="rounded-2xl bg-surface-container-lowest border border-outline-variant hover:border-primary/50 p-space-md space-y-2 transition-all shadow-2xs group"
        >
          <div className="flex items-center justify-between">
            <span className="p-2 rounded-xl bg-secondary/10 text-secondary font-bold">
              <span className="material-symbols-outlined text-[22px]">fingerprint</span>
            </span>
            <span className="text-xs font-semibold text-outline">Shared L1/L2</span>
          </div>
          <div>
            <h3 className="font-headline-sm text-base font-bold text-on-surface group-hover:text-primary transition-colors">
              Rumour Memory Bank
            </h3>
            <p className="text-xs text-on-surface-variant">
              Manage deduplicated viral clusters and freshness TTLs.
            </p>
          </div>
        </Link>

        {/* Sources Registry */}
        <Link
          href="/admin/sources"
          className="rounded-2xl bg-surface-container-lowest border border-outline-variant hover:border-primary/50 p-space-md space-y-2 transition-all shadow-2xs group"
        >
          <div className="flex items-center justify-between">
            <span className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 font-bold">
              <span className="material-symbols-outlined text-[22px]">policy</span>
            </span>
            <span className="text-xs font-semibold text-outline">Tier 1 - 3</span>
          </div>
          <div>
            <h3 className="font-headline-sm text-base font-bold text-on-surface group-hover:text-primary transition-colors">
              Authoritative Registry
            </h3>
            <p className="text-xs text-on-surface-variant">
              Inspect gazette domains, statutory sources, and IFCN publishers.
            </p>
          </div>
        </Link>
      </div>

      {/* Live Operational Stream Table (Operational Inspection Only) */}
      <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
          <div>
            <h2 className="font-headline-sm text-lg font-bold text-on-surface">
              Live Pipeline Ingestion Desk
            </h2>
            <p className="font-body-sm text-[12px] text-on-surface-variant">
              Operational log of recently received WhatsApp and Web verification submissions.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/admin/checks"
              className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
            >
              <span>View Full Stream</span>
              <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-on-surface-variant space-y-2">
            <span className="material-symbols-outlined animate-spin text-[28px] text-primary">
              progress_activity
            </span>
            <p className="text-xs">Loading operational checks stream...</p>
          </div>
        ) : recentChecks.length === 0 ? (
          <div className="py-8 text-center text-on-surface-variant text-xs">
            No active submissions recorded in the pipeline yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-body-sm text-[13px]">
              <thead>
                <tr className="border-b border-outline-variant text-[11px] font-semibold text-outline uppercase tracking-wider">
                  <th className="py-2.5 px-3">Check ID</th>
                  <th className="py-2.5 px-3">Origin / Type</th>
                  <th className="py-2.5 px-3">Statement Summary</th>
                  <th className="py-2.5 px-3">Verdict</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/50">
                {recentChecks.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-container-low/60 transition-colors">
                    <td className="py-3 px-3 font-code-sm font-semibold text-on-surface">
                      {item.id}
                    </td>
                    <td className="py-3 px-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container-low text-[11px] font-bold text-on-surface-variant">
                        {item.inputType}
                      </span>
                    </td>
                    <td className="py-3 px-3 max-w-xs truncate text-on-surface" title={item.originalMessage}>
                      {item.originalMessage}
                    </td>
                    <td className="py-3 px-3">
                      <VerdictBadge verdict={item.overallVerdict} size="sm" />
                    </td>
                    <td className="py-3 px-3 text-on-surface-variant text-[11px]">
                      {formatDate(item.submittedAt)}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <Link
                        href={`/check/${item.id}`}
                        className="px-2.5 py-1 rounded-lg border border-outline-variant bg-surface-container-low hover:bg-primary hover:text-on-primary text-xs font-semibold transition-colors inline-flex items-center gap-1"
                      >
                        <span>Inspect</span>
                        <span className="material-symbols-outlined text-[13px]">open_in_new</span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
