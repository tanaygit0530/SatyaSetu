'use client';

import React, { useState, useEffect } from 'react';
import { SourceTierBadge } from '@/components/evidence/SourceTierBadge';
import { formatDate } from '@/lib/utils';
import { listAuthoritativeSources } from '@/lib/api';
import { AuthoritativeSource } from '@/types';

export default function AdminSourcesPage() {
  const [sources, setSources] = useState<AuthoritativeSource[]>([]);
  const [filter, setFilter] = useState<string>('ALL');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadSources() {
      try {
        setLoading(true);
        const data = await listAuthoritativeSources();
        if (!isMounted) return;
        setSources(data);
      } catch (err) {
        console.error('Failed to load authoritative sources:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadSources();

    return () => {
      isMounted = false;
    };
  }, []);

  const filtered = sources.filter((s) => {
    const matchesFilter = filter === 'ALL' || s.tier === filter;
    const matchesSearch =
      search === '' ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.domain.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-space-lg">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">policy</span>
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              OFFICIAL REGISTRY REPOSITORIES
            </span>
          </div>
          <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
            Authoritative Source Registry & Precedence Matrix
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Official government gazettes, NIC portals, statutory authorities, and legal databases indexed into SachCheck.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-space-sm items-stretch sm:items-center justify-between bg-surface-container-lowest p-space-md rounded-xl border border-outline-variant shadow-2xs">
        <div className="relative flex-1 max-w-md">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
            search
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search verified registries, ministries, domains..."
            className="w-full h-10 pl-9 pr-4 rounded-xl bg-surface-container-low border border-outline-variant font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-primary"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto">
          {['ALL', 'TIER_1_PRIMARY', 'TIER_2_SECONDARY', 'TIER_3_REPUTABLE'].map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setFilter(cat)}
              className={`px-2.5 py-1 rounded-lg text-label-sm font-semibold shrink-0 transition-colors ${
                filter === cat
                  ? 'bg-primary text-on-primary font-bold shadow-xs'
                  : 'bg-surface-container-low text-on-surface-variant hover:text-on-surface border border-outline-variant'
              }`}
            >
              {cat === 'ALL' ? 'All Tiers' : cat.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="p-space-xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="font-body-sm text-on-surface-variant">Loading registered sources from Source Registry...</p>
        </div>
      )}

      {/* Sources Grid */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-md">
          {filtered.map((source) => (
            <div
              key={source.id}
              className="p-space-lg rounded-2xl bg-surface-container-lowest border border-outline-variant hover:border-primary/40 transition-colors shadow-2xs space-y-space-sm flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <SourceTierBadge tier={source.tier} />
                  <span className="font-code-sm text-[11px] text-tertiary font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    Active Registry
                  </span>
                </div>

                <div>
                  <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                    {source.name}
                  </h3>
                  <a
                    href={`https://${source.domain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-code-sm text-[12px] text-primary hover:underline inline-flex items-center gap-1"
                  >
                    <span>{source.domain}</span>
                    <span className="material-symbols-outlined text-[12px]">open_in_new</span>
                  </a>
                </div>
              </div>

              <div className="pt-space-sm border-t border-outline-variant/60 flex items-center justify-between font-label-sm text-[11px] text-on-surface-variant">
                <span>Precedence: Tier {source.precedenceRank}</span>
                <span>Category: {source.category}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
