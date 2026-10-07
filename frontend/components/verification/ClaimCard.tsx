import React from 'react';
import Link from 'next/link';
import { Claim } from '@/types';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { ConfidenceBand } from '@/components/verdict/ConfidenceBand';
import { EvidenceCard } from '@/components/evidence/EvidenceCard';

interface ClaimCardProps {
  claim: Claim;
  checkId: string;
  isDetailedView?: boolean;
}

export function ClaimCard({ claim, checkId, isDetailedView = false }: ClaimCardProps) {
  return (
    <article className="rounded-xl bg-surface-container-lowest border border-outline-variant p-space-md md:p-space-lg shadow-2xs space-y-space-md">
      {/* Header: Claim Number & Verdict Badge */}
      <div className="flex flex-wrap items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
        <div className="flex items-center gap-space-sm">
          <span className="w-7 h-7 rounded-full bg-surface-container-high flex items-center justify-center font-code-sm text-code-sm font-bold text-on-surface">
            #{claim.claimNumber}
          </span>
          <span className="font-label-md text-label-md text-on-surface-variant font-medium">
            Extracted Atomic Claim
          </span>
          {claim.temporalStatus === 'OUTDATED_2022' && (
            <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-code-sm text-[11px] font-bold">
              Temporal Mismatch (2020 Order)
            </span>
          )}
        </div>

        <div className="flex items-center gap-space-sm">
          <VerdictBadge verdict={claim.verdict} size="md" />
        </div>
      </div>

      {/* Claim Extraction Quote Block in Source Serif 4 */}
      <div className="rounded-lg p-space-md bg-surface-container-low border-l-4 border-l-outline border border-outline-variant">
        <p className="font-serif italic text-on-surface text-[16px] md:text-[17px] leading-relaxed">
          "{claim.claimText}"
        </p>
        {claim.originalLanguageText && (
          <p className="mt-2 font-devanagari text-on-surface-variant text-[14px]">
            मूल भाषा: "{claim.originalLanguageText}"
          </p>
        )}
      </div>

      {/* Verification Summary & Analysis */}
      <div className="space-y-2">
        <h4 className="font-label-md text-label-md font-bold text-on-surface">
          Why this verdict:
        </h4>
        <p className="font-body-md text-body-md text-on-surface">
          {claim.summary}
        </p>
        <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
          {claim.detailedAnalysis}
        </p>
      </div>

      {/* Counter Evidence Flag if False / Outdated */}
      {claim.counterEvidenceSummary && (
        <div className="rounded-lg p-space-sm bg-error-container/20 border border-error/30 flex items-start gap-2">
          <span className="material-symbols-outlined text-[18px] text-error shrink-0 mt-0.5">
            warning
          </span>
          <p className="font-body-sm text-body-sm text-error font-medium">
            {claim.counterEvidenceSummary}
          </p>
        </div>
      )}

      {/* Citations Preview */}
      {claim.sourceCitations.length > 0 && (
        <div className="space-y-space-sm pt-space-xs">
          <div className="flex items-center justify-between">
            <span className="font-label-sm text-label-sm text-on-surface-variant font-bold uppercase tracking-wider">
              Corroborating Sources ({claim.sourceCitations.length})
            </span>
            {claim.ruleMatched && (
              <span className="font-code-sm text-[11px] text-outline">
                Engine: {claim.ruleMatched}
              </span>
            )}
          </div>

          <div className="space-y-2">
            {claim.sourceCitations.slice(0, isDetailedView ? undefined : 1).map((citation) => (
              <EvidenceCard key={citation.id} citation={citation} />
            ))}
          </div>
        </div>
      )}

      {/* Footer Actions: Confidence & Link to Evidence Dossier */}
      <div className="pt-space-sm border-t border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm">
        <div className="w-full sm:w-48">
          <ConfidenceBand confidence={claim.confidence} verdict={claim.verdict} />
        </div>

        {!isDetailedView && (
          <Link
            href={`/check/${checkId}/evidence/${claim.id}`}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline-variant text-primary hover:bg-surface-container-low font-label-md text-label-md font-semibold transition-colors self-start sm:self-auto"
          >
            <span>Inspect Forensic Dossier</span>
            <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
          </Link>
        )}
      </div>
    </article>
  );
}
