'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { InputTabs } from '@/components/input/InputTabs';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';
import { APP_CONFIG } from '@/lib/constants';
import { isAuthenticated } from '@/lib/auth';

export default function LandingPage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(isAuthenticated());
  }, []);

  return (
    <AppShell>
      {/* SECTION 1: HERO */}
      <section className="relative w-full overflow-hidden bg-gradient-to-b from-surface-container-low/70 via-background to-background py-space-xl md:py-space-2xl border-b border-outline-variant/60">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop flex flex-col items-center text-center space-y-space-md">
          {/* Trust Banner Pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-surface-container-high border border-outline-variant text-primary font-label-sm text-[12px] font-semibold">
            <span className="material-symbols-outlined text-[16px] text-primary">verified_user</span>
            <span>Official SatyaSetu Misinformation Combat Architecture</span>
            <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
            <span className="text-on-surface-variant font-code-sm">IFCN Standard</span>
          </div>

          {/* Main Headline */}
          <h1 className="font-headline-xl text-3xl sm:text-5xl md:text-6xl font-black text-on-surface tracking-tight max-w-4xl leading-tight">
            Before You Forward It, <br className="hidden sm:inline" />
            <span className="text-primary bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-700">
              Verify It.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl text-base sm:text-lg">
            Verify suspicious messages, screenshots, voice notes, PDFs, and links with evidence-backed explanations in your language.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link
              href={isLoggedIn ? '/dashboard' : '/login'}
              className="px-6 py-3 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-all shadow-xs flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-[20px]">
                {isLoggedIn ? 'dashboard' : 'login'}
              </span>
              <span>{isLoggedIn ? 'Go to Personal Dashboard' : 'Start Verifying / Get Started'}</span>
            </Link>

            <a
              href="#how-it-works"
              className="px-5 py-3 rounded-xl border border-outline-variant bg-surface-container-low hover:bg-surface-container text-on-surface font-label-md text-label-md font-semibold transition-colors flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[18px]">account_tree</span>
              <span>How It Works</span>
            </a>

            <Link
              href="/whatsapp"
              className="px-5 py-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-[#146336] dark:text-emerald-300 font-label-md text-label-md font-semibold transition-colors flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[18px] text-emerald-600">chat</span>
              <span>WhatsApp Tipline</span>
            </Link>
          </div>

          {/* Integrated Multi-Modal Verification Composer */}
          <div className="w-full max-w-3xl pt-space-lg text-left">
            <InputTabs />
          </div>
        </div>
      </section>

      {/* SECTION 2: HOW IT WORKS (Compact Flow Diagram) */}
      <section id="how-it-works" className="py-space-2xl bg-surface-container-lowest border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop space-y-space-xl">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Verification Pipeline
            </span>
            <h2 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
              How SatyaSetu Verifies Claims
            </h2>
            <p className="font-body-md text-on-surface-variant text-sm sm:text-base">
              A four-stage deterministic workflow powered by authoritative source grounding and atomic claim extraction.
            </p>
          </div>

          {/* Compact 4-Step Diagram */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-space-md relative">
            {/* Step 1 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-3 relative">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary font-code-sm font-bold flex items-center justify-center border border-primary/20">
                01
              </div>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                1. Submit Content
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Forward WhatsApp messages, upload circular PDFs, audio clips, or paste news links into our portal.
              </p>
            </div>

            {/* Step 2 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-3 relative">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary font-code-sm font-bold flex items-center justify-center border border-primary/20">
                02
              </div>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                2. Extract Claims
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Multi-claim statements are decomposed into atomic, verifiable propositions to isolate falsehoods from truth.
              </p>
            </div>

            {/* Step 3 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-3 relative">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary font-code-sm font-bold flex items-center justify-center border border-primary/20">
                03
              </div>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                3. Retrieve Evidence
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Queries Tier-1 Gazettes, PIB Fact Check, and statutory archives. Verified against Shared Rumour Memory.
              </p>
            </div>

            {/* Step 4 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-3 relative">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary font-code-sm font-bold flex items-center justify-center border border-primary/20">
                04
              </div>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                4. Deliver Verdict
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Receive an authoritative verdict, verbatim quotations, and direct links to official sources in your language.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: FIVE VERDICTS TAXONOMY */}
      <section className="py-space-2xl bg-surface-container-low/50 border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop space-y-space-xl">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Transparent Classification
            </span>
            <h2 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
              The Five Evidentiary Verdicts
            </h2>
            <p className="font-body-md text-on-surface-variant text-sm">
              SatyaSetu adheres strictly to IFCN fact-checking criteria. We never guess: when evidence is insufficient, claims are marked as unconfirmed.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-md">
            {/* 1. VERIFIED */}
            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-emerald-500/30 space-y-2.5 shadow-2xs">
              <VerdictBadge verdict="VERIFIED" size="sm" />
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Statutorily Accurate
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Supported by active official gazette notifications, primary circulars, or certified government announcements.
              </p>
            </div>

            {/* 2. FALSE */}
            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-rose-500/30 space-y-2.5 shadow-2xs">
              <VerdictBadge verdict="FALSE" size="sm" />
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Factually Refuted
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Directly contradicted by official public records, statutory notices, or confirmed as fabricated disinformation.
              </p>
            </div>

            {/* 3. OUTDATED */}
            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-amber-500/30 space-y-2.5 shadow-2xs">
              <VerdictBadge verdict="OUTDATED" size="sm" />
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Expired Context
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                May have been true in a previous financial year or pandemic period, but circulated today as current truth.
              </p>
            </div>

            {/* 4. PARTLY_SUPPORTED */}
            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-orange-500/30 space-y-2.5 shadow-2xs">
              <VerdictBadge verdict="PARTLY_SUPPORTED" size="sm" />
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Mixed Evidence
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Contains a kernel of truth (e.g., scheme exists) mixed with inflated grant amounts or phishing registration links.
              </p>
            </div>

            {/* 5. CANNOT_BE_CONFIRMED */}
            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-slate-500/30 space-y-2.5 shadow-2xs">
              <VerdictBadge verdict="CANNOT_BE_CONFIRMED" size="sm" />
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Insufficient Evidence
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                When official records are absent or private claims lack public evidence, SatyaSetu abstains from speculation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 4: REAL IMPLEMENTED FEATURES */}
      <section id="features" className="py-space-2xl bg-surface-container-lowest border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop space-y-space-xl">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Core Capabilities
            </span>
            <h2 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
              Engineered for Real-World Civic Misinformation
            </h2>
            <p className="font-body-md text-on-surface-variant text-sm">
              Every feature below is implemented in code and operational across our web portal and WhatsApp bot.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-md">
            {/* Feature 1 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[28px]">multimodal</span>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                Multimodal Input Ingestion
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Accepts text forwards, screenshot images with OCR, audio voice memos, PDF circulars, and article URLs.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[28px]">segment</span>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                Atomic Claim-Level Correction
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Decomposes mixed forwards into discrete statements so legitimate facts aren't mistakenly dismissed alongside false claims.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[28px]">policy</span>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                Evidence-Grounded Verdicts
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Every verdict cites Tier-1 gazettes, official .gov.in domains, and verified IFCN repositories with verbatim quotes.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[28px]">fingerprint</span>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                Shared Rumour Memory
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Identifies viral forwards using L1 caching and L2 vector memory, returning instant verified responses to curb spread.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[28px]">translate</span>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                Multilingual Reasoning
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Supports verification and explanation in Hindi, Marathi, and English with cross-lingual claim mapping.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="p-space-md rounded-2xl bg-surface-container-low border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[28px]">chat</span>
              <h3 className="font-headline-sm text-base font-bold text-on-surface">
                Twilio WhatsApp Integration
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Direct tipline integration via official webhook with verified OTP delivery and user session management.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5: CIVIC IMPACT (INTENDED BENEFITS) */}
      <section id="impact" className="py-space-2xl bg-surface-container-low/40 border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop space-y-space-xl">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Intended Benefits
            </span>
            <h2 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
              Civic Impact & Digital Literacy Goals
            </h2>
            <p className="font-body-md text-on-surface-variant text-sm">
              Our mission is to empower citizens with evidentiary truth before harmful forwards are amplified.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[24px]">language</span>
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Language Inclusion
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Ensuring citizens accessing regional languages receive equal evidentiary protection from viral deceptions.
              </p>
            </div>

            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[24px]">school</span>
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Media Literacy
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Training readers to spot phishing URLs, forged government circulars, and out-of-context video claims.
              </p>
            </div>

            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[24px]">shield</span>
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Financial Scam Prevention
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Intercepting fake welfare recruitment scams and fraudulent lottery schemes before citizens suffer losses.
              </p>
            </div>

            <div className="p-space-md rounded-2xl bg-surface-container-lowest border border-outline-variant space-y-2 shadow-2xs">
              <span className="material-symbols-outlined text-primary text-[24px]">speed</span>
              <h3 className="font-headline-sm text-sm font-bold text-on-surface">
                Rapid Fact-Check Triage
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Substantially reducing turnaround time from days to seconds with deterministic rules and authoritative search.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 6: FOOTER */}
      <footer className="py-space-xl bg-surface-container-lowest border-t border-outline-variant text-xs text-on-surface-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop flex flex-col sm:flex-row items-center justify-between gap-space-md text-center sm:text-left">
          <div className="space-y-1">
            <div className="flex items-center justify-center sm:justify-start gap-2">
              <span className="font-bold text-on-surface">{APP_CONFIG.name}</span>
              <span>•</span>
              <span>{APP_CONFIG.compliance}</span>
            </div>
            <p className="text-[11px] text-outline">
              Evidence-based misinformation verification engine. Built for transparency and civic resilience.
            </p>
          </div>

          <div className="flex items-center gap-4 flex-wrap justify-center font-medium">
            <Link href="/whatsapp" className="hover:text-primary transition-colors">
              WhatsApp Tipline
            </Link>
            <Link href="/how-we-decide" className="hover:text-primary transition-colors">
              Decision Standard
            </Link>
            <Link href="/history" className="hover:text-primary transition-colors">
              Public Ledger
            </Link>
            <Link href="/login" className="hover:text-primary transition-colors font-bold text-primary">
              Citizen Login
            </Link>
          </div>
        </div>
      </footer>
    </AppShell>
  );
}
