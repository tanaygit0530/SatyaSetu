'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function MobileNavigation() {
  const pathname = usePathname();

  const tabs = [
    { label: 'Verify', path: '/check', icon: 'fact_check' },
    { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
    { label: 'History', path: '/history', icon: 'history' },
    { label: 'WhatsApp', path: '/whatsapp', icon: 'chat' },
    { label: 'Standards', path: '/how-we-decide', icon: 'policy' },
  ];

  // Don't show bottom bar inside admin pages
  if (pathname.startsWith('/admin')) {
    return null;
  }

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface-container-lowest/95 backdrop-blur-md border-t border-outline-variant px-2 py-1.5 flex items-center justify-around shadow-lg">
      {tabs.map((tab) => {
        const isActive =
          tab.path === '/check'
            ? pathname === '/check' || pathname.startsWith('/check/')
            : pathname === tab.path;
        return (
          <Link
            key={tab.path}
            href={tab.path}
            className={`flex flex-col items-center justify-center py-1 px-3 rounded-lg text-center transition-colors ${
              isActive
                ? 'text-primary font-bold'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span
              className={`material-symbols-outlined text-[22px] ${
                isActive ? 'fill text-primary' : ''
              }`}
            >
              {tab.icon}
            </span>
            <span className="font-label-sm text-[11px] leading-tight mt-0.5">
              {tab.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
