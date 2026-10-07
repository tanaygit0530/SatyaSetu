'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { MOCK_VERIFICATION_RESULTS } from '@/lib/mock/checks';
import { formatDate } from '@/lib/utils';
import { Verdict } from '@/types';

export default function AdminLiveChecksPage() {
  const [search, setSearch] = useState('');
  const [filterVerdict, setFilterVerdict] = useState<string>('ALL');
  const [selectedCheckId, setSelectedCheckId] = useState<string>('SC-2026-8941');

  const allChecks = Object.values(MOCK_VERIFICATION_RESULTS);

  const filtered = allChecks.filter((c) => {
    const matchesVerdict = filterVerdict === 'ALL' || c.overallVerdict === filterVerdict;
    const matchesSearch =
      search === '' ||
      c.id.toLowerCase().includes(search.toLowerCase()) ||
      c.originalMessage.toLowerCase().includes(search.toLowerCase());
    return matchesVerdict && matchesSearch;
  });

  const activeCheck = MOCK_VERIFICATION_RESULTS[selectedCheckId] || allChecks[0];

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
            placeholder="Search checks, claims, domains..."
            className="w-full h-10 pl-9 pr-4 rounded-xl bg-surface-container-low border border-outline-variant font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-primary"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto">
          {['ALL', 'FALSE', 'OUTDATED', 'CANNOT_BE_CONFIRMED', 'VERIFIED'].map((v) => (
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
              {v === 'ALL' ? 'All Verdicts' : v.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Tri-Pane Inspection Layout: Table + Live Inspection Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg">
        {/* Table column */}
        <div className="lg:col-span-2 rounded-2xl bg-surface-container-lowest border border-outline-variant shadow-2xs overflow-hidden">
          <table className="w-full text-left font-body-sm text-[13px]">
            <thead className="bg-surface-container-low text-on-surface-variant font-label-sm text-[11px] uppercase tracking-wider border-b border-outline-variant">
              <tr>
                <th className="py-3 px-3">Case ID</th>
                <th className="py-3 px-3">Input</th>
                <th className="py-3 px-3">Message Snippet</th>
                <th className="py-3 px-3">Verdict</th>
                <th className="py-3 px-3 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60">
              {filtered.map((item) => {
                const isSelected = item.id === selectedCheckId;
                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedCheckId(item.id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-primary-fixed/20 border-l-4 border-l-primary'
                        : 'hover:bg-surface-container-low/50'
                    }`}
                  >
                    <td className="py-3 px-3 font-code-sm font-bold text-primary">
                      #{item.id}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded-full bg-surface-container font-code-sm text-[11px]">
                        {item.inputType}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-serif italic max-w-xs truncate text-on-surface">
                      "{item.originalMessage.slice(0, 50)}..."
                    </td>
                    <td className="py-3 px-3">
                      <VerdictBadge verdict={item.overallVerdict} size="sm" />
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span className="material-symbols-outlined text-outline text-[18px]">
                        chevron_right
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Live Rule & Trace Inspector Drawer */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-md space-y-space-md shadow-2xs">
          <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
            <div>
              <span className="font-code-sm text-[11px] text-outline font-bold">
                DIAGNOSTIC TRACE
              </span>
              <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                Case #{activeCheck.id}
              </h3>
            </div>
            <VerdictBadge verdict={activeCheck.overallVerdict} size="sm" />
          </div>

          <div className="space-y-1">
            <span className="font-label-sm text-[11px] uppercase tracking-wider text-outline font-bold">
              Raw Message:
            </span>
            <p className="font-serif italic text-[14px] text-on-surface p-2.5 rounded-lg bg-surface-container-low border border-outline-variant">
              "{activeCheck.originalMessage}"
            </p>
          </div>

          <div className="space-y-2">
            <span className="font-label-sm text-[11px] uppercase tracking-wider text-outline font-bold">
              Extracted Claims ({activeCheck.claims.length}):
            </span>
            <div className="space-y-2">
              {activeCheck.claims.map((claim) => (
                <div
                  key={claim.id}
                  className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant space-y-1 text-[12px]"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-code-sm font-bold">Claim #{claim.claimNumber}</span>
                    <VerdictBadge verdict={claim.verdict} size="sm" />
                  </div>
                  <p className="font-medium text-on-surface">"{claim.claimText}"</p>
                  <p className="text-on-surface-variant font-code-sm">
                    Rule: {claim.ruleMatched || 'RULE-STATUTORY'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-outline-variant flex flex-col gap-2">
            <Link
              href={`/check/${activeCheck.id}`}
              className="w-full py-2 rounded-xl bg-primary text-on-primary font-label-md text-label-md font-bold text-center hover:bg-primary-container transition-colors"
            >
              Open Full Citizen Result
            </Link>
            <Link
              href={`/check/${activeCheck.id}/evidence/${activeCheck.claims[0]?.id || 'CLM-8941-1'}`}
              className="w-full py-2 rounded-xl border border-outline-variant text-on-surface font-label-md text-label-md font-semibold text-center hover:bg-surface-container-low transition-colors"
            >
              Inspect Source Dossier
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
