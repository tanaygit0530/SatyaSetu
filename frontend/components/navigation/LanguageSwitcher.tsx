'use client';

import React, { useState, useEffect } from 'react';
import { Language } from '@/types';

interface LanguageSwitcherProps {
  className?: string;
}

export function LanguageSwitcher({ className = '' }: LanguageSwitcherProps) {
  const [lang, setLang] = useState<Language>('en');

  useEffect(() => {
    const saved = localStorage.getItem('sachcheck_lang') as Language;
    if (saved && ['en', 'hi', 'mr'].includes(saved)) {
      setLang(saved);
      document.documentElement.lang = saved;
    }
  }, []);

  const changeLang = (newLang: Language) => {
    setLang(newLang);
    localStorage.setItem('sachcheck_lang', newLang);
    document.documentElement.lang = newLang;
    window.dispatchEvent(new CustomEvent('language_change', { detail: newLang }));
  };

  return (
    <div
      aria-label="Language Selector"
      className={`inline-flex items-center bg-surface-container-low rounded-lg p-0.5 border border-outline-variant ${className}`}
    >
      <button
        type="button"
        onClick={() => changeLang('en')}
        className={`px-2 py-1 rounded text-label-sm font-semibold transition-all ${
          lang === 'en'
            ? 'bg-surface-container-lowest text-on-surface shadow-xs font-bold'
            : 'text-on-surface-variant hover:text-on-surface'
        }`}
      >
        EN
      </button>
      <span className="text-outline text-label-sm px-1">|</span>
      <button
        type="button"
        onClick={() => changeLang('hi')}
        className={`px-2 py-1 rounded text-label-sm font-semibold transition-all ${
          lang === 'hi'
            ? 'bg-surface-container-lowest text-on-surface shadow-xs font-bold'
            : 'text-on-surface-variant hover:text-on-surface'
        }`}
      >
        हिं
      </button>
      <span className="text-outline text-label-sm px-1">|</span>
      <button
        type="button"
        onClick={() => changeLang('mr')}
        className={`px-2 py-1 rounded text-label-sm font-semibold transition-all ${
          lang === 'mr'
            ? 'bg-surface-container-lowest text-on-surface shadow-xs font-bold'
            : 'text-on-surface-variant hover:text-on-surface'
        }`}
      >
        मरा
      </button>
    </div>
  );
}
