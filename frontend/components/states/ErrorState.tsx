import React from 'react';
import Link from 'next/link';

interface ErrorStateProps {
  code?: string;
  title?: string;
  description?: string;
  retryAction?: () => void;
  className?: string;
}

export function ErrorState({
  code = '500',
  title = 'Something went wrong.',
  description = 'Our deterministic verification pipelines encountered an unexpected fault. We are logging the trace.',
  retryAction,
  className = '',
}: ErrorStateProps) {
  return (
    <div
      className={`rounded-2xl border border-outline-variant bg-surface-container-lowest p-space-2xl text-center max-w-lg mx-auto space-y-space-md ${className}`}
    >
      <div className="w-16 h-16 rounded-full bg-error-container/40 text-error flex items-center justify-center mx-auto border border-error/20">
        <span className="material-symbols-outlined text-[32px]">error</span>
      </div>

      <div className="space-y-1.5">
        <span className="font-code-sm text-code-sm text-error font-bold uppercase tracking-wider">
          Fault Code: {code}
        </span>
        <h3 className="font-headline-sm text-headline-sm text-on-surface font-bold">
          {title}
        </h3>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-md mx-auto">
          {description}
        </p>
      </div>

      <div className="pt-2 flex flex-wrap justify-center gap-3">
        {retryAction ? (
          <button
            type="button"
            onClick={retryAction}
            className="px-5 py-2.5 rounded-xl bg-primary text-on-primary font-label-md text-label-md font-bold hover:bg-primary-container"
          >
            Retry Verification
          </button>
        ) : (
          <Link
            href="/check"
            className="px-5 py-2.5 rounded-xl bg-primary text-on-primary font-label-md text-label-md font-bold hover:bg-primary-container"
          >
            Return to Check
          </Link>
        )}
        <Link
          href="/"
          className="px-4 py-2.5 rounded-xl border border-outline-variant text-on-surface font-label-md text-label-md hover:bg-surface-container-low"
        >
          Go to Home
        </Link>
      </div>
    </div>
  );
}
