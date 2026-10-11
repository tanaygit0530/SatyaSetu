'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Language } from '@/types';

interface LanguageOption {
  code: Language;
  label: string;
  nativeLabel: string;
}

const LANGUAGES: LanguageOption[] = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिन्दी' },
  { code: 'mr', label: 'Marathi', nativeLabel: 'मराठी' },
];

interface LanguageSwitcherProps {
  className?: string;
}

export function LanguageSwitcher({ className = '' }: LanguageSwitcherProps) {
  const [lang, setLang] = useState<Language>('en');
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem('sachcheck_lang') as Language;
    if (saved && ['en', 'hi', 'mr'].includes(saved)) {
      setLang(saved);
      document.documentElement.lang = saved;
    }
  }, []);

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const changeLang = (newLang: Language) => {
    setLang(newLang);
    setIsOpen(false);
    localStorage.setItem('sachcheck_lang', newLang);
    document.documentElement.lang = newLang;
    window.dispatchEvent(new CustomEvent('language_change', { detail: newLang }));
  };

  const currentOption = LANGUAGES.find((l) => l.code === lang) || LANGUAGES[0];

  return (
    <div ref={dropdownRef} className={`relative inline-block text-left ${className}`}>
      {/* Trigger Button */}
      <button
        type="button"
        id="language-menu-button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={`Select language, currently ${currentOption.label}`}
        onClick={() => setIsOpen((prev) => !prev)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline-variant/80 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface text-xs font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 shadow-2xs"
      >
        <span className="material-symbols-outlined text-[16px] text-primary shrink-0">
          translate
        </span>
        <span className="font-medium text-slate-800 dark:text-slate-200">
          {currentOption.label}
        </span>
        <span
          className={`material-symbols-outlined text-[16px] text-on-surface-variant transition-transform duration-200 shrink-0 ${
            isOpen ? 'rotate-180' : ''
          }`}
        >
          expand_more
        </span>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="listbox"
          aria-labelledby="language-menu-button"
          className="absolute right-0 mt-1.5 w-40 rounded-xl bg-surface-container-lowest border border-outline-variant shadow-lg py-1 z-50 animate-in fade-in-50 zoom-in-95 duration-150"
        >
          {LANGUAGES.map((option) => {
            const isSelected = option.code === lang;
            return (
              <button
                key={option.code}
                role="option"
                aria-selected={isSelected}
                type="button"
                onClick={() => changeLang(option.code)}
                className={`w-full px-3 py-2 text-left text-xs flex items-center justify-between transition-colors ${
                  isSelected
                    ? 'bg-primary/10 text-primary font-bold'
                    : 'text-on-surface hover:bg-surface-container-low'
                }`}
              >
                <div className="flex flex-col">
                  <span className="text-on-surface font-semibold">{option.label}</span>
                  <span className="text-[10px] text-on-surface-variant">{option.nativeLabel}</span>
                </div>
                {isSelected && (
                  <span className="material-symbols-outlined text-primary text-[16px]">
                    check
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
