'use client';

import React from 'react';
import Link from 'next/link';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { AdminKpiCard } from '@/components/admin/AdminKpiCard';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { MOCK_ADMIN_METRICS, MOCK_HOURLY_VOLUME } from '@/lib/mock/admin';
import { MOCK_VERIFICATION_RESULTS } from '@/lib/mock/checks';

export default function AdminOverviewPage() {
  const metrics = MOCK_ADMIN_METRICS;
  const recentChecks = Object.values(MOCK_VERIFICATION_RESULTS);

  return (
    <div className="space-y-space-lg">
      {/* Top Controls & Desk Banner */}
      <div className="flex flex-wrap items-center justify-between gap-space-md bg-surface-container-lowest p-space-md rounded-xl border border-outline-variant shadow-2xs">
        <div className="flex flex-wrap items-center gap-space-md">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[12px] font-bold">
              <span className="w-2 h-2 rounded-full bg-[#1E8E4E] animate-pulse mr-1.5"></span>
              Live Pipeline Active
            </span>
            <span className="font-code-sm text-[12px] text-on-surface-variant font-medium">
              Cluster: NIC-DELHI-GW4
            </span>
          </div>

          <div className="h-4 w-px bg-surface-container-highest hidden sm:block"></div>

          <div className="flex items-center gap-1.5 text-on-surface-variant font-body-sm text-body-sm">
            <span className="material-symbols-outlined text-primary text-[18px]">
              verified_user
            </span>
            <span className="font-medium text-on-surface">Vector Cache:</span>
            <span className="font-code-sm text-code-sm text-primary font-bold">
              L1/L2 Active ({metrics.cacheHitRatio}% cached)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/admin/checks"
            className="px-3 py-1.5 rounded-lg bg-primary text-on-primary font-label-sm text-label-sm font-semibold hover:bg-primary-container transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[16px]">fact_check</span>
            <span>Live Audit Stream</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
        <AdminKpiCard
          label="Total Checks (24h)"
          value={metrics.totalChecks24h.toLocaleString('en-IN')}
          change="+14.2%"
          changeType="positive"
          subtext="WhatsApp forwards comprise 72%"
          icon="mark_chat_read"
          iconColorClass="text-primary bg-primary-fixed"
        />

        <AdminKpiCard
          label="Avg Pipeline Latency"
          value={`${(metrics.avgLatencyMs / 1000).toFixed(2)}s`}
          change="-120ms"
          changeType="positive"
          subtext="eGazette vector index warm"
          icon="timer"
          iconColorClass="text-tertiary bg-emerald-100"
        />

        <AdminKpiCard
          label="Rumour Cache Hit Ratio"
          value={`${metrics.cacheHitRatio}%`}
          change="+3.4%"
          changeType="positive"
          subtext="3,912 duplicate forwards absorbed"
          icon="fingerprint"
          iconColorClass="text-secondary bg-orange-100"
        />

        <AdminKpiCard
          label="Deterministic Precision"
          value={`${metrics.accuracyRate}%`}
          change="0.0% FP"
          changeType="positive"
          subtext="Audited against IFCN Ground Truth"
          icon="verified"
          iconColorClass="text-emerald-800 bg-emerald-100"
        />
      </div>

      {/* Charts & Verdict Distribution Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg">
        {/* Ingestion Volume Area Chart */}
        <div className="lg:col-span-2 rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                Ingestion Volume & Real-Time Flow
              </h2>
              <p className="font-body-sm text-[12px] text-on-surface-variant">
                Hourly forward submissions across WhatsApp tipline and web portal.
              </p>
            </div>
            <span className="px-2 py-0.5 rounded bg-surface-container font-code-sm text-[11px] font-bold text-on-surface-variant">
              Last 24 Hours
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_HOURLY_VOLUME} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1D4ED8" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#1D4ED8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" stroke="#747686" fontSize={12} tickLine={false} />
                <YAxis stroke="#747686" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderColor: '#c4c5d7',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="volume"
                  stroke="#1D4ED8"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#volGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Verdict Distribution Breakdown */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
          <div>
            <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Verdict Distribution
            </h2>
            <p className="font-body-sm text-[12px] text-on-surface-variant">
              Breakdown across {metrics.totalChecks24h.toLocaleString()} verified statements.
            </p>
          </div>

          <div className="space-y-3 pt-1">
            {[
              { label: 'False Claims', count: metrics.checksPerVerdict.falseClaims, verdict: 'FALSE' as const, pct: 39.4 },
              { label: 'Verified True', count: metrics.checksPerVerdict.verified, verdict: 'VERIFIED' as const, pct: 29.2 },
              { label: 'Outdated Circulars', count: metrics.checksPerVerdict.outdated, verdict: 'OUTDATED' as const, pct: 15.9 },
              { label: 'Partly Supported', count: metrics.checksPerVerdict.partlySupported, verdict: 'PARTLY_SUPPORTED' as const, pct: 10.7 },
              { label: 'Cannot Confirm', count: metrics.checksPerVerdict.cannotConfirm, verdict: 'CANNOT_BE_CONFIRMED' as const, pct: 4.8 },
            ].map((item) => (
              <div key={item.label} className="space-y-1">
                <div className="flex items-center justify-between font-label-sm text-[12px]">
                  <span className="font-semibold text-on-surface">{item.label}</span>
                  <span className="font-code-sm text-on-surface-variant font-bold">
                    {item.count.toLocaleString()} ({item.pct}%)
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${item.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Checks Live Feed Table */}
      <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Recent Evidentiary Audits
            </h2>
            <p className="font-body-sm text-[12px] text-on-surface-variant">
              Real-time forward inspection queue processed by deterministic pipeline.
            </p>
          </div>
          <Link
            href="/admin/checks"
            className="font-label-sm text-label-sm text-primary font-bold hover:underline"
          >
            View All Live Checks →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-body-sm text-[13px]">
            <thead className="bg-surface-container-low text-on-surface-variant font-label-sm text-[11px] uppercase tracking-wider border-y border-outline-variant">
              <tr>
                <th className="py-2.5 px-3">Check ID</th>
                <th className="py-2.5 px-3">Input Type</th>
                <th className="py-2.5 px-3">Original Claim Snippet</th>
                <th className="py-2.5 px-3">Claims</th>
                <th className="py-2.5 px-3">Verdict</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60">
              {recentChecks.map((item) => (
                <tr key={item.id} className="hover:bg-surface-container-low/50">
                  <td className="py-3 px-3 font-code-sm font-bold text-primary">
                    #{item.id}
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded-full bg-surface-container font-code-sm text-[11px] text-on-surface-variant">
                      {item.inputType}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-serif italic max-w-xs truncate text-on-surface">
                    "{item.originalMessage.slice(0, 65)}..."
                  </td>
                  <td className="py-3 px-3 font-code-sm font-semibold">
                    {item.claims.length} claims
                  </td>
                  <td className="py-3 px-3">
                    <VerdictBadge verdict={item.overallVerdict} size="sm" />
                  </td>
                  <td className="py-3 px-3 text-right">
                    <Link
                      href={`/check/${item.id}`}
                      className="text-primary hover:underline font-semibold"
                    >
                      Inspect
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
