'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { MOCK_HISTORY_ITEMS } from '@/lib/mock/history';
import { formatDate } from '@/lib/utils';
import { Verdict } from '@/types';

export default function HistoryPage() {
  const [filter, setFilter] = useState<string>('ALL');
  const [items, setItems] = useState(MOCK_HISTORY_ITEMS);
  const [search, setSearch] = useState('');

  const filteredItems = items.filter((item) => {
    const matchesFilter = filter === 'ALL' || item.verdict === filter;
    const matchesSearch =
      search === '' ||
      item.title.toLowerCase().includes(search.toLowerCase()) ||
      item.snippet.toLowerCase().includes(search.toLowerCase()) ||
      item.checkId.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const clearHistory = () => {
    if (confirm('Clear local verification history from this device?')) {
      setItems([]);
    }
  };

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-lg">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-md pb-space-xs border-b border-outline-variant">
          <div>
            <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
              Verification History
            </h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Timeline of forwards and claims checked on this device. Stored locally with zero server tracking.
            </p>
          </div>

          {items.length > 0 && (
            <button
              type="button"
              onClick={clearHistory}
              className="self-start sm:self-auto px-3 py-1.5 rounded-lg border border-outline-variant text-error hover:bg-error-container/20 font-label-sm text-label-sm flex items-center gap-1.5 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">delete_sweep</span>
              <span>Clear History</span>
            </button>
          )}
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row gap-space-sm items-stretch sm:items-center justify-between">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
              search
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search checks, keywords, case IDs..."
              className="w-full h-10 pl-9 pr-4 rounded-xl bg-surface-container-lowest border border-outline-variant font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Verdict Filter Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {['ALL', 'FALSE', 'OUTDATED', 'VERIFIED', 'CANNOT_BE_CONFIRMED'].map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setFilter(v)}
                className={`px-2.5 py-1 rounded-lg text-label-sm font-semibold shrink-0 transition-colors ${
                  filter === v
                    ? 'bg-primary text-on-primary font-bold shadow-xs'
                    : 'bg-surface-container-low text-on-surface-variant hover:text-on-surface border border-outline-variant'
                }`}
              >
                {v === 'ALL' ? 'All Records' : v.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Items List */}
        {filteredItems.length === 0 ? (
          <div className="p-space-2xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
            <span className="material-symbols-outlined text-[36px] text-outline">history</span>
            <p className="font-body-md text-on-surface-variant">
              No verification records found matching your query.
            </p>
            <Link
              href="/check"
              className="inline-flex items-center gap-1 px-4 py-2 rounded-xl bg-primary text-on-primary font-label-md text-label-md font-bold"
            >
              Check a Forward
            </Link>
          </div>
        ) : (
          <div className="space-y-space-sm">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant hover:border-primary/40 transition-colors shadow-2xs space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-code-sm text-[11px] font-bold text-primary bg-surface-container px-2 py-0.5 rounded">
                      #{item.checkId}
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-surface-container-low font-code-sm text-[11px] text-on-surface-variant border border-outline-variant">
                      {item.inputType}
                    </span>
                    <span className="font-code-sm text-[11px] text-outline">
                      {formatDate(item.timestamp)}
                    </span>
                  </div>

                  <VerdictBadge verdict={item.verdict} size="sm" />
                </div>

                <Link
                  href={`/check/${item.checkId}`}
                  className="font-headline-sm text-headline-sm font-bold text-on-surface hover:text-primary transition-colors block"
                >
                  {item.title}
                </Link>

                <p className="font-body-sm text-body-sm text-on-surface-variant line-clamp-2">
                  {item.snippet}
                </p>

                <div className="pt-2 border-t border-outline-variant/60 flex items-center justify-between font-label-sm text-[12px]">
                  <span className="text-on-surface-variant">
                    {item.claimsCount} claims extracted
                  </span>

                  <Link
                    href={`/check/${item.checkId}`}
                    className="text-primary hover:underline font-bold inline-flex items-center gap-1"
                  >
                    <span>View Dossier</span>
                    <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
