import React from 'react';
import { Verdict } from '@/types';
import { getVerdictConfig } from '@/lib/utils';

interface VerdictBadgeProps {
  verdict: Verdict;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export function VerdictBadge({
  verdict,
  size = 'md',
  showIcon = true,
  className = '',
}: VerdictBadgeProps) {
  const config = getVerdictConfig(verdict);

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px] gap-1',
    md: 'px-2.5 py-1 text-label-sm gap-1.5',
    lg: 'px-3.5 py-1.5 text-label-md gap-2 font-bold',
  };

  const iconSizes = {
    sm: 'text-[14px]',
    md: 'text-[16px]',
    lg: 'text-[18px]',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border font-semibold tracking-wide ${config.badgeClass} ${sizeClasses[size]} ${className}`}
    >
      {showIcon && (
        <span className={`material-symbols-outlined ${iconSizes[size]}`}>
          {config.icon}
        </span>
      )}
      <span>{config.label}</span>
    </span>
  );
}
