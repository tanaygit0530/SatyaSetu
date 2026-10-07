'use client';

import React, { useState } from 'react';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { MOCK_REVIEW_QUEUE } from '@/lib/mock/admin';
import { formatDate } from '@/lib/utils';
import { ReviewQueueItem } from '@/types';

export default function AdminReviewQueuePage() {
  const [queue, setQueue] = useState<ReviewQueueItem[]>(MOCK_REVIEW_QUEUE);
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(queue[0] || null);

  const handleResolve = (id: string, action: 'CONFIRM' | 'OVERRIDE') => {
    alert(`Dispute ${id} resolved with action: ${action}`);
    setQueue((prev) => prev.filter((item) => item.id !== id));
    setSelectedItem(queue[1] || null);
  };

  return (
    <div className="space-y-space-lg">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-error text-[20px]">rate_review</span>
            <span className="font-code-sm text-[12px] text-error font-bold uppercase tracking-wider">
              CITIZEN DISPUTES & EDGE CASES
            </span>
          </div>
          <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
            Review & Dispute Queue
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Disputed claims where citizens or domain experts have submitted counter-documents.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full bg-error-container text-on-error-container font-code-sm text-[12px] font-bold">
            {queue.length} Pending Disputes
          </span>
        </div>
      </div>

      {/* Review Layout: Queue List + Active Dispute Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg">
        {/* List */}
        <div className="space-y-space-sm">
          {queue.length === 0 ? (
            <div className="p-space-lg rounded-2xl bg-surface-container-lowest border border-outline-variant text-center space-y-2">
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
                      ? 'bg-surface-container-lowest border-primary shadow-xs ring-1 ring-primary/20'
                      : 'bg-surface-container-lowest border-outline-variant hover:border-primary/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-code-sm text-[11px] font-bold text-primary">
                      {item.id} • #{item.checkId}
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-error-container/40 text-error font-code-sm text-[10px] font-bold uppercase">
                      {item.priority} Priority
                    </span>
                  </div>

                  <p className="font-serif italic text-[14px] text-on-surface line-clamp-2">
                    "{item.claimText}"
                  </p>

                  <div className="flex items-center justify-between pt-1 border-t border-outline-variant/60 font-code-sm text-[11px] text-on-surface-variant">
                    <span>By: {item.submittedBy}</span>
                    <span>{formatDate(item.createdAt)}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Dispute Details & Decision Actions */}
        {selectedItem && (
          <div className="lg:col-span-2 rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-outline-variant">
              <div>
                <span className="font-code-sm text-[11px] text-outline font-bold">
                  DISPUTE DOSSIER #{selectedItem.id}
                </span>
                <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                  Case #{selectedItem.checkId} • Claim #{selectedItem.claimId}
                </h3>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[12px] text-on-surface-variant font-code-sm">Machine Verdict:</span>
                <VerdictBadge verdict={selectedItem.automatedVerdict} size="sm" />
              </div>
            </div>

            <div className="space-y-1">
              <span className="font-label-sm text-[11px] uppercase tracking-wider text-outline font-bold">
                Disputed Claim Under Review:
              </span>
              <p className="font-serif italic text-[16px] text-on-surface p-space-md rounded-xl bg-surface-container-low border border-outline-variant">
                "{selectedItem.claimText}"
              </p>
            </div>

            <div className="p-space-md rounded-xl bg-amber-50 border border-amber-200 space-y-1 text-[13px]">
              <span className="font-bold text-amber-900 block">Citizen Submitter's Contention:</span>
              <p className="text-amber-800">{selectedItem.disputeReason}</p>
              <div className="pt-1 text-[11px] text-amber-700 font-code-sm">
                Submitter ID: {selectedItem.submittedBy} • Received: {formatDate(selectedItem.createdAt)}
              </div>
            </div>

            <div className="space-y-2">
              <span className="font-label-sm text-[11px] uppercase tracking-wider text-outline font-bold">
                Auditor Adjudication Actions:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleResolve(selectedItem.id, 'CONFIRM')}
                  className="py-2.5 px-3 rounded-xl bg-primary text-on-primary font-label-md text-label-md font-bold hover:bg-primary-container transition-colors shadow-2xs"
                >
                  Uphold Machine Finding
                </button>
                <button
                  type="button"
                  onClick={() => handleResolve(selectedItem.id, 'OVERRIDE')}
                  className="py-2.5 px-3 rounded-xl border border-secondary text-secondary hover:bg-secondary/10 font-label-md text-label-md font-bold transition-colors"
                >
                  Override Finding
                </button>
                <button
                  type="button"
                  onClick={() => alert(`Escalated case ${selectedItem.id} to Legal Registry.`)}
                  className="py-2.5 px-3 rounded-xl border border-outline-variant text-on-surface font-label-md text-label-md hover:bg-surface-container transition-colors"
                >
                  Escalate to Judiciary
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
