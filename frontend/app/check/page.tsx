'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { InputTabs } from '@/components/input/InputTabs';

export default function CheckPage() {
  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-lg">
        {/* Page Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse"></span>
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Citizen Verification Intake
            </span>
          </div>
          <h1 className="font-headline-xl text-2xl sm:text-3xl md:text-4xl font-extrabold text-on-surface">
            Check a forward
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
            Submit any suspicious message, viral screenshot, audio note, official circular PDF, or link. Our deterministic pipeline will extract atomic claims and verify them against statutory records.
          </p>
        </div>

        {/* 5-Way Input Tabs Component */}
        <InputTabs />

        {/* Verification Guarantee & Evidence Standards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md pt-space-sm">
          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-1">
            <div className="flex items-center gap-2 text-primary font-bold">
              <span className="material-symbols-outlined text-[18px]">policy</span>
              <span className="font-label-md text-[13px]">Statutory Primary First</span>
            </div>
            <p className="font-body-sm text-[12px] text-on-surface-variant">
              Every verdict requires corroboration against Gazette notifications, ministry circulars, or court decrees.
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-1">
            <div className="flex items-center gap-2 text-primary font-bold">
              <span className="material-symbols-outlined text-[18px]">verified</span>
              <span className="font-label-md text-[13px]">No LLM Hallucination</span>
            </div>
            <p className="font-body-sm text-[12px] text-on-surface-variant">
              Claims are verified with deterministic rules. If evidence is missing, we report "Cannot Be Confirmed".
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-1">
            <div className="flex items-center gap-2 text-primary font-bold">
              <span className="material-symbols-outlined text-[18px]">privacy_tip</span>
              <span className="font-label-md text-[13px]">Strict Privacy Standard</span>
            </div>
            <p className="font-body-sm text-[12px] text-on-surface-variant">
              We never store citizen identity numbers, private sender metadata, or contact lists.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
