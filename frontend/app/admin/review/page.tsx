'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { formatDate } from '@/lib/utils';
import { listChecks, adaptCheckToUi } from '@/lib/api';
import { ReviewQueueItem } from '@/types';

export default function AdminReviewQueuePage() {
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadReviewItems() {
      try {
        setLoading(true);
        // Load real checks that could have dispute flags or unconfirmed status
        const checks = await listChecks(20);
        if (!isMounted) return;

        // Map checks that need auditor attention (e.g. CANNOT_BE_CONFIRMED or PARTLY_SUPPORTED)
        const itemsToReview: ReviewQueueItem[] = [];
        checks.forEach((chk) => {
          const adapted = adaptCheckToUi(chk);
          if (adapted.overallVerdict === 'CANNOT_BE_CONFIRMED' || adapted.overallVerdict === 'PARTLY_SUPPORTED') {
            itemsToReview.push({
              id: `DISP-${chk.check_id}`,
              checkId: chk.check_id,
              claimId: adapted.claims[0]?.id || `clm_${chk.check_id}`,
              claimText: adapted.claims[0]?.claimText || chk.text,
              automatedVerdict: adapted.overallVerdict,
              confidence: adapted.claims[0]?.confidence || 50,
              disputeReason: 'Automated verdict marked unconfirmed or partly supported; pending auditor gazette certification.',
              submittedBy: 'Citizen Tipline',
              createdAt: chk.created_at || new Date().toISOString(),
              priority: 'MEDIUM',
              status: 'PENDING',
            });
          }
        });

        setQueue(itemsToReview);
        if (itemsToReview.length > 0) {
          setSelectedItem(itemsToReview[0]);
        }
      } catch (err) {
        console.error('Failed to load review queue:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadReviewItems();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleResolve = (id: string, action: 'CONFIRM' | 'OVERRIDE') => {
    alert(`Dispute ${id} marked: ${action}.`);
    setQueue((prev) => prev.filter((item) => item.id !== id));
    setSelectedItem(queue[1] || null);
  };

  return (
    <div className="space-y-space-lg">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">rate_review</span>
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              CITIZEN DISPUTES & REVIEW AUDIT
            </span>
          </div>
          <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
            Review & Dispute Queue
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Claims with partial or unconfirmed evidence requiring manual statutory certification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface font-code-sm text-[12px] font-bold">
            {queue.length} Pending In Queue
          </span>
        </div>
      </div>

      {loading && (
        <div className="p-space-xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="font-body-sm text-on-surface-variant">Checking review queue from repository...</p>
        </div>
      )}

      {/* Review Layout */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg">
          {/* List */}
          <div className="space-y-space-sm">
            {queue.length === 0 ? (
              <div className="p-space-xl rounded-2xl bg-surface-container-lowest border border-outline-variant text-center space-y-2">
                <span className="material-symbols-outlined text-[32px] text-tertiary">check_circle</span>
                <p className="font-body-md text-on-surface font-semibold">Queue All Clear</p>
                <p className="font-body-sm text-[12px] text-on-surface-variant">
                  No outstanding citizen disputes require human auditor intervention.
                </p>
              </div>
            ) : (
              queue.map((item) => {
                const isSelected = selectedItem?.id === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={`p-space-md rounded-xl border transition-all cursor-pointer space-y-2 ${
                      isSelected
                        ? 'bg-surface-container-lowest border-primary shadow-xs ring-1 ring-primary/30'
                        : 'bg-surface-container-lowest border-outline-variant hover:border-primary/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-code-sm text-[11px] font-bold text-primary">
                        #{item.checkId}
                      </span>
                      <VerdictBadge verdict={item.automatedVerdict} size="sm" />
                    </div>

                    <p className="font-serif italic text-[14px] text-on-surface line-clamp-2">
                      "{item.claimText}"
                    </p>

                    <div className="flex items-center justify-between font-label-sm text-[11px] text-on-surface-variant pt-1 border-t border-outline-variant/60">
                      <span>{formatDate(item.createdAt)}</span>
                      <span className="text-primary font-bold">Inspect</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Dispute Inspector Panel */}
          <div className="lg:col-span-2">
            {selectedItem ? (
              <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
                <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant">
                  <div>
                    <span className="font-code-sm text-[11px] text-outline font-bold uppercase">
                      Auditor Case Inspection
                    </span>
                    <h2 className="font-headline-sm text-lg font-bold text-on-surface">
                      Check #{selectedItem.checkId}
                    </h2>
                  </div>
                  <VerdictBadge verdict={selectedItem.automatedVerdict} size="sm" />
                </div>

                <div className="space-y-1">
                  <span className="font-label-sm text-[11px] font-bold uppercase text-outline">
                    Audited Proposition:
                  </span>
                  <blockquote className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant font-serif italic text-on-surface text-[15px]">
                    "{selectedItem.claimText}"
                  </blockquote>
                </div>

                <div className="space-y-1">
                  <span className="font-label-sm text-[11px] font-bold uppercase text-outline">
                    Dispute Reason:
                  </span>
                  <p className="font-body-sm text-on-surface-variant bg-surface-container-low p-space-sm rounded-lg border border-outline-variant">
                    {selectedItem.disputeReason}
                  </p>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-outline-variant">
                  <Link
                    href={`/check/${encodeURIComponent(selectedItem.checkId)}`}
                    className="font-label-sm text-primary font-bold hover:underline"
                  >
                    View Complete Case Dossier →
                  </Link>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleResolve(selectedItem.id, 'CONFIRM')}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-label-sm font-semibold hover:bg-emerald-700 transition-colors"
                    >
                      Confirm Automated Verdict
                    </button>
                    <button
                      type="button"
                      onClick={() => handleResolve(selectedItem.id, 'OVERRIDE')}
                      className="px-3 py-1.5 rounded-lg border border-outline-variant text-on-surface font-label-sm font-semibold hover:bg-surface-container transition-colors"
                    >
                      Override
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center p-space-xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant text-on-surface-variant">
                Select an item from the queue to inspect dispute details.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
