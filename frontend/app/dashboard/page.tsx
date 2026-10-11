'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { AppShell } from '@/components/layout/AppShell';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { EmptyState } from '@/components/states/EmptyState';
import { formatDate } from '@/lib/utils';
import {
  fetchUserAnalytics,
  fetchUserChecks,
  logoutUser,
  UserAnalyticsSummary,
} from '@/lib/api';
import { isAuthenticated, getUser, clearAuth, AuthUser } from '@/lib/auth';
import { Verdict } from '@/types';

const VERDICT_COLORS: Record<string, string> = {
  VERIFIED: '#10b981', // emerald-500
  FALSE: '#ef4444', // red-500
  OUTDATED: '#f59e0b', // amber-500
  PARTLY_SUPPORTED: '#f97316', // orange-500
  CANNOT_BE_CONFIRMED: '#6b7280', // gray-500
};

export default function UserDashboardPage() {
  const router = useRouter();

  const [user, setUserState] = useState<AuthUser | null>(null);
  const [analytics, setAnalytics] = useState<UserAnalyticsSummary | null>(null);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [totalHistory, setTotalHistory] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & filter in personal history
  const [search, setSearch] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('ALL');

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login');
      return;
    }

    const cachedUser = getUser();
    setUserState(cachedUser);

    loadDashboardData();
  }, [router]);

  async function loadDashboardData() {
    setLoading(true);
    setError(null);
    try {
      const [analyticsData, checksData] = await Promise.all([
        fetchUserAnalytics(),
        fetchUserChecks(50, 0),
      ]);
      setAnalytics(analyticsData);
      setHistoryItems(checksData.checks || []);
      setTotalHistory(checksData.total || 0);
    } catch (err: any) {
      console.error('Failed to load user dashboard:', err);
      setError(err.message || 'Failed to load your personal dashboard.');
    } finally {
      setLoading(false);
    }
  }

  const handleLogout = async () => {
    await logoutUser();
    clearAuth();
    router.replace('/login');
  };

  // Safe verdict counts with defaults to prevent runtime undefined errors
  const verdictCounts = analytics?.verdict_counts || {
    VERIFIED: 0,
    FALSE: 0,
    OUTDATED: 0,
    PARTLY_SUPPORTED: 0,
    CANNOT_BE_CONFIRMED: 0,
  };

  // Verdict distribution bar data
  const verdictDistributionData = [
    { name: 'VERIFIED', count: verdictCounts.VERIFIED ?? 0, color: VERDICT_COLORS.VERIFIED },
    { name: 'FALSE', count: verdictCounts.FALSE ?? 0, color: VERDICT_COLORS.FALSE },
    { name: 'OUTDATED', count: verdictCounts.OUTDATED ?? 0, color: VERDICT_COLORS.OUTDATED },
    { name: 'PARTLY', count: verdictCounts.PARTLY_SUPPORTED ?? 0, color: VERDICT_COLORS.PARTLY_SUPPORTED },
    { name: 'UNCONFIRMED', count: verdictCounts.CANNOT_BE_CONFIRMED ?? 0, color: VERDICT_COLORS.CANNOT_BE_CONFIRMED },
  ];

  // Activity timeline format
  const timelineData = (analytics?.activity_timeline || []).map((item) => ({
    date: item?.date ? item.date.slice(5) : '', // MM-DD
    fullDate: item?.date || '',
    count: item?.count ?? 0,
  }));

  // Filtered personal history items
  const filteredHistory = (historyItems || []).filter((item) => {
    const rawVerdict = (item?.verdict || 'CANNOT_BE_CONFIRMED').toUpperCase();
    const matchesFilter = verdictFilter === 'ALL' || rawVerdict === verdictFilter;
    const matchesSearch =
      search === '' ||
      (item?.text && item.text.toLowerCase().includes(search.toLowerCase())) ||
      (item?.check_id && item.check_id.toLowerCase().includes(search.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-xl">
        {/* Top Header & User Identity Banner */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl flex flex-col md:flex-row md:items-center justify-between gap-space-md shadow-xs">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <span className="material-symbols-outlined text-primary text-[28px]">
                account_circle
              </span>
              <h1 className="font-headline-lg text-2xl md:text-3xl font-extrabold text-on-surface">
                Personal Verification Dashboard
              </h1>
            </div>
            <p className="font-body-md text-on-surface-variant flex items-center gap-2 flex-wrap">
              <span>Account phone:</span>
              <span className="font-code-sm font-semibold text-on-surface bg-surface-container-low px-2 py-0.5 rounded border border-outline-variant">
                {user?.phone_number || 'Authenticated Citizen'}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-500/15 px-2 py-0.5 rounded-full border border-emerald-500/30">
                <span className="material-symbols-outlined text-[13px]">verified</span>
                Twilio WhatsApp OTP Verified
              </span>
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
            <Link
              href="/check"
              className="px-4 py-2 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-all shadow-2xs flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[18px]">add_circle</span>
              <span>Verify Claim</span>
            </Link>

            <Link
              href="/whatsapp"
              className="px-3.5 py-2 rounded-xl bg-surface-container-low hover:bg-surface-container border border-outline-variant text-on-surface font-label-md text-label-md font-semibold transition-colors flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[18px] text-emerald-600">chat</span>
              <span>WhatsApp Bot</span>
            </Link>

            <button
              onClick={handleLogout}
              className="px-3 py-2 rounded-xl border border-outline-variant hover:bg-error-container/20 text-on-surface-variant hover:text-error text-xs font-semibold transition-colors flex items-center gap-1"
              title="Sign Out"
            >
              <span className="material-symbols-outlined text-[16px]">logout</span>
              <span>Logout</span>
            </button>
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && (
          <div className="p-12 text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
            <span className="material-symbols-outlined animate-spin text-[36px] text-primary">
              progress_activity
            </span>
            <p className="font-body-md text-on-surface-variant">Loading your personal verification analytics...</p>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-2xl bg-error-container/20 border border-error/40 p-space-lg flex items-start gap-3">
            <span className="material-symbols-outlined text-error text-[24px] shrink-0 mt-0.5">
              error
            </span>
            <div className="space-y-1">
              <h3 className="font-headline-sm text-sm font-bold text-error">
                Failed to load personal analytics
              </h3>
              <p className="text-body-sm text-xs text-error/90">{error}</p>
              <button
                onClick={loadDashboardData}
                className="mt-2 text-xs font-bold text-error underline"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Dashboard Content */}
        {!loading && !error && analytics && (
          <>
            {/* Overview KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-space-sm md:gap-space-md">
              {/* Total Verified */}
              <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-4 space-y-1 shadow-2xs">
                <div className="flex items-center justify-between text-on-surface-variant">
                  <span className="text-[12px] font-medium">Total Claims</span>
                  <span className="material-symbols-outlined text-[18px] text-primary">analytics</span>
                </div>
                <div className="font-headline-lg text-2xl font-black text-on-surface">
                  {analytics?.total_checks ?? 0}
                </div>
                <div className="text-[11px] text-on-surface-variant">Processed for you</div>
              </div>

              {/* Verified */}
              <div className="rounded-2xl bg-emerald-500/5 border border-emerald-500/20 p-4 space-y-1 shadow-2xs">
                <div className="flex items-center justify-between text-emerald-700 dark:text-emerald-400">
                  <span className="text-[12px] font-semibold">VERIFIED</span>
                  <span className="material-symbols-outlined text-[18px]">verified</span>
                </div>
                <div className="font-headline-lg text-2xl font-black text-emerald-700 dark:text-emerald-300">
                  {verdictCounts.VERIFIED ?? 0}
                </div>
                <div className="text-[11px] text-emerald-800/80 dark:text-emerald-400/80">Statutorily accurate</div>
              </div>

              {/* False */}
              <div className="rounded-2xl bg-rose-500/5 border border-rose-500/20 p-4 space-y-1 shadow-2xs">
                <div className="flex items-center justify-between text-rose-700 dark:text-rose-400">
                  <span className="text-[12px] font-semibold">FALSE</span>
                  <span className="material-symbols-outlined text-[18px]">cancel</span>
                </div>
                <div className="font-headline-lg text-2xl font-black text-rose-700 dark:text-rose-300">
                  {verdictCounts.FALSE ?? 0}
                </div>
                <div className="text-[11px] text-rose-800/80 dark:text-rose-400/80">Refuted by facts</div>
              </div>

              {/* Outdated */}
              <div className="rounded-2xl bg-amber-500/5 border border-amber-500/20 p-4 space-y-1 shadow-2xs">
                <div className="flex items-center justify-between text-amber-700 dark:text-amber-400">
                  <span className="text-[12px] font-semibold">OUTDATED</span>
                  <span className="material-symbols-outlined text-[18px]">history</span>
                </div>
                <div className="font-headline-lg text-2xl font-black text-amber-700 dark:text-amber-300">
                  {verdictCounts.OUTDATED ?? 0}
                </div>
                <div className="text-[11px] text-amber-800/80 dark:text-amber-400/80">Expired context</div>
              </div>

              {/* Partly Supported */}
              <div className="rounded-2xl bg-orange-500/5 border border-orange-500/20 p-4 space-y-1 shadow-2xs">
                <div className="flex items-center justify-between text-orange-700 dark:text-orange-400">
                  <span className="text-[12px] font-semibold">PARTLY</span>
                  <span className="material-symbols-outlined text-[18px]">adjust</span>
                </div>
                <div className="font-headline-lg text-2xl font-black text-orange-700 dark:text-orange-300">
                  {verdictCounts.PARTLY_SUPPORTED ?? 0}
                </div>
                <div className="text-[11px] text-orange-800/80 dark:text-orange-400/80">Mixed evidence</div>
              </div>

              {/* Unconfirmed */}
              <div className="rounded-2xl bg-slate-500/5 border border-slate-500/20 p-4 space-y-1 shadow-2xs">
                <div className="flex items-center justify-between text-slate-700 dark:text-slate-400">
                  <span className="text-[12px] font-semibold">UNCONFIRMED</span>
                  <span className="material-symbols-outlined text-[18px]">help</span>
                </div>
                <div className="font-headline-lg text-2xl font-black text-slate-700 dark:text-slate-300">
                  {verdictCounts.CANNOT_BE_CONFIRMED ?? 0}
                </div>
                <div className="text-[11px] text-slate-700/80 dark:text-slate-400/80">Insufficient proof</div>
              </div>
            </div>

            {/* Zero State for New Users */}
            {(analytics?.total_checks ?? 0) === 0 ? (
              <EmptyState
                icon="fact_check"
                title="No checks performed yet"
                description="Submit your first suspicious WhatsApp forward, viral screenshot, or claim text to see personal evidentiary analytics."
                actionHref="/check"
                actionText="Verify Your First Forward"
                className="my-space-md"
              />
            ) : (
              <>
                {/* Visual Charts: Activity Timeline & Verdict Breakdown */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-md">
                  {/* Activity Over Time */}
                  <div className="lg:col-span-2 rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <h2 className="font-headline-sm text-base font-bold text-on-surface">
                          Verification Activity Over Time
                        </h2>
                        <p className="text-[12px] text-on-surface-variant">
                          Real-time checks recorded for your account
                        </p>
                      </div>
                      <span className="text-xs font-semibold bg-surface-container-low px-2 py-1 rounded text-on-surface-variant border border-outline-variant">
                        Last 7 Days
                      </span>
                    </div>

                    <div className="h-56 w-full pt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={timelineData}>
                          <defs>
                            <linearGradient id="userActivityGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                            </linearGradient>
                          </defs>
                          <XAxis
                            dataKey="date"
                            tick={{ fill: '#888', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                          />
                          <YAxis
                            allowDecimals={false}
                            tick={{ fill: '#888', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            width={24}
                          />
                          <Tooltip
                            contentStyle={{
                              borderRadius: '8px',
                              border: '1px solid #e5e7eb',
                              boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                              fontSize: '12px',
                            }}
                          />
                          <Area
                            type="monotone"
                            dataKey="count"
                            stroke="#2563eb"
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill="url(#userActivityGrad)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Verdict Distribution */}
                  <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
                    <div className="space-y-0.5">
                      <h2 className="font-headline-sm text-base font-bold text-on-surface">
                        Verdict Breakdown
                      </h2>
                      <p className="text-[12px] text-on-surface-variant">
                        Categorical distribution of your submissions
                      </p>
                    </div>

                    <div className="h-56 w-full pt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={verdictDistributionData} layout="vertical">
                          <XAxis type="number" hide />
                          <YAxis
                            dataKey="name"
                            type="category"
                            tick={{ fill: '#666', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            width={90}
                          />
                          <Tooltip
                            contentStyle={{
                              borderRadius: '8px',
                              border: '1px solid #e5e7eb',
                              fontSize: '12px',
                            }}
                          />
                          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                            {verdictDistributionData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Personal History Table / List */}
                <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-outline-variant">
                    <div>
                      <h2 className="font-headline-sm text-lg font-bold text-on-surface">
                        Your Verification Records
                      </h2>
                      <p className="text-xs text-on-surface-variant">
                        Showing {filteredHistory.length} of {totalHistory} verified checks
                      </p>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                      <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search claims or IDs..."
                        className="px-3 py-1.5 rounded-lg border border-outline-variant bg-surface-container-low text-xs text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
                      />
                      <select
                        value={verdictFilter}
                        onChange={(e) => setVerdictFilter(e.target.value)}
                        className="px-2.5 py-1.5 rounded-lg border border-outline-variant bg-surface-container-low text-xs text-on-surface focus:outline-none focus:border-primary cursor-pointer"
                      >
                        <option value="ALL">All Verdicts</option>
                        <option value="VERIFIED">Verified</option>
                        <option value="FALSE">False</option>
                        <option value="OUTDATED">Outdated</option>
                        <option value="PARTLY_SUPPORTED">Partly Supported</option>
                        <option value="CANNOT_BE_CONFIRMED">Cannot Confirm</option>
                      </select>
                    </div>
                  </div>

                  {filteredHistory.length === 0 ? (
                    <div className="py-8 text-center text-on-surface-variant text-xs">
                      No matching records found for this search or filter.
                    </div>
                  ) : (
                    <div className="divide-y divide-outline-variant/60">
                      {filteredHistory.map((item) => {
                        const rawVerdict = (item.verdict || 'CANNOT_BE_CONFIRMED').toUpperCase() as Verdict;
                        return (
                          <div
                            key={item.check_id}
                            className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-container-low/50 px-2 rounded-xl transition-colors"
                          >
                            <div className="space-y-1 max-w-xl">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-code-sm text-[11px] text-on-surface-variant bg-surface-container-low px-1.5 py-0.5 rounded border border-outline-variant">
                                  {item.check_id}
                                </span>
                                <span className="text-[11px] font-semibold text-primary uppercase bg-primary/10 px-1.5 py-0.5 rounded">
                                  {item.input_type || 'TEXT'}
                                </span>
                                <span className="text-[11px] text-outline">
                                  {item.created_at ? formatDate(item.created_at) : 'Recent'}
                                </span>
                              </div>
                              <p className="font-body-sm text-sm text-on-surface font-medium line-clamp-2">
                                {item.text || 'Claim statement'}
                              </p>
                            </div>

                            <div className="flex items-center gap-3 shrink-0">
                              <VerdictBadge verdict={rawVerdict} size="sm" />
                              <Link
                                href={`/check/${item.check_id}`}
                                className="px-3 py-1.5 rounded-lg border border-outline-variant bg-surface-container-low hover:bg-primary hover:text-on-primary text-xs font-bold transition-colors flex items-center gap-1"
                              >
                                <span>Evidence Card</span>
                                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                              </Link>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
