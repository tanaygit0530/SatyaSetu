'use client';

import React, { useState, useEffect } from 'react';
import { FontScale } from '@/types';

interface FontScalerProps {
  className?: string;
}

export function FontScaler({ className = '' }: FontScalerProps) {
  const [scale, setScale] = useState<FontScale>('standard');

  useEffect(() => {
    const saved = localStorage.getItem('sachcheck_font_scale') as FontScale;
    if (saved && ['standard', 'medium', 'large'].includes(saved)) {
      setScale(saved);
      document.documentElement.setAttribute('data-font-scale', saved);
    }
  }, []);

  const changeScale = (newScale: FontScale) => {
    setScale(newScale);
    localStorage.setItem('sachcheck_font_scale', newScale);
    document.documentElement.setAttribute('data-font-scale', newScale);
  };

  return (
    <div
      aria-label="Civic Font Scaler Widget"
      className={`inline-flex items-center bg-surface-container-low rounded-lg p-0.5 border border-outline-variant ${className}`}
    >
      <button
        type="button"
        onClick={() => changeScale('standard')}
        title="Standard Font Size (100%)"
        className={`px-2 py-1 rounded text-label-sm font-semibold transition-all ${
          scale === 'standard'
            ? 'bg-surface-container-lowest text-on-surface shadow-xs font-bold'
            : 'text-on-surface-variant hover:text-on-surface'
        }`}
      >
        A
      </button>
      <span className="text-outline text-label-sm px-1">|</span>
      <button
        type="button"
        onClick={() => changeScale('medium')}
        title="Medium Font Size (112.5%)"
        className={`px-2 py-1 rounded text-label-sm font-semibold transition-all ${
          scale === 'medium'
            ? 'bg-surface-container-lowest text-on-surface shadow-xs font-bold'
            : 'text-on-surface-variant hover:text-on-surface'
        }`}
      >
        A+
      </button>
      <span className="text-outline text-label-sm px-1">|</span>
      <button
        type="button"
        onClick={() => changeScale('large')}
        title="Large Font Size (125%)"
        className={`px-2 py-1 rounded text-label-sm font-semibold transition-all ${
          scale === 'large'
            ? 'bg-surface-container-lowest text-on-surface shadow-xs font-bold'
            : 'text-on-surface-variant hover:text-on-surface'
        }`}
      >
        A++
      </button>
    </div>
  );
}
