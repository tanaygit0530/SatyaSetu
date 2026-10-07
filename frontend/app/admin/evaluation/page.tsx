'use client';

import React from 'react';

export default function AdminEvaluationPage() {
  return (
    <div className="space-y-space-lg">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">analytics</span>
            <span className="font-code-sm text-[12px] text-primary font-bold uppercase tracking-wider">
              BENCHMARK EVALUATION SUITE
            </span>
          </div>
          <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
            Evaluation & Adversarial Benchmarks
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Continuous validation against 15,350 labeled Indian civic claims and adversarial injection datasets.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[12px] font-bold">
            F1-Score: 0.997 (IFCN Target Passed)
          </span>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-space-md">
        <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-1">
          <span className="font-code-sm text-[11px] text-outline font-bold">PRECISION</span>
          <p className="font-headline-lg text-2xl font-bold text-on-surface">99.8%</p>
          <span className="font-code-sm text-[11px] text-tertiary">14 False Positives / 8,434 Claims</span>
        </div>
        <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-1">
          <span className="font-code-sm text-[11px] text-outline font-bold">RECALL</span>
          <p className="font-headline-lg text-2xl font-bold text-on-surface">99.6%</p>
          <span className="font-code-sm text-[11px] text-tertiary">28 False Negatives / 6,918 Checks</span>
        </div>
        <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-1">
          <span className="font-code-sm text-[11px] text-outline font-bold">VERBATIM QUOTE ACCURACY</span>
          <p className="font-headline-lg text-2xl font-bold text-on-surface">100.0%</p>
          <span className="font-code-sm text-[11px] text-tertiary">Zero Hallucinated Citations</span>
        </div>
        <div className="p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant space-y-1">
          <span className="font-code-sm text-[11px] text-outline font-bold">BENCHMARK SET</span>
          <p className="font-headline-lg text-2xl font-bold text-on-surface">15,352</p>
          <span className="font-code-sm text-[11px] text-on-surface-variant">eGazette + PIB Ground Truth</span>
        </div>
      </div>

      {/* Confusion Matrix Section */}
      <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Deterministic Confusion Matrix
            </h2>
            <p className="font-body-sm text-[12px] text-on-surface-variant">
              Auditing algorithmic alignment against human fact-checker consensus.
            </p>
          </div>
          <span className="font-code-sm text-[11px] text-outline">
            Test Split: Holdout-v4
          </span>
        </div>

        <div className="grid grid-cols-2 gap-space-md max-w-xl mx-auto pt-2 text-center">
          <div className="p-space-lg rounded-xl bg-emerald-50 border border-emerald-200 space-y-1">
            <span className="font-code-sm text-[11px] text-emerald-800 font-bold uppercase">
              True Positive (TP)
            </span>
            <p className="font-headline-lg text-3xl font-extrabold text-emerald-900">
              8,420
            </p>
            <span className="font-body-sm text-[12px] text-emerald-700">
              Corroborated claims correctly marked True
            </span>
          </div>

          <div className="p-space-lg rounded-xl bg-red-50 border border-red-200 space-y-1">
            <span className="font-code-sm text-[11px] text-red-800 font-bold uppercase">
              False Positive (FP)
            </span>
            <p className="font-headline-lg text-3xl font-extrabold text-red-900">
              14
            </p>
            <span className="font-body-sm text-[12px] text-red-700">
              Fabricated claims misclassified
            </span>
          </div>

          <div className="p-space-lg rounded-xl bg-red-50 border border-red-200 space-y-1">
            <span className="font-code-sm text-[11px] text-red-800 font-bold uppercase">
              False Negative (FN)
            </span>
            <p className="font-headline-lg text-3xl font-extrabold text-red-900">
              28
            </p>
            <span className="font-body-sm text-[12px] text-red-700">
              Genuine orders falsely flagged
            </span>
          </div>

          <div className="p-space-lg rounded-xl bg-emerald-50 border border-emerald-200 space-y-1">
            <span className="font-code-sm text-[11px] text-emerald-800 font-bold uppercase">
              True Negative (TN)
            </span>
            <p className="font-headline-lg text-3xl font-extrabold text-emerald-900">
              6,890
            </p>
            <span className="font-body-sm text-[12px] text-emerald-700">
              Rumours & scams correctly flagged False
            </span>
          </div>
        </div>
      </div>

      {/* Adversarial Suites List */}
      <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-space-md shadow-2xs">
        <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
          Adversarial Test Suites
        </h2>

        <div className="space-y-space-sm">
          {[
            {
              suite: 'Phishing & Homoglyph Injection',
              score: '100% Detected',
              desc: 'Testing lookalike government domains (e.g. pmssy-gov.in, sbi-kyc-update.org, pib-fact.in).',
            },
            {
              suite: 'Temporal Order Recirculation',
              score: '99.4% Detected',
              desc: 'Recirculating 2020 lockdown notices and 2016 demonetisation circulars with omitted dates.',
            },
            {
              suite: 'Vernacular Code-Mixing (Hinglish/Maranglish)',
              score: '98.8% Passed',
              desc: 'Auditing complex mixed Roman script sentences and slang against formal Hindi & Marathi gazettes.',
            },
            {
              suite: 'Zero-Hallucination Citation Validation',
              score: '100% Passed',
              desc: 'Ensuring model cannot output a claim without citing an existing verified Gazette URL.',
            },
          ].map((item) => (
            <div
              key={item.suite}
              className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div>
                <h3 className="font-label-md text-label-md font-bold text-on-surface">
                  {item.suite}
                </h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  {item.desc}
                </p>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-[#146336] font-code-sm text-[12px] font-bold shrink-0 self-start sm:self-auto">
                {item.score}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
