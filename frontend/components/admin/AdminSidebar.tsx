'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ADMIN_NAV_LINKS } from '@/lib/constants';

interface AdminSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function AdminSidebar({ isOpen, onClose }: AdminSidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={`fixed left-0 top-0 h-full w-64 bg-surface-container-lowest border-r border-outline-variant z-50 flex flex-col justify-between transition-transform duration-300 md:translate-x-0 ${
        isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      }`}
    >
      <div className="flex flex-col flex-1 min-h-0">
        {/* Top Header / Desk Badge */}
        <div className="h-16 px-space-md flex items-center justify-between border-b border-outline-variant">
          <Link href="/admin" className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center text-on-primary font-bold">
              S
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-headline-sm text-headline-sm text-on-surface tracking-tight font-bold">
                  SachCheck
                </span>
                <span className="px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant font-code-sm text-[10px] uppercase font-bold tracking-wider">
                  Ops
                </span>
              </div>
              <span className="font-label-sm text-[10px] text-on-surface-variant">
                Auditor Console
              </span>
            </div>
          </Link>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="md:hidden p-1 text-on-surface-variant hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          )}
        </div>

        {/* Desk Unit Status */}
        <div className="px-space-md py-space-sm">
          <div className="px-2.5 py-1.5 rounded-lg bg-surface-container-low flex items-center justify-between border border-outline-variant/60">
            <span className="font-label-sm text-[11px] uppercase tracking-wider text-on-surface-variant font-bold">
              Desk Unit
            </span>
            <span className="font-code-sm text-[11px] text-primary font-bold">
              DESK-DL-41
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-space-sm py-space-xs space-y-1 overflow-y-auto">
          {ADMIN_NAV_LINKS.map((item) => {
            const isActive =
              item.path === '/admin'
                ? pathname === '/admin'
                : pathname === item.path || pathname.startsWith(`${item.path}/`);

            return (
              <Link
                key={item.path}
                href={item.path}
                onClick={onClose}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg font-label-md text-label-md transition-colors ${
                  isActive
                    ? 'bg-primary-container text-on-primary font-semibold shadow-xs'
                    : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-[20px]">
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`px-2 py-0.5 rounded-full font-code-sm text-[11px] font-bold ${
                      isActive
                        ? 'bg-on-primary text-primary'
                        : 'bg-error-container text-on-error-container'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info & Logout */}
      <div className="p-space-md border-t border-outline-variant bg-surface-container-lowest space-y-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-tertiary"></span>
            <span className="font-code-sm text-[11px] text-on-surface-variant">
              Truth Engine v4.2 LTS
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-on-surface-variant">
            <span className="material-symbols-outlined text-[14px] text-tertiary">
              verified
            </span>
            <span className="font-label-sm text-[11px]">
              IFCN Standards Audited
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-outline-variant/60">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-on-surface-variant hover:text-primary font-label-sm text-[12px]"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            <span>Citizen Portal</span>
          </Link>
          <Link
            href="/admin/login"
            className="flex items-center gap-1 text-on-surface-variant hover:text-error font-label-sm text-[12px]"
          >
            <span className="material-symbols-outlined text-[16px]">logout</span>
            <span>Exit</span>
          </Link>
        </div>
      </div>
    </aside>
  );
}
