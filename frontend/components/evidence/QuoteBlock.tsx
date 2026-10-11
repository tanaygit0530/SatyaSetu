import React from 'react';

interface QuoteBlockProps {
  quote?: string;
  text?: string;
  sourceTitle?: string;
  sourcePublisher?: string;
  source?: string;
  sourceDate?: string;
  variant?: 'forwarded' | 'source';
  highlightType?: string;
  className?: string;
}

export function QuoteBlock({
  quote,
  text,
  sourceTitle,
  sourcePublisher,
  source,
  sourceDate,
  variant = 'source',
  className = '',
}: QuoteBlockProps) {
  const displayQuote = quote || text || '';
  const displayPublisher = sourcePublisher || source;
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
            "{displayQuote}"
          </blockquote>
          {(displayPublisher || sourceTitle) && (
            <div className="flex flex-wrap items-center gap-2 pt-1 font-label-sm text-[12px] text-on-surface-variant">
              {displayPublisher && (
                <span className="font-bold text-on-surface">{displayPublisher}</span>
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
