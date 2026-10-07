import React from 'react';
import { Verdict } from '@/types';
import { getVerdictConfig } from '@/lib/utils';

interface ConfidenceBandProps {
  confidence: number; // 0 to 100
  verdict?: Verdict;
  showLabel?: boolean;
  className?: string;
}

export function ConfidenceBand({
  confidence,
  verdict = 'VERIFIED',
  showLabel = true,
  className = '',
}: ConfidenceBandProps) {
  const config = getVerdictConfig(verdict);

  return (
    <div className={`space-y-1 ${className}`}>
      {showLabel && (
        <div className="flex items-center justify-between font-code-sm text-[11px] text-on-surface-variant">
          <span>Algorithmic Confidence</span>
          <span className="font-bold text-on-surface">{confidence.toFixed(1)}%</span>
        </div>
      )}
      <div className="h-1.5 w-full rounded-full bg-surface-container-high overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${config.dotColor}`}
          style={{ width: `${Math.min(Math.max(confidence, 5), 100)}%` }}
        />
      </div>
    </div>
  );
}
