'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LanguageSwitcher } from './LanguageSwitcher';
import { APP_CONFIG, CITIZEN_NAV_LINKS } from '@/lib/constants';
import { isAuthenticated, getUser, clearAuth, AuthUser } from '@/lib/auth';
import { logoutUser } from '@/lib/api';

export function TopNavigation() {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const syncAuth = () => {
      setIsLoggedIn(isAuthenticated());
      setCurrentUser(getUser());
    };

    syncAuth();
    window.addEventListener('auth-change', syncAuth);
    return () => window.removeEventListener('auth-change', syncAuth);
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    clearAuth();
    setMobileMenuOpen(false);
    router.push('/login');
  };

  const isItemActive = (path: string) => {
    if (path === '/') return pathname === '/';
    if (path === '/check') return pathname === '/check' || pathname.startsWith('/check/');
    return pathname === path || pathname.startsWith(`${path}/`);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800 transition-colors">
      <div className="h-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
        {/* Left Section: Brand Logo & Title */}
        <div className="flex items-center shrink-0">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shadow-xs group-hover:bg-primary-container transition-colors shrink-0">
              <span className="material-symbols-outlined text-[20px]">verified_user</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-headline-md text-lg tracking-tight font-extrabold text-slate-900 dark:text-white">
                {APP_CONFIG.name}
              </span>
              <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-primary/10 text-primary font-code-sm text-[10px] font-bold border border-primary/20">
                CIVIC TRUTH
              </span>
            </div>
          </Link>
        </div>

        {/* Center Section: Balanced Navigation Links (Desktop) */}
        <nav
          aria-label="Primary Navigation"
          className="hidden md:flex items-center gap-1 bg-transparent"
        >
          {CITIZEN_NAV_LINKS.map((item) => {
            const active = isItemActive(item.path);
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                  active
                    ? 'bg-primary/10 text-primary font-bold shadow-2xs'
                    : 'text-slate-600 hover:text-primary hover:bg-slate-50 dark:text-slate-300 dark:hover:text-primary dark:hover:bg-slate-800/60'
                }`}
              >
                <span
                  className={`material-symbols-outlined text-[17px] ${
                    active ? 'text-primary' : 'text-slate-400 dark:text-slate-500'
                  }`}
                >
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Section: Compact Language Dropdown & User Profile */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Language Selector Dropdown */}
          <LanguageSwitcher />

          {/* User Profile / Login Action */}
          {isLoggedIn ? (
            <div className="flex items-center gap-1.5">
              <Link
                href="/dashboard"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 hover:border-primary/40 text-xs text-slate-700 dark:text-slate-200 transition-colors shadow-2xs group focus:outline-none focus:ring-2 focus:ring-primary/20"
                title="Open Personal Dashboard"
              >
                <span className="material-symbols-outlined text-primary text-[18px] shrink-0">
                  account_circle
                </span>
                <span className="font-code-sm font-semibold max-w-[130px] truncate hidden sm:inline">
                  {currentUser?.phone_number || 'Citizen'}
                </span>
              </Link>

              <button
                type="button"
                onClick={handleLogout}
                className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 dark:text-slate-400 dark:hover:text-rose-400 dark:hover:bg-rose-950/30 transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500/20"
                title="Sign Out"
                aria-label="Sign Out"
              >
                <span className="material-symbols-outlined text-[18px]">logout</span>
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary-container text-white text-xs font-bold transition-all shadow-2xs flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <span className="material-symbols-outlined text-[16px]">login</span>
              <span>Login</span>
            </Link>
          )}

          {/* Mobile Hamburger Menu Toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="md:hidden p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-primary/20"
            aria-label="Toggle Navigation Menu"
            aria-expanded={mobileMenuOpen}
          >
            <span className="material-symbols-outlined text-[22px]">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-3 space-y-2 animate-in slide-in-from-top-2 duration-150 shadow-md">
          <nav className="flex flex-col gap-1">
            {CITIZEN_NAV_LINKS.map((item) => {
              const active = isItemActive(item.path);
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-colors ${
                    active
                      ? 'bg-primary/10 text-primary font-bold'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <span
                    className={`material-symbols-outlined text-[19px] ${
                      active ? 'text-primary' : 'text-slate-400'
                    }`}
                  >
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Mobile User Profile Section */}
          <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
            {isLoggedIn ? (
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">
                    account_circle
                  </span>
                  <span className="font-code-sm text-xs font-semibold text-slate-800 dark:text-slate-200">
                    {currentUser?.phone_number || 'Citizen'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="px-2.5 py-1 rounded-lg text-xs font-bold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[16px]">logout</span>
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full py-2 rounded-lg bg-primary text-white text-xs font-bold text-center flex items-center justify-center gap-1.5"
              >
                <span className="material-symbols-outlined text-[16px]">login</span>
                <span>Login with WhatsApp OTP</span>
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
