import React from 'react';
import { SourceTier } from '@/types';

interface SourceTierBadgeProps {
  tier: SourceTier;
  className?: string;
}

export function SourceTierBadge({ tier, className = '' }: SourceTierBadgeProps) {
  switch (tier) {
    case 'TIER_1_PRIMARY':
      return (
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary-fixed text-on-primary-fixed-variant font-code-sm text-[11px] font-bold border border-primary/20 ${className}`}
          title="Primary Statutory Record: Official Gazette, NIC Portal, Ministry Circular"
        >
          <span className="material-symbols-outlined text-[13px] text-primary">
            account_balance
          </span>
          <span>Tier-1 Primary Statutory</span>
        </span>
      );
    case 'TIER_2_SECONDARY':
      return (
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface font-code-sm text-[11px] font-bold border border-outline-variant ${className}`}
          title="Secondary Official Authority: Statutory Bodies, Apex Regulators"
        >
          <span className="material-symbols-outlined text-[13px]">policy</span>
          <span>Tier-2 Regulatory</span>
        </span>
      );
    case 'TIER_3_REPUTABLE':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-container-low text-on-surface-variant font-code-sm text-[11px] font-semibold border border-outline-variant ${className}`}
          title="Reputable Third-Party: IFCN Signatories, National Press Repositories"
        >
          <span className="material-symbols-outlined text-[13px]">verified</span>
          <span>Tier-3 IFCN Audited</span>
        </span>
      );
  }
}
