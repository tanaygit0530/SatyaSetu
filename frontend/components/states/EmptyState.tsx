import React from 'react';
import Link from 'next/link';

interface EmptyStateProps {
  icon?: string;
  title?: string;
  description?: string;
  actionHref?: string;
  actionText?: string;
  className?: string;
}

export function EmptyState({
  icon = 'inbox',
  title = "You haven't checked anything yet.",
  description = 'Forward a message, upload a screenshot, or submit a link to begin evidentiary verification.',
  actionHref = '/check',
  actionText = 'Check a Forward Now',
  className = '',
}: EmptyStateProps) {
  return (
    <div
      className={`rounded-2xl border border-outline-variant bg-surface-container-lowest p-space-2xl text-center max-w-lg mx-auto space-y-space-md ${className}`}
    >
      <div className="w-16 h-16 rounded-full bg-surface-container-low text-primary flex items-center justify-center mx-auto border border-outline-variant">
        <span className="material-symbols-outlined text-[32px]">{icon}</span>
      </div>

      <div className="space-y-1.5">
        <h3 className="font-headline-sm text-headline-sm text-on-surface font-bold">
          {title}
        </h3>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-md mx-auto">
          {description}
        </p>
      </div>

      {actionHref && (
        <div className="pt-2">
          <Link
            href={actionHref}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-colors shadow-2xs"
          >
            <span className="material-symbols-outlined text-[18px]">verified_user</span>
            <span>{actionText}</span>
          </Link>
        </div>
      )}
    </div>
  );
}
