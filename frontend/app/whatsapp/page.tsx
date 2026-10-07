'use client';

import React from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { APP_CONFIG } from '@/lib/constants';

export default function WhatsAppPage() {
  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-xl">
        {/* Header */}
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[12px] font-bold">
            <span className="w-2 h-2 rounded-full bg-[#1E8E4E]"></span>
            Official WhatsApp Verification Tipline
          </div>
          <h1 className="font-headline-xl text-3xl sm:text-4xl font-extrabold text-on-surface">
            Verify forwards where they already arrive.
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Forward any suspicious WhatsApp message, viral circular screenshot, or voice note to our verified number. Receive a tamper-proof evidence dossier in seconds.
          </p>
        </div>

        {/* Tipline Action Box */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl grid grid-cols-1 md:grid-cols-2 gap-space-lg items-center shadow-sm">
          <div className="space-y-4">
            <div className="space-y-1">
              <span className="font-code-sm text-[12px] text-outline font-bold">
                DIRECT WHATSAPP TIPLINE
              </span>
              <h2 className="font-headline-lg text-2xl font-bold text-on-surface">
                {APP_CONFIG.whatsappNumber}
              </h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Available 24/7 across India in Hindi, Marathi, and English.
              </p>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row gap-3">
              <a
                href={APP_CONFIG.whatsappDeepLink}
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-3 rounded-xl bg-[#1E8E4E] hover:bg-[#146336] text-white font-label-md text-label-md font-bold flex items-center justify-center gap-2 shadow-xs transition-colors"
              >
                <span className="material-symbols-outlined text-[20px]">chat</span>
                <span>Open in WhatsApp</span>
              </a>
              <Link
                href="/check"
                className="px-4 py-3 rounded-xl border border-outline-variant bg-surface-container-lowest text-on-surface font-label-md text-label-md font-semibold hover:bg-surface-container-low flex items-center justify-center"
              >
                Use Web Check Instead
              </Link>
            </div>
          </div>

          {/* WhatsApp Chat Simulation Mockup */}
          <div className="rounded-xl bg-[#EFEAE2] border border-outline-variant p-space-md space-y-3 font-sans text-[13px] shadow-inner">
            {/* User Incoming Forward Message */}
            <div className="bg-white rounded-lg p-2.5 rounded-tr-none shadow-xs max-w-[85%] ml-auto border border-black/5 space-y-1">
              <div className="flex items-center gap-1 text-[11px] text-slate-500 font-semibold italic">
                <span className="material-symbols-outlined text-[14px]">forward</span>
                <span>Forwarded</span>
              </div>
              <p className="text-slate-800">
                "Education Ministry giving ₹50,000 scholarship cash grant. Register immediately on pmssy-gov.in"
              </p>
              <div className="text-right text-[10px] text-slate-400">09:42 AM</div>
            </div>

            {/* SachCheck Bot Reply */}
            <div className="bg-[#EAF6EE] rounded-lg p-2.5 rounded-tl-none shadow-xs max-w-[90%] border border-[#B8E4C8] space-y-1.5">
              <div className="flex items-center gap-1 text-[#146336] font-bold text-[12px]">
                <span className="material-symbols-outlined text-[16px]">cancel</span>
                <span>VERDICT: FALSE / PHISHING</span>
              </div>
              <p className="text-slate-800 leading-snug">
                The ₹50,000 grant is fabricated. Genuine amount is ₹12,000/yr. The portal <i>pmssy-gov.in</i> is a credential-harvesting phishing site.
              </p>
              <div className="pt-1 border-t border-[#B8E4C8]/60 flex items-center justify-between text-[11px] text-[#146336] font-semibold">
                <span>View Full Gazette Proof:</span>
                <span className="underline">sachcheck.in/c/SC-2026-8941</span>
              </div>
              <div className="text-right text-[10px] text-slate-400">09:42 AM • Instant Bot</div>
            </div>
          </div>
        </div>

        {/* 3 Step Instructions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md pt-2">
          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
            <span className="font-code-sm text-primary font-bold text-[14px]">STEP 01</span>
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Save the Contact
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Add +91 91122 33445 to your phone contacts as "SachCheck Civic Bot".
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
            <span className="font-code-sm text-primary font-bold text-[14px]">STEP 02</span>
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Forward Any Message
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Forward unverified WhatsApp messages, images, PDF circulars, or voice memos.
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
            <span className="font-code-sm text-primary font-bold text-[14px]">STEP 03</span>
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Receive Proof Card
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Within 3 seconds, receive the atomic verdict and shareable link with statutory citations.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
