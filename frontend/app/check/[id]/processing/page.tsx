'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { getCheckStatus, CheckStatusResponse } from '@/lib/api';

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const checkId = (params?.id as string) || '';

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [activeStage, setActiveStage] = useState('RECEIVED');
  const [statusResponse, setStatusResponse] = useState<CheckStatusResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isFailed, setIsFailed] = useState(false);

  const steps = [
    {
      id: 'step-1',
      stageKey: 'EXTRACTING',
      title: 'Atomic Claim Extraction',
      description: 'Decomposing submitted message into testable propositional claims and entities.',
      source: 'Multilingual NLP Engine',
    },
    {
      id: 'step-2',
      stageKey: 'RETRIEVING',
      title: 'Statutory Repository Retrieval',
      description: 'Querying eGazette, PIB Fact Check, National Portals, and regulatory archives.',
      source: 'Authoritative Multi-Source Retrieval',
    },
    {
      id: 'step-3',
      stageKey: 'VALIDATING',
      title: 'Verbatim Quote & Evidence Grounding',
      description: 'Extracting small evidence windows, validating exact quotes, and checking temporal status.',
      source: 'Evidence Locking Validator',
    },
    {
      id: 'step-4',
      stageKey: 'VERIFYING',
      title: 'Deterministic Verdict Evaluation',
      description: 'Executing deterministic rule engine and computing confidence without hallucination.',
      source: 'Deterministic Rule Engine',
    },
  ];

  // Map backend stage string to stepper index
  const stageToIndex = (stage: string): number => {
    const s = stage.toUpperCase();
    if (s === 'RECEIVED') return 0;
    if (s === 'EXTRACTING' || s === 'CLAIMING') return 0;
    if (s === 'RETRIEVING') return 1;
    if (s === 'VALIDATING') return 2;
    if (s === 'VERIFYING') return 3;
    if (s === 'COMPLETED') return 4;
    return 0;
  };

  useEffect(() => {
    if (!checkId) return;

    const timer = setInterval(() => {
      setElapsedMs((prev) => prev + 100);
    }, 100);

    let isSubscribed = true;

    const pollStatus = async () => {
      try {
        const data = await getCheckStatus(checkId);
        if (!isSubscribed) return;

        setStatusResponse(data);
        setActiveStage(data.stage || 'RECEIVED');
        setCurrentStepIndex(stageToIndex(data.stage || 'RECEIVED'));

        if (data.status === 'COMPLETED' || data.stage === 'COMPLETED') {
          clearInterval(timer);
          clearInterval(pollInterval);
          setTimeout(() => {
            router.push(`/check/${encodeURIComponent(checkId)}`);
          }, 400);
        } else if (data.status === 'FAILED') {
          clearInterval(timer);
          clearInterval(pollInterval);
          setIsFailed(true);
          setErrorMessage(data.error || 'Verification processing encountered an error in the pipeline.');
        }
      } catch (err: any) {
        if (!isSubscribed) return;
        console.warn('Status poll attempt failed:', err?.message);
        // Do not fail immediately on transient network blip; keep polling up to timeout
      }
    };

    // Initial check
    pollStatus();
    const pollInterval = setInterval(pollStatus, 400);

    return () => {
      isSubscribed = false;
      clearInterval(timer);
      clearInterval(pollInterval);
    };
  }, [checkId, router]);

  // Compute calculated progress percent
  const progressPercent = Math.min(
    100,
    Math.max(15, ((currentStepIndex + 1) / steps.length) * 100)
  );

  return (
    <AppShell showFooter={false}>
      <div className="max-w-3xl mx-auto px-margin md:px-margin-desktop py-space-xl sm:py-space-2xl space-y-space-lg">
        {/* Radar Scanner Hero Card */}
        <div className="rounded-3xl bg-surface-container-lowest border border-outline-variant p-space-lg sm:p-space-xl text-center space-y-4 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-primary via-tertiary to-primary animate-[pulse_2s_infinite]"></div>

          {/* Concentric Sonar Radar Beacon */}
          <div className="relative flex items-center justify-center w-24 h-24 mx-auto pt-2">
            {!isFailed ? (
              <>
                <div className="absolute inset-2 rounded-full bg-primary/10 animate-ping duration-1000"></div>
                <div className="absolute inset-0 rounded-full border border-primary/25 animate-[spin_8s_linear_infinite]"></div>
                <div className="absolute -inset-2 rounded-full border border-dashed border-primary/20 animate-[spin_14s_linear_infinite_reverse]"></div>
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary to-primary-container text-on-primary flex items-center justify-center shadow-lg shadow-primary/20">
                  <span className="material-symbols-outlined text-[32px] animate-pulse">radar</span>
                </div>
              </>
            ) : (
              <div className="w-16 h-16 rounded-2xl bg-error-container text-error flex items-center justify-center shadow-md">
                <span className="material-symbols-outlined text-[32px]">warning</span>
              </div>
            )}
          </div>

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-fixed text-primary font-code-sm text-[12px] font-bold">
            <span className={`w-2 h-2 rounded-full ${isFailed ? 'bg-error' : 'bg-primary animate-ping'}`}></span>
            <span>REAL-TIME AUDIT IN PROGRESS • CASE #{checkId || 'WAITING'}</span>
          </div>

          <h1 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
            {isFailed ? 'Verification Halted' : 'Verifying Claim Authenticity'}
          </h1>

          <p className="font-body-md text-on-surface-variant max-w-lg mx-auto leading-relaxed">
            {isFailed
              ? 'An error occurred while evaluating the evidence.'
              : 'Cross-referencing Gazette of India, PIB bulletins, official registries, and executing deterministic proof rules.'}
          </p>

          {/* Real-Time Linear Progress Indicator */}
          {!isFailed && (
            <div className="max-w-md mx-auto space-y-1.5 pt-2">
              <div className="flex items-center justify-between font-code-sm text-[11px] text-on-surface-variant">
                <span>Verification Progress</span>
                <span className="font-bold text-primary">{Math.round(progressPercent)}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-surface-container overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary via-tertiary to-primary transition-all duration-300 rounded-full"
                  style={{ width: `${progressPercent}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="pt-2 flex flex-wrap items-center justify-center gap-4 sm:gap-8 font-code-sm text-[13px] text-on-surface-variant border-t border-outline-variant/60">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-primary">timer</span>
              <span>Latency: </span>
              <span className="font-bold text-primary">{(elapsedMs / 1000).toFixed(1)}s</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-tertiary">hub</span>
              <span>Current Stage: </span>
              <span className={`font-bold ${isFailed ? 'text-error' : 'text-tertiary'}`}>
                {activeStage}
              </span>
            </div>
          </div>
        </div>

        {/* Failure Card if processing failed */}
        {isFailed && (
          <div className="rounded-2xl bg-error-container/20 border border-error/40 p-space-lg space-y-3 text-center">
            <div className="w-12 h-12 rounded-full bg-error/10 text-error flex items-center justify-center mx-auto">
              <span className="material-symbols-outlined text-[28px]">report_problem</span>
            </div>
            <h3 className="font-headline-sm text-lg font-bold text-error">
              Verification Could Not Be Completed
            </h3>
            <p className="font-body-sm text-on-surface max-w-md mx-auto">
              {errorMessage}
            </p>
            <div className="pt-2 flex justify-center gap-3">
              <Link
                href="/check"
                className="px-4 py-2 rounded-xl bg-primary text-on-primary font-label-md text-label-md font-semibold"
              >
                Submit New Check
              </Link>
            </div>
          </div>
        )}

        {/* Stepper Progress Modules */}
        {!isFailed && (
          <div className="space-y-space-md">
            {steps.map((step, idx) => {
              const isCompleted = idx < currentStepIndex;
              const isCurrent = idx === currentStepIndex;

              return (
                <div
                  key={step.id}
                  className={`p-space-md rounded-xl border transition-all ${
                    isCurrent
                      ? 'bg-surface-container-lowest border-primary shadow-xs ring-1 ring-primary/20'
                      : isCompleted
                      ? 'bg-surface-container-low/60 border-outline-variant/60 opacity-90'
                      : 'bg-surface-container-lowest/40 border-outline-variant/40 opacity-40'
                  }`}
                >
                  <div className="flex items-start justify-between gap-space-md">
                    <div className="flex items-start gap-space-md">
                      {/* Step Indicator Icon */}
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                          isCompleted
                            ? 'bg-emerald-100 text-[#146336]'
                            : isCurrent
                            ? 'bg-primary text-on-primary'
                            : 'bg-surface-container text-outline'
                        }`}
                      >
                        {isCompleted ? (
                          <span className="material-symbols-outlined text-[20px]">check</span>
                        ) : isCurrent ? (
                          <span className="w-3.5 h-3.5 border-2 border-on-primary border-t-transparent rounded-full animate-spin"></span>
                        ) : (
                          <span className="font-code-sm text-[12px] font-bold">0{idx + 1}</span>
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-label-lg text-label-lg font-bold text-on-surface">
                            {step.title}
                          </h3>
                          {isCurrent && (
                            <span className="px-2 py-0.5 rounded-full bg-primary-fixed text-primary font-code-sm text-[10px] font-bold uppercase animate-pulse">
                              Processing
                            </span>
                          )}
                        </div>
                        <p className="font-body-sm text-body-sm text-on-surface-variant">
                          {step.description}
                        </p>
                      </div>
                    </div>

                    <span className="font-code-sm text-[11px] text-outline text-right shrink-0 hidden sm:inline">
                      {step.source}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Live Forensic Notice */}
        <div className="text-center font-code-sm text-[12px] text-on-surface-variant flex items-center justify-center gap-2">
          <span className="material-symbols-outlined text-[16px] text-primary">gavel</span>
          <span>Deterministic verdict evaluation enforces zero hallucination policy.</span>
        </div>
      </div>
    </AppShell>
  );
}
