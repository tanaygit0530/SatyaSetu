import React from 'react';

interface AdminKpiCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  subtext?: string;
  icon: string;
  iconColorClass?: string;
}

export function AdminKpiCard({
  label,
  value,
  change,
  changeType = 'neutral',
  subtext,
  icon,
  iconColorClass = 'text-primary bg-primary-fixed',
}: AdminKpiCardProps) {
  const changeColors = {
    positive: 'text-tertiary bg-emerald-50',
    negative: 'text-error bg-red-50',
    neutral: 'text-on-surface-variant bg-surface-container',
  };

  return (
    <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant shadow-2xs space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-label-sm text-[12px] uppercase tracking-wider text-on-surface-variant font-bold">
          {label}
        </span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconColorClass}`}>
          <span className="material-symbols-outlined text-[18px]">{icon}</span>
        </div>
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <div className="font-headline-lg text-headline-lg font-bold text-on-surface">
          {value}
        </div>
        {change && (
          <span className={`px-2 py-0.5 rounded-full font-code-sm text-[11px] font-bold ${changeColors[changeType]}`}>
            {change}
          </span>
        )}
      </div>

      {subtext && (
        <p className="font-body-sm text-[12px] text-on-surface-variant pt-1 border-t border-outline-variant/40">
          {subtext}
        </p>
      )}
    </div>
  );
}
