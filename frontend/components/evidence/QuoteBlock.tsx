import React from 'react';

interface QuoteBlockProps {
  quote: string;
  sourceTitle?: string;
  sourcePublisher?: string;
  sourceDate?: string;
  variant?: 'forwarded' | 'source';
  className?: string;
}

export function QuoteBlock({
  quote,
  sourceTitle,
  sourcePublisher,
  sourceDate,
  variant = 'source',
  className = '',
}: QuoteBlockProps) {
  return (
    <div
      className={`rounded-lg p-space-md bg-surface-container-low border-l-4 border-l-primary/40 border border-outline-variant/60 ${className}`}
    >
      <div className="flex items-start gap-2">
        <span className="material-symbols-outlined text-[18px] text-primary shrink-0 mt-0.5 select-none">
          format_quote
        </span>
        <div className="flex-1 space-y-1.5">
          <blockquote className="font-serif italic text-on-surface text-[15px] sm:text-[16px] leading-relaxed">
            "{quote}"
          </blockquote>
          {(sourcePublisher || sourceTitle) && (
            <div className="flex flex-wrap items-center gap-2 pt-1 font-label-sm text-[12px] text-on-surface-variant">
              {sourcePublisher && (
                <span className="font-bold text-on-surface">{sourcePublisher}</span>
              )}
              {sourceTitle && <span>• {sourceTitle}</span>}
              {sourceDate && (
                <span className="font-code-sm text-[11px] text-outline">
                  ({sourceDate})
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
