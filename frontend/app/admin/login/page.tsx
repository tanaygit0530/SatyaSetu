'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function AdminLoginPage() {
  const router = useRouter();
  const [deskId, setDeskId] = useState('DESK-DL-41');
  const [passkey, setPasskey] = useState('••••••••••••');

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    router.push('/admin');
  };

  return (
    <div className="min-h-screen w-full bg-background flex items-center justify-center p-space-md">
      <div className="w-full max-w-md space-y-space-md">
        {/* State / Hackathon Notice Bar */}
        <div className="bg-surface-container-low border border-outline-variant px-4 py-2.5 rounded-xl flex items-center justify-between text-on-surface-variant font-code-sm text-[12px]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-tertiary"></span>
            <span>AUDITOR CONSOLE DEMO</span>
          </div>
          <span className="font-bold text-primary">v4.2 LTS</span>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm">
          {/* Logo & Header */}
          <div className="flex items-center gap-3 pb-space-sm border-b border-outline-variant">
            <div className="w-10 h-10 rounded-xl bg-primary-container text-on-primary flex items-center justify-center font-bold text-[18px]">
              S
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-headline-sm text-headline-sm font-bold text-on-surface">
                  SachCheck Ops
                </span>
                <span className="px-1.5 py-0.5 rounded bg-surface-container font-code-sm text-[10px] uppercase font-bold text-on-surface-variant">
                  SECURE
                </span>
              </div>
              <p className="font-label-sm text-[11px] text-on-surface-variant">
                Auditor & Investigator Desk Authentication
              </p>
            </div>
          </div>

          <form onSubmit={handleSignIn} className="space-y-space-md">
            <div className="space-y-1">
              <label className="font-label-sm text-[12px] uppercase tracking-wider text-on-surface-variant font-bold">
                Assigned Desk Unit ID
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
                  badge
                </span>
                <input
                  type="text"
                  value={deskId}
                  onChange={(e) => setDeskId(e.target.value)}
                  required
                  className="w-full h-11 pl-10 pr-3 rounded-xl bg-surface-container-low border border-outline-variant font-code-sm text-[13px] text-on-surface focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="font-label-sm text-[12px] uppercase tracking-wider text-on-surface-variant font-bold">
                Security Passkey / Token
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
                  key
                </span>
                <input
                  type="password"
                  value={passkey}
                  onChange={(e) => setPasskey(e.target.value)}
                  required
                  className="w-full h-11 pl-10 pr-3 rounded-xl bg-surface-container-low border border-outline-variant font-code-sm text-[13px] text-on-surface focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-3 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-colors shadow-2xs flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">lock_open</span>
              <span>Authenticate & Enter Console</span>
            </button>
          </form>

          {/* Quick Demo Access Button */}
          <div className="pt-2 border-t border-outline-variant/60">
            <button
              type="button"
              onClick={() => router.push('/admin')}
              className="w-full py-2.5 rounded-xl border border-secondary text-secondary hover:bg-secondary/10 font-label-md text-label-md font-bold transition-colors flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">admin_panel_settings</span>
              <span>Direct Demo Login as Auditor</span>
            </button>
          </div>

          <div className="text-center pt-1">
            <Link
              href="/"
              className="font-label-sm text-[12px] text-on-surface-variant hover:text-primary transition-colors inline-flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[14px]">arrow_back</span>
              <span>Back to Citizen Portal</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
