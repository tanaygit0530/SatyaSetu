'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';

export default function SettingsPage() {
  const [retention, setRetention] = useState('7_days');
  const [telemetry, setTelemetry] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  const handleClearCache = () => {
    if (confirm('Erase local verification records, tokens, and display preferences?')) {
      localStorage.clear();
      showToast('Local history and preferences erased.');
    }
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-xl">
        {/* Toast Alert */}
        {toastMessage && (
          <div className="fixed top-20 right-6 z-50 bg-tertiary-container text-on-tertiary px-4 py-2.5 rounded-xl shadow-lg font-label-md flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">check_circle</span>
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Header */}
        <div className="space-y-1 pb-space-xs border-b border-outline-variant">
          <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
            Settings & Civic Privacy
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Configure how your browser stores verification dossiers and processes citizen forwards.
          </p>
        </div>

        {/* Section 1: History Retention */}
        <div className="p-space-lg rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-space-md shadow-2xs">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">history</span>
            <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Device History Retention
            </h2>
          </div>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Specify how long evidence cards remain accessible in your device's local history timeline.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-sm pt-1">
            {[
              { id: 'zero', label: 'Zero History', sub: 'Purge when closing browser' },
              { id: '7_days', label: '7 Days', sub: 'Recommended for active citizens' },
              { id: '30_days', label: '30 Days', sub: 'Extended archival timeline' },
            ].map((option) => (
              <label
                key={option.id}
                onClick={() => {
                  setRetention(option.id);
                  showToast('Retention preference saved.');
                }}
                className={`p-space-md rounded-xl border cursor-pointer transition-all ${
                  retention === option.id
                    ? 'border-primary bg-primary-fixed/20 ring-1 ring-primary'
                    : 'border-outline-variant hover:bg-surface-container-low'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-label-md text-label-md font-bold text-on-surface">
                    {option.label}
                  </span>
                  <input
                    type="radio"
                    name="retention"
                    checked={retention === option.id}
                    onChange={() => {}}
                    className="accent-primary"
                  />
                </div>
                <span className="font-body-sm text-[12px] text-on-surface-variant">
                  {option.sub}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Section 2: Privacy Guarantee */}
        <div className="p-space-lg rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-space-md shadow-2xs">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">security</span>
            <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Privacy Guarantees
            </h2>
          </div>

          <div className="space-y-3 font-body-sm text-body-sm text-on-surface-variant">
            <div className="flex items-start gap-2.5">
              <span className="material-symbols-outlined text-tertiary text-[18px] shrink-0 mt-0.5">
                check_circle
              </span>
              <p>
                <b>No Phone Book Harvesting:</b> When using WhatsApp verification, we never inspect other group members or collect address books.
              </p>
            </div>
            <div className="flex items-start gap-2.5">
              <span className="material-symbols-outlined text-tertiary text-[18px] shrink-0 mt-0.5">
                check_circle
              </span>
              <p>
                <b>Zero Biometric / Aadhaar Storage:</b> Screenshot OCR automatically scrubs 12-digit Aadhaar patterns before running similarity indexing.
              </p>
            </div>
          </div>
        </div>

        {/* Section 3: Data Erase Button */}
        <div className="p-space-lg rounded-2xl bg-surface-container-low border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-space-md">
          <div className="space-y-1">
            <h3 className="font-headline-sm text-headline-sm font-bold text-error">
              Clear All Local Storage
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Removes verification history, cached cards, and custom preferences immediately.
            </p>
          </div>

          <button
            type="button"
            onClick={handleClearCache}
            className="px-4 py-2.5 rounded-xl border border-error text-error hover:bg-error hover:text-white font-label-md text-label-md font-bold transition-colors"
          >
            Clear Local Data
          </button>
        </div>
      </div>
    </AppShell>
  );
}
