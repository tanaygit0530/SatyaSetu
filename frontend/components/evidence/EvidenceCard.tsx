import React from 'react';
import { SourceCitation } from '@/types';
import { SourceTierBadge } from './SourceTierBadge';
import { QuoteBlock } from './QuoteBlock';

interface EvidenceCardProps {
  citation: SourceCitation;
  className?: string;
}

export function EvidenceCard({ citation, className = '' }: EvidenceCardProps) {
  return (
    <div
      className={`rounded-xl bg-surface-container-lowest border border-outline-variant p-space-md shadow-2xs hover:border-primary/40 transition-colors ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-space-sm">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-surface-container-low flex items-center justify-center text-primary font-bold">
            <span className="material-symbols-outlined text-[16px]">verified</span>
          </div>
          <div>
            <h4 className="font-label-md text-label-md font-bold text-on-surface">
              {citation.publisher}
            </h4>
            <span className="font-code-sm text-[11px] text-on-surface-variant">
              {citation.domain}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <SourceTierBadge tier={citation.tier} />
          <span className="font-code-sm text-[11px] text-outline">
            {citation.date}
          </span>
        </div>
      </div>

      <div className="space-y-space-sm">
        <p className="font-body-sm text-body-sm text-on-surface font-semibold">
          {citation.title}
        </p>

        <QuoteBlock
          quote={citation.exactQuote}
          sourcePublisher={citation.publisher}
          sourceDate={citation.date}
        />

        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-outline-variant/60 font-code-sm text-[11px]">
          <div className="flex items-center gap-1.5 text-tertiary font-medium">
            <span className="material-symbols-outlined text-[14px]">lock</span>
            <span>Archive Corroborated</span>
          </div>

          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
          >
            <span>Inspect Statutory Source</span>
            <span className="material-symbols-outlined text-[14px]">open_in_new</span>
          </a>
        </div>
      </div>
    </div>
  );
}
