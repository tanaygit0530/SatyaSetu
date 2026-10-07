'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LanguageSwitcher } from './LanguageSwitcher';
import { FontScaler } from './FontScaler';
import { APP_CONFIG, CITIZEN_NAV_LINKS } from '@/lib/constants';

export function TopNavigation() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-surface-container-lowest/95 backdrop-blur-md border-b border-outline-variant">
      <div className="h-16 max-w-7xl mx-auto px-margin md:px-margin-desktop flex items-center justify-between gap-gutter">
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-space-lg">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center text-on-primary shadow-xs group-hover:bg-primary transition-colors">
              <span className="material-symbols-outlined text-[20px]">verified_user</span>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="font-headline-md text-headline-md text-on-surface tracking-tight font-bold">
                SachCheck
              </span>
              <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-primary-fixed text-on-primary-fixed font-code-sm text-[10px] font-bold">
                CIVIC TRUTH
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {CITIZEN_NAV_LINKS.map((item) => {
              const isActive =
                item.path === '/'
                  ? pathname === '/'
                  : pathname === item.path || pathname.startsWith(`${item.path}/`);
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={`px-3 py-1.5 rounded-lg font-label-md text-label-md transition-colors flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-surface-container text-primary font-bold shadow-2xs'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Utility Controls */}
        <div className="flex items-center gap-space-sm sm:gap-space-md">
          {/* Language Switcher */}
          <LanguageSwitcher className="hidden sm:inline-flex" />

          {/* Font Scaler */}
          <FontScaler className="hidden md:inline-flex" />

          {/* Admin link shortcut */}
          <Link
            href="/admin"
            className="hidden lg:flex items-center gap-1 px-2.5 py-1 rounded-lg border border-outline-variant text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low font-label-sm text-label-sm"
          >
            <span className="material-symbols-outlined text-[16px] text-secondary">
              admin_panel_settings
            </span>
            <span>Auditor Desk</span>
          </Link>

          {/* Profile / Sign In */}
          <Link
            href="/login"
            className="w-9 h-9 rounded-full bg-surface-container-low border border-outline-variant flex items-center justify-center text-on-surface hover:bg-surface-container transition-colors"
            title="Citizen Account"
          >
            <span className="material-symbols-outlined text-[20px] text-on-surface-variant">
              person
            </span>
          </Link>

          {/* Mobile Hamburger Toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-low"
            aria-label="Toggle Navigation Menu"
          >
            <span className="material-symbols-outlined text-[24px]">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-surface-container-lowest border-b border-outline-variant px-margin py-space-md space-y-3">
          <nav className="flex flex-col gap-1">
            {CITIZEN_NAV_LINKS.map((item) => (
              <Link
                key={item.path}
                href={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg text-on-surface font-label-md text-label-md flex items-center gap-2 hover:bg-surface-container-low"
              >
                <span className="material-symbols-outlined text-[20px] text-primary">
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </Link>
            ))}
            <Link
              href="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg text-on-surface font-label-md text-label-md flex items-center gap-2 hover:bg-surface-container-low"
            >
              <span className="material-symbols-outlined text-[20px] text-primary">
                settings
              </span>
              <span>Settings</span>
            </Link>
            <Link
              href="/admin"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg text-secondary font-label-md text-label-md flex items-center gap-2 hover:bg-surface-container-low"
            >
              <span className="material-symbols-outlined text-[20px]">
                admin_panel_settings
              </span>
              <span>Admin Console</span>
            </Link>
          </nav>

          <div className="pt-2 border-t border-outline-variant flex items-center justify-between">
            <LanguageSwitcher />
            <FontScaler />
          </div>
        </div>
      )}
    </header>
  );
}
