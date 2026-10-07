'use client';

import React from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { InputTabs } from '@/components/input/InputTabs';
import { VerdictBadge } from '@/components/verdict/VerdictBadge';

export default function LandingPage() {
  return (
    <AppShell>
      {/* SECTION 1: HERO */}
      <section className="relative w-full overflow-hidden bg-gradient-to-b from-surface-container-low/60 to-background py-space-xl md:py-space-2xl border-b border-outline-variant/60">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop flex flex-col items-center text-center space-y-space-md">
          {/* Trust Banner Pill */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-high border border-outline-variant text-primary font-label-sm text-[12px] font-semibold">
            <span className="material-symbols-outlined text-[16px] text-primary">verified_user</span>
            <span>Indian Civic Multi-lingual Fact Verification Engine</span>
            <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
            <span className="text-on-surface-variant font-code-sm">IFCN Standard</span>
          </div>

          {/* Main Headline */}
          <h1 className="font-headline-xl text-3xl sm:text-4xl md:text-5xl font-extrabold text-on-surface tracking-tight max-w-3xl leading-tight">
            Don't forward it. <br className="hidden sm:inline" />
            <span className="text-primary">Check it first.</span>
          </h1>

          {/* Subtitle */}
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">
            Forward it. Know if it's true. In your language, with statutory proof. We dissect complex forwards claim by claim against official gazettes.
          </p>

          {/* Integrated 5-Way Input Composer */}
          <div className="w-full max-w-3xl pt-space-md text-left">
            <InputTabs />
          </div>
        </div>
      </section>

      {/* SECTION 2: CLAIM DECOMPOSITION DEMONSTRATION */}
      <section className="py-space-2xl bg-surface-container-lowest border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop">
          <div className="text-center max-w-2xl mx-auto space-y-2 mb-space-xl">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Atomic Claim Extraction
            </span>
            <h2 className="font-headline-lg text-headline-lg font-bold text-on-surface">
              One forward can contain many claims.
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Rumours mix truthful facts with fabricated numbers to deceive readers. SachCheck unpacks every statement individually.
            </p>
          </div>

          {/* Visual Forward Decomposition Card */}
          <div className="max-w-4xl mx-auto rounded-2xl bg-surface-container-low border border-outline-variant p-space-md md:p-space-lg space-y-space-md">
            {/* Raw Forward Quote */}
            <div className="rounded-xl bg-surface-container-lowest p-space-md border border-outline-variant">
              <span className="font-label-sm text-[11px] font-bold uppercase tracking-wider text-outline">
                Forwarded WhatsApp Message:
              </span>
              <blockquote className="font-serif italic text-on-surface text-[16px] md:text-[17px] mt-1">
                "URGENT: Ministry of Education announced Prime Minister Higher Merit Scholarship 2026. All college students receive ₹50,000 cash grant directly in bank. Register today on pmssy-gov.in."
              </blockquote>
            </div>

            {/* Decomposed Atomic Claims */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md pt-2">
              {/* Claim 1 */}
              <div className="rounded-xl bg-surface-container-lowest border border-outline-variant p-space-md space-y-2 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="font-code-sm text-[11px] font-bold text-outline">CLAIM 1</span>
                  <VerdictBadge verdict="VERIFIED" size="sm" />
                </div>
                <p className="font-body-sm text-[13px] text-on-surface font-medium">
                  "Ministry has notified PM Higher Merit Scheme."
                </p>
                <p className="font-code-sm text-[11px] text-tertiary">
                  ✓ Confirmed in Gazette MoE/HE/2026/04
                </p>
              </div>

              {/* Claim 2 */}
              <div className="rounded-xl bg-surface-container-lowest border border-outline-variant p-space-md space-y-2 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="font-code-sm text-[11px] font-bold text-outline">CLAIM 2</span>
                  <VerdictBadge verdict="FALSE" size="sm" />
                </div>
                <p className="font-body-sm text-[13px] text-on-surface font-medium">
                  "All students receive ₹50,000 cash grant."
                </p>
                <p className="font-code-sm text-[11px] text-error">
                  ✕ False: ₹12,000/yr strictly for top 80th percentile
                </p>
              </div>

              {/* Claim 3 */}
              <div className="rounded-xl bg-surface-container-lowest border border-outline-variant p-space-md space-y-2 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="font-code-sm text-[11px] font-bold text-outline">CLAIM 3</span>
                  <VerdictBadge verdict="FALSE" size="sm" />
                </div>
                <p className="font-body-sm text-[13px] text-on-surface font-medium">
                  "Apply on domain pmssy-gov.in."
                </p>
                <p className="font-code-sm text-[11px] text-error">
                  ✕ Phishing URL. Genuine: scholarships.gov.in
                </p>
              </div>
            </div>

            <div className="text-center pt-2">
              <Link
                href="/check/SC-2026-8941"
                className="inline-flex items-center gap-1.5 font-label-md text-label-md text-primary font-bold hover:underline"
              >
                <span>View Full Forensic Verification Record</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: THE 5 CANONICAL VERDICTS */}
      <section className="py-space-2xl bg-background border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop">
          <div className="text-center max-w-2xl mx-auto space-y-2 mb-space-xl">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Standardized System
            </span>
            <h2 className="font-headline-lg text-headline-lg font-bold text-on-surface">
              The 5 Evidentiary Verdicts
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Every verdict token is strictly paired with an unambiguous glyph and color standard compliant with accessibility requirements.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-md">
            {[
              {
                verdict: 'VERIFIED' as const,
                desc: 'Full factual alignment with verifiable, authoritative primary records.',
              },
              {
                verdict: 'FALSE' as const,
                desc: 'Wholly fabricated statements or manipulated media debunked by official sources.',
              },
              {
                verdict: 'OUTDATED' as const,
                desc: 'Authentic historical orders misleadingly recirculated as present reality.',
              },
              {
                verdict: 'PARTLY_SUPPORTED' as const,
                desc: 'Mixture of factual premises and unverified extrapolations or numbers.',
              },
              {
                verdict: 'CANNOT_BE_CONFIRMED' as const,
                desc: 'Insufficient documentary records or subjective assertion without public record.',
              },
            ].map((item) => (
              <div
                key={item.verdict}
                className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant flex flex-col justify-between space-y-3 shadow-2xs"
              >
                <VerdictBadge verdict={item.verdict} size="md" />
                <p className="font-body-sm text-[13px] text-on-surface-variant flex-1">
                  {item.desc}
                </p>
                <div className="pt-2 border-t border-outline-variant/60 font-code-sm text-[11px] text-outline">
                  IFCN Section 11 Standard
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 4: 4-STEP PIPELINE */}
      <section className="py-space-2xl bg-surface-container-lowest border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop">
          <div className="text-center max-w-2xl mx-auto space-y-2 mb-space-xl">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              How It Works
            </span>
            <h2 className="font-headline-lg text-headline-lg font-bold text-on-surface">
              AI reads. Evidence proves. Rules decide.
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              We never let a black-box LLM make ungrounded decisions. Every verdict is backed by statutory evidence and deterministic rules.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-space-md">
            {[
              {
                step: '01',
                title: 'Atomic Extraction',
                desc: 'Multilingual NLP isolates specific testable factual claims from opinions, greetings, or rhetoric.',
                icon: 'segment',
              },
              {
                step: '02',
                title: 'Statutory Retrieval',
                desc: 'Live crawlers query eGazette, PIB Fact Check, National Portals, and Railway orders.',
                icon: 'account_balance',
              },
              {
                step: '03',
                title: 'Exact Quote Matching',
                desc: 'Extracts verbatim quotes from authenticated PDF circulars and certifies source precedence.',
                icon: 'format_quote',
              },
              {
                step: '04',
                title: 'Deterministic Verdict',
                desc: 'Rule engine executes hard Boolean checks to prevent hallucinations before publishing verdict.',
                icon: 'gavel',
              },
            ].map((col) => (
              <div
                key={col.step}
                className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-code-sm text-[14px] font-bold text-primary">
                    {col.step}
                  </span>
                  <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined text-[18px]">
                      {col.icon}
                    </span>
                  </div>
                </div>
                <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                  {col.title}
                </h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  {col.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 5: MULTILINGUAL SHOWCASE */}
      <section className="py-space-2xl bg-background border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop">
          <div className="text-center max-w-2xl mx-auto space-y-2 mb-space-xl">
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              Multilingual India
            </span>
            <h2 className="font-headline-lg text-headline-lg font-bold text-on-surface">
              Built for English, हिन्दी, and मराठी
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Misinformation targets linguistic comfort. SachCheck ingests and delivers evidence seamlessly across Indian languages.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md max-w-5xl mx-auto">
            {/* English Card */}
            <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-label-sm font-bold text-primary">English (Indian)</span>
                <span className="px-2 py-0.5 rounded bg-surface-container font-code-sm text-[11px]">EN</span>
              </div>
              <p className="font-serif italic text-on-surface text-[15px]">
                "Scholarship amount is ₹50,000 for all college students."
              </p>
              <div className="pt-2 border-t border-outline-variant">
                <VerdictBadge verdict="FALSE" size="sm" />
                <p className="font-body-sm text-[12px] text-on-surface-variant mt-1.5">
                  Refuted: Amount is ₹12,000/yr under official NSP guidelines.
                </p>
              </div>
            </div>

            {/* Hindi Card */}
            <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-label-sm font-bold text-primary">हिन्दी</span>
                <span className="px-2 py-0.5 rounded bg-surface-container font-code-sm text-[11px]">HI</span>
              </div>
              <p className="font-devanagari text-on-surface text-[15px]">
                "कॉलेज छात्रों के लिए छात्रवृत्ति राशि ₹50,000 सीधे बैंक में मिलेगी।"
              </p>
              <div className="pt-2 border-t border-outline-variant">
                <VerdictBadge verdict="FALSE" size="sm" />
                <p className="font-devanagari text-[12px] text-on-surface-variant mt-1.5">
                  असत्य: आधिकारिक एनएसपी दिशानिर्देशों के तहत राशि ₹12,000/वर्ष है।
                </p>
              </div>
            </div>

            {/* Marathi Card */}
            <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-label-sm font-bold text-primary">मराठी</span>
                <span className="px-2 py-0.5 rounded bg-surface-container font-code-sm text-[11px]">MR</span>
              </div>
              <p className="font-devanagari text-on-surface text-[15px]">
                "महाविद्यालयीन विद्यार्थ्यांसाठी शिष्यवृत्तीची रक्कम ₹50,000 आहे."
              </p>
              <div className="pt-2 border-t border-outline-variant">
                <VerdictBadge verdict="FALSE" size="sm" />
                <p className="font-devanagari text-[12px] text-on-surface-variant mt-1.5">
                  खोटे: अधिकृत राजपत्रानुसार रक्कम प्रतिवर्ष ₹12,000 मंजूर आहे.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 6: WHATSAPP INTEGRATION CALLOUT */}
      <section className="py-space-2xl bg-surface-container-low border-b border-outline-variant">
        <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop">
          <div className="max-w-4xl mx-auto rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl flex flex-col md:flex-row items-center justify-between gap-space-lg shadow-sm">
            <div className="space-y-3 text-left">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[12px] font-bold">
                <span className="w-2 h-2 rounded-full bg-[#1E8E4E]"></span>
                WhatsApp Verified Bot Active
              </div>
              <h3 className="font-headline-lg text-headline-lg font-bold text-on-surface">
                Verify where forwards already live.
              </h3>
              <p className="font-body-md text-body-md text-on-surface-variant max-w-lg">
                No app installation required. Forward any voice note, image circular, or forward directly to our verified civic tipline number.
              </p>
              <div className="pt-1 flex flex-wrap gap-3">
                <Link
                  href="/whatsapp"
                  className="px-5 py-2.5 rounded-xl bg-[#1E8E4E] hover:bg-[#146336] text-white font-label-md text-label-md font-bold flex items-center gap-2 shadow-xs transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">chat</span>
                  <span>Connect on WhatsApp</span>
                </Link>
                <Link
                  href="/how-we-decide"
                  className="px-4 py-2.5 rounded-xl border border-outline-variant text-on-surface font-label-md text-label-md hover:bg-surface-container-low"
                >
                  Read Methodology
                </Link>
              </div>
            </div>

            <div className="w-full md:w-64 p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2 text-center">
              <span className="font-code-sm text-[11px] text-outline font-bold">
                CIVIC TIPLINE
              </span>
              <p className="font-headline-sm text-[18px] font-bold text-on-surface">
                +91 91122 33445
              </p>
              <p className="font-body-sm text-[11px] text-on-surface-variant">
                Auto-replies in 3 seconds with official Gazette evidence cards.
              </p>
            </div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
