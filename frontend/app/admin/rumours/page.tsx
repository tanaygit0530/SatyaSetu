'use client';

import React, { useState } from 'react';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { MOCK_RUMOUR_CLUSTERS } from '@/lib/mock/admin';
import { formatDate } from '@/lib/utils';

export default function AdminRumourMemoryPage() {
  const [clusters, setClusters] = useState(MOCK_RUMOUR_CLUSTERS);
  const [selectedCluster, setSelectedCluster] = useState(clusters[0]);

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
            Rumour Memory & Deterministic Cache
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Clusters of identical or semantically similar forwards. Ingests once, replies instantly to 100,000s of subsequent forwards.
          </p>
        </div>
      </div>

      {/* Cluster Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
        {clusters.map((cluster) => {
          const isSelected = cluster.id === selectedCluster.id;
          return (
            <div
              key={cluster.id}
              onClick={() => setSelectedCluster(cluster)}
              className={`p-space-lg rounded-2xl border transition-all cursor-pointer space-y-3 ${
                isSelected
                  ? 'bg-surface-container-lowest border-primary shadow-sm ring-1 ring-primary/30'
                  : 'bg-surface-container-lowest border-outline-variant hover:border-primary/50'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-code-sm text-[11px] font-bold text-primary bg-primary-fixed/40 px-2 py-0.5 rounded">
                    {cluster.clusterId}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-surface-container font-code-sm text-[11px] text-on-surface-variant">
                    Threshold: {cluster.similarityThreshold}
                  </span>
                </div>
                <VerdictBadge verdict={cluster.verdict} size="sm" />
              </div>

              <blockquote className="font-serif italic text-[15px] text-on-surface leading-snug">
                "{cluster.canonicalClaim}"
              </blockquote>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2 border-t border-outline-variant/60 font-code-sm text-[12px]">
                <div>
                  <span className="text-outline">TOTAL VIRAL HITS:</span>
                  <p className="font-bold text-on-surface">{cluster.totalOccurrences.toLocaleString()}</p>
                </div>
                <div>
                  <span className="text-outline">CACHE REPLAYS:</span>
                  <p className="font-bold text-tertiary">{cluster.cachedHits.toLocaleString()}</p>
                </div>
                <div>
                  <span className="text-outline">LANGUAGES:</span>
                  <p className="font-bold text-primary uppercase">{cluster.languages.join(', ')}</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1 font-body-sm text-[11px] text-on-surface-variant">
                <span>First Seen: {formatDate(cluster.firstSeen)}</span>
                <span>Vector: Cosine Index Warm</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Cluster Deep Inspector Panel */}
      <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-outline-variant">
          <div>
            <span className="font-code-sm text-[11px] text-outline font-bold">ACTIVE CLUSTER INSPECTION</span>
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              {selectedCluster.clusterId} ({selectedCluster.canonicalClaim.slice(0, 48)}...)
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => alert(`Cluster ${selectedCluster.clusterId} re-indexed successfully.`)}
              className="px-3 py-1.5 rounded-lg border border-outline-variant bg-surface-container-low text-on-surface font-label-sm text-label-sm hover:bg-surface-container"
            >
              Force Vector Re-index
            </button>
            <button
              type="button"
              onClick={() => alert(`Dispatched updated debunk card to WhatsApp Broadcast.`)}
              className="px-3 py-1.5 rounded-lg bg-primary text-on-primary font-label-sm text-label-sm font-bold hover:bg-primary-container"
            >
              Push Debunk to Broadcast
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md font-body-sm text-body-sm">
          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-1">
            <span className="font-label-sm font-bold text-on-surface">Top Vector Variant</span>
            <p className="font-serif italic text-[13px] text-on-surface-variant">
              "Ministry giving scholarship ₹50,000 cash lump sum without exam."
            </p>
          </div>
          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-1">
            <span className="font-label-sm font-bold text-on-surface">Vernacular Variation (Hindi)</span>
            <p className="font-devanagari text-[13px] text-on-surface-variant">
              "छात्रवृत्ति राशि ₹50,000 सभी छात्रों के बैंक में ट्रांसफर।"
            </p>
          </div>
          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-1">
            <span className="font-label-sm font-bold text-on-surface">Vernacular Variation (Marathi)</span>
            <p className="font-devanagari text-[13px] text-on-surface-variant">
              "सर्व विद्यार्थ्यांसाठी ₹50,000 शिष्यवृत्ती अनुदान मंजूर."
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
