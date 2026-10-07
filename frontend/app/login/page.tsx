'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';

export default function CitizenLoginPage() {
  const router = useRouter();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState('');

  const handleSendOtp = (e: React.FormEvent) => {
    e.preventDefault();
    if (phoneNumber.length >= 10) {
      setOtpSent(true);
    }
  };

  const handleVerifyOtp = (e: React.FormEvent) => {
    e.preventDefault();
    router.push('/check');
  };

  const handleDemoSignIn = () => {
    router.push('/check');
  };

  return (
    <AppShell showFooter={false}>
      <div className="max-w-md mx-auto px-margin py-space-2xl space-y-space-lg">
        {/* Card Container */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm text-center">
          {/* Emblem */}
          <div className="w-12 h-12 rounded-xl bg-primary-container text-on-primary flex items-center justify-center mx-auto shadow-xs">
            <span className="material-symbols-outlined text-[28px]">verified_user</span>
          </div>

          <div className="space-y-1">
            <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
              Citizen Sign In
            </h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Access your personal verification timeline and bookmark statutory evidence cards.
            </p>
          </div>

          {!otpSent ? (
            <form onSubmit={handleSendOtp} className="space-y-space-md text-left pt-2">
              <div className="space-y-1">
                <label className="font-label-md text-label-md text-on-surface font-semibold">
                  Mobile Number (India)
                </label>
                <div className="flex rounded-xl border border-outline-variant overflow-hidden focus-within:border-primary focus-within:ring-1 focus-within:ring-primary">
                  <span className="px-3 py-2.5 bg-surface-container-low text-on-surface-variant font-code-sm text-[13px] border-r border-outline-variant flex items-center">
                    +91
                  </span>
                  <input
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="98201 xxxxx"
                    maxLength={10}
                    required
                    className="flex-1 px-3 py-2.5 bg-surface-container-lowest text-on-surface font-body-md focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-colors shadow-2xs"
              >
                Send Verification OTP
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-space-md text-left pt-2">
              <div className="space-y-1">
                <label className="font-label-md text-label-md text-on-surface font-semibold">
                  Enter 6-Digit OTP
                </label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="1 2 3 4 5 6"
                  maxLength={6}
                  required
                  className="w-full text-center tracking-widest text-xl py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest font-code-sm focus:outline-none focus:border-primary"
                />
                <p className="font-body-sm text-[12px] text-on-surface-variant text-center">
                  OTP sent to +91 {phoneNumber}
                </p>
              </div>

              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-colors shadow-2xs"
              >
                Confirm & Continue
              </button>
            </form>
          )}

          <div className="pt-2 border-t border-outline-variant/60">
            <button
              type="button"
              onClick={handleDemoSignIn}
              className="w-full py-2.5 rounded-xl border border-outline-variant bg-surface-container-low hover:bg-surface-container text-on-surface font-label-md text-label-md font-semibold transition-colors flex items-center justify-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[18px] text-primary">login</span>
              <span>Quick Demo Guest Access</span>
            </button>
          </div>

          <div className="pt-1">
            <Link
              href="/admin/login"
              className="font-label-sm text-[12px] text-secondary font-bold hover:underline"
            >
              Auditor / Reviewer Portal Login →
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
