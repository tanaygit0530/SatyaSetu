'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { formatDate } from '@/lib/utils';
import { listChecks, adaptCheckToUi } from '@/lib/api';
import { VerificationResult } from '@/types';

export default function AdminRumourMemoryPage() {
  const [cachedChecks, setCachedChecks] = useState<VerificationResult[]>([]);
  const [selectedCheck, setSelectedCheck] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadRumourMemory() {
      try {
        setLoading(true);
        const raw = await listChecks(50);
        if (!isMounted) return;

        const adapted = raw.map(adaptCheckToUi);
        setCachedChecks(adapted);
        if (adapted.length > 0) {
          setSelectedCheck(adapted[0]);
        }
      } catch (err) {
        console.error('Failed to load rumour memory checks:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadRumourMemory();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-space-lg">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-[20px]">fingerprint</span>
            <span className="font-code-sm text-[12px] text-secondary font-bold uppercase tracking-wider">
              L1/L2 VECTOR MEMORY
            </span>
          </div>
          <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
            Rumour Memory & Shared Claim Cache
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Identical and semantically similar forwards cached in shared memory. Ingests once, responds in milliseconds to duplicate forwards.
          </p>
        </div>
      </div>

      {loading && (
        <div className="p-space-xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="font-body-sm text-on-surface-variant">Loading rumour memory cache records...</p>
        </div>
      )}

      {!loading && cachedChecks.length === 0 ? (
        <div className="p-space-2xl text-center rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-3">
          <span className="material-symbols-outlined text-[36px] text-outline">memory</span>
          <h3 className="font-headline-sm text-lg font-bold text-on-surface">No Rumour Memory Records Cached Yet</h3>
          <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
            As claims are verified and stored into Shared Claim Memory, their semantic embeddings and cached entries will appear here.
          </p>
          <div className="pt-2">
            <Link href="/check" className="px-4 py-2 rounded-xl bg-primary text-on-primary font-label-md font-bold">
              Verify a Claim to Populate Cache
            </Link>
          </div>
        </div>
      ) : (
        !loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            {cachedChecks.map((chk) => {
              const isSelected = chk.id === selectedCheck?.id;
              return (
                <div
                  key={chk.id}
                  onClick={() => setSelectedCheck(chk)}
                  className={`p-space-lg rounded-2xl border transition-all cursor-pointer space-y-3 ${
                    isSelected
                      ? 'bg-surface-container-lowest border-primary shadow-sm ring-1 ring-primary/30'
                      : 'bg-surface-container-lowest border-outline-variant hover:border-primary/50'
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-code-sm text-[11px] font-bold text-primary bg-primary-fixed/40 px-2 py-0.5 rounded">
                        #{chk.id}
                      </span>
                      {chk.cacheHit && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[11px] font-bold">
                          ✓ Memory Hit
                        </span>
                      )}
                    </div>
                    <VerdictBadge verdict={chk.overallVerdict} size="sm" />
                  </div>

                  <blockquote className="font-serif italic text-[15px] text-on-surface leading-snug line-clamp-2">
                    "{chk.originalMessage}"
                  </blockquote>

                  <p className="font-body-sm text-[12px] text-on-surface-variant line-clamp-2">
                    {chk.verdictSummary}
                  </p>

                  <div className="pt-2 border-t border-outline-variant/60 flex items-center justify-between font-code-sm text-[11px] text-outline">
                    <span>Verified: {formatDate(chk.submittedAt)}</span>
                    <Link
                      href={`/check/${encodeURIComponent(chk.id)}`}
                      className="text-primary hover:underline font-bold"
                    >
                      Inspect Dossier →
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}
