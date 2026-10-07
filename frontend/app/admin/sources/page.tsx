'use client';

import React, { useState } from 'react';
import { SourceTierBadge } from '@/components/evidence/SourceTierBadge';
import { MOCK_SOURCES } from '@/lib/mock/admin';
import { formatDate } from '@/lib/utils';
import { AuthoritativeSource } from '@/types';

export default function AdminSourcesPage() {
  const [sources, setSources] = useState<AuthoritativeSource[]>(MOCK_SOURCES);
  const [filter, setFilter] = useState<string>('ALL');
  const [search, setSearch] = useState('');

  const filtered = sources.filter((s) => {
    const matchesFilter = filter === 'ALL' || s.category === filter;
    const matchesSearch =
      search === '' ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.domain.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleSyncSource = (id: string) => {
    alert(`Triggered immediate incremental crawler sync for ${id}.`);
  };

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

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => alert('All 48 crawlers synced with NIC Gateway.')}
            className="px-3 py-1.5 rounded-lg bg-primary text-on-primary font-label-sm text-label-sm font-semibold hover:bg-primary-container transition-colors flex items-center gap-1.5 shadow-2xs"
          >
            <span className="material-symbols-outlined text-[16px]">sync</span>
            <span>Sync All Repositories</span>
          </button>
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
            placeholder="Search repository name, domain, ministry..."
            className="w-full h-10 pl-9 pr-4 rounded-xl bg-surface-container-low border border-outline-variant font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-primary"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto">
          {['ALL', 'STATE_GAZETTE', 'PIB', 'MINISTRY', 'STATUTORY_BODY'].map((cat) => (
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
              {cat === 'ALL' ? 'All Registries' : cat.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Sources Table */}
      <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant overflow-hidden shadow-2xs">
        <table className="w-full text-left font-body-sm text-[13px]">
          <thead className="bg-surface-container-low text-on-surface-variant font-label-sm text-[11px] uppercase tracking-wider border-b border-outline-variant">
            <tr>
              <th className="py-3 px-3">Precedence</th>
              <th className="py-3 px-3">Registry Name</th>
              <th className="py-3 px-3">Domain</th>
              <th className="py-3 px-3">Tier</th>
              <th className="py-3 px-3">Records Indexed</th>
              <th className="py-3 px-3">Status</th>
              <th className="py-3 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/60">
            {filtered.map((s) => (
              <tr key={s.id} className="hover:bg-surface-container-low/50">
                <td className="py-3 px-3 font-code-sm font-bold text-primary">
                  #{s.precedenceRank}
                </td>
                <td className="py-3 px-3 font-bold text-on-surface">
                  {s.name}
                </td>
                <td className="py-3 px-3 font-code-sm text-on-surface-variant">
                  {s.domain}
                </td>
                <td className="py-3 px-3">
                  <SourceTierBadge tier={s.tier} />
                </td>
                <td className="py-3 px-3 font-code-sm">
                  {s.recordsIndexed.toLocaleString()} records
                </td>
                <td className="py-3 px-3">
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[11px] font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#1E8E4E]"></span>
                    {s.status}
                  </span>
                </td>
                <td className="py-3 px-3 text-right">
                  <button
                    type="button"
                    onClick={() => handleSyncSource(s.id)}
                    className="text-primary hover:underline font-semibold font-label-sm"
                  >
                    Sync Now
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
