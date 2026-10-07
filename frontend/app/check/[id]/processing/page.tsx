'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const checkId = (params?.id as string) || 'SC-2026-8941';

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);

  const steps = [
    {
      id: 'step-1',
      title: 'Atomic Claim Extraction',
      description: 'Decomposing submitted message into 3 testable propositional claims in English & Hindi.',
      source: 'Multilingual NLP Engine v4.2',
    },
    {
      id: 'step-2',
      title: 'Statutory Repository Retrieval',
      description: 'Querying eGazette, PIB Fact Check, National Scholarship Portal, and Railway Board records.',
      source: 'NIC-DELHI-GW4 Live Crawlers',
    },
    {
      id: 'step-3',
      title: 'Verbatim Quote & Temporal Alignment',
      description: 'Checking document publication timestamps (2026 vs 2020) and extracting matching sections.',
      source: 'Deterministic Evidence Matcher',
    },
    {
      id: 'step-4',
      title: 'Boolean Rule Evaluation & Final Verdict',
      description: 'Evaluating financial discrepancies and fake domain warnings. Finalizing dossier.',
      source: 'IFCN Standard Decision Rules',
    },
  ];

  useEffect(() => {
    const timerInterval = setInterval(() => {
      setElapsedMs((prev) => prev + 100);
    }, 100);

    const stepInterval = setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev < steps.length - 1) {
          return prev + 1;
        } else {
          clearInterval(stepInterval);
          setTimeout(() => {
            router.push(`/check/${checkId}`);
          }, 1000);
          return prev;
        }
      });
    }, 850);

    return () => {
      clearInterval(timerInterval);
      clearInterval(stepInterval);
    };
  }, [checkId, router, steps.length]);

  return (
    <AppShell showFooter={false}>
      <div className="max-w-3xl mx-auto px-margin md:px-margin-desktop py-space-2xl space-y-space-xl">
        {/* Header with Case ID and Live Timer */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg text-center space-y-3 shadow-sm">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-fixed text-primary font-code-sm text-[12px] font-bold">
            <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
            <span>PIPELINE ACTIVE • CASE #{checkId}</span>
          </div>

          <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
            Checking this forward
          </h1>

          <p className="font-body-md text-on-surface-variant max-w-lg mx-auto">
            Extracting statements, consulting gazette databases, and formulating forensic proof.
          </p>

          <div className="pt-2 flex items-center justify-center gap-6 font-code-sm text-[13px] text-on-surface-variant">
            <div>
              <span>Latency: </span>
              <span className="font-bold text-primary">{(elapsedMs / 1000).toFixed(1)}s</span>
            </div>
            <div>
              <span>Status: </span>
              <span className="font-bold text-tertiary">Live Processing</span>
            </div>
          </div>
        </div>

        {/* Stepper Progress Modules */}
        <div className="space-y-space-md">
          {steps.map((step, idx) => {
            const isCompleted = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex;
            const isPending = idx > currentStepIndex;

            return (
              <div
                key={step.id}
                className={`p-space-md rounded-xl border transition-all duration-300 ${
                  isCurrent
                    ? 'bg-surface-container-lowest border-primary shadow-sm ring-1 ring-primary/20'
                    : isCompleted
                    ? 'bg-surface-container-lowest border-outline-variant opacity-90'
                    : 'bg-surface-container-low/40 border-outline-variant/60 opacity-60'
                }`}
              >
                <div className="flex items-start gap-3.5">
                  {/* Step status icon */}
                  <div className="shrink-0 mt-0.5">
                    {isCompleted ? (
                      <div className="w-7 h-7 rounded-full bg-emerald-100 text-[#146336] flex items-center justify-center">
                        <span className="material-symbols-outlined text-[18px]">check_circle</span>
                      </div>
                    ) : isCurrent ? (
                      <div className="w-7 h-7 rounded-full bg-primary text-on-primary flex items-center justify-center animate-pulse">
                        <span className="material-symbols-outlined text-[16px]">sync</span>
                      </div>
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-surface-container-high text-on-surface-variant flex items-center justify-center font-code-sm text-[12px] font-bold">
                        0{idx + 1}
                      </div>
                    )}
                  </div>

                  {/* Step text */}
                  <div className="flex-1 space-y-1">
                    <div className="flex flex-wrap items-center justify-between gap-1">
                      <h3
                        className={`font-label-md text-label-md font-bold ${
                          isCurrent ? 'text-primary' : 'text-on-surface'
                        }`}
                      >
                        {step.title}
                      </h3>
                      <span className="font-code-sm text-[11px] text-outline">
                        {step.source}
                      </span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      {step.description}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Skip to Result Button */}
        <div className="text-center pt-2">
          <button
            type="button"
            onClick={() => router.push(`/check/${checkId}`)}
            className="text-primary hover:underline font-label-md text-label-md font-semibold inline-flex items-center gap-1"
          >
            <span>Skip animation & view result immediately</span>
            <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
          </button>
        </div>
      </div>
    </AppShell>
  );
}
