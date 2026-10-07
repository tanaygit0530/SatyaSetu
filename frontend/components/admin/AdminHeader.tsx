'use client';

import React, { useState } from 'react';
import { LanguageSwitcher } from '@/components/navigation/LanguageSwitcher';

interface AdminHeaderProps {
  onToggleSidebar?: () => void;
}

export function AdminHeader({ onToggleSidebar }: AdminHeaderProps) {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="fixed top-0 left-0 md:left-64 right-0 h-16 bg-surface-container-lowest/95 backdrop-blur-md border-b border-outline-variant z-40 px-space-md md:px-space-lg flex items-center justify-between gap-space-md">
      {/* Mobile Sidebar Toggle Button */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="md:hidden p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low rounded-lg"
          aria-label="Open sidebar"
        >
          <span className="material-symbols-outlined text-[24px]">menu</span>
        </button>

        <span className="hidden sm:inline-block px-2 py-0.5 rounded bg-surface-container text-on-surface-variant font-code-sm text-[11px] font-bold uppercase tracking-wider">
          LIVE DESK CONSOLE
        </span>
      </div>

      {/* Global Search Bar */}
      <div className="relative flex-1 max-w-md hidden sm:block">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
          search
        </span>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search checks, claims, domains, audit IDs..."
          className="w-full h-9 pl-9 pr-12 rounded-lg bg-surface-container-low text-on-surface placeholder:text-on-surface-variant font-body-sm text-body-sm border border-transparent focus:outline-none focus:border-primary focus:bg-surface-container-lowest focus:ring-1 focus:ring-primary"
        />
        <span className="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded bg-surface-container-highest text-on-surface-variant font-code-sm text-[10px] font-bold">
          ⌘K
        </span>
      </div>

      {/* Right Header Controls */}
      <div className="flex items-center gap-space-sm sm:gap-space-md">
        {/* Crawler Health Status */}
        <div className="hidden xl:flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-low border border-outline-variant/60">
          <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
          <span className="font-label-sm text-[12px] text-on-surface font-medium">
            NIC & PIB Crawlers: Online 99.9%
          </span>
        </div>

        {/* Language selector */}
        <LanguageSwitcher />

        {/* Notification Bell */}
        <button
          type="button"
          className="relative w-9 h-9 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
          title="Review Queue Alerts"
        >
          <span className="material-symbols-outlined text-[20px]">notifications</span>
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-error"></span>
        </button>

        {/* Auditor Profile */}
        <div className="flex items-center gap-2.5 pl-space-xs border-l border-outline-variant">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary font-bold text-[13px]">
            AD
          </div>
          <div className="hidden lg:flex flex-col text-left">
            <span className="font-label-sm text-[12px] font-semibold text-on-surface leading-tight">
              Auditor Desk
            </span>
            <span className="font-code-sm text-[10px] text-on-surface-variant leading-tight">
              DESK-DL-41
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
