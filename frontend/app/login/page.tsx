'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { requestOtp, verifyOtp } from '@/lib/api';
import { setToken, setUser, isAuthenticated } from '@/lib/auth';

export default function LoginPage() {
  const router = useRouter();

  const [countryCode, setCountryCode] = useState('+91');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  // Resend cooldown timer
  const [cooldown, setCooldown] = useState<number>(0);

  useEffect(() => {
    // If already authenticated, redirect straight to user dashboard
    if (isAuthenticated()) {
      router.replace('/dashboard');
    }
  }, [router]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const getFullPhone = () => {
    const rawDigits = phoneNumber.trim().replace(/\D/g, '');
    const cleanCode = countryCode.trim().startsWith('+') ? countryCode.trim() : `+${countryCode.trim()}`;
    return `${cleanCode}${rawDigits}`;
  };

  const handleSendOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);
    setInfoMessage(null);

    const fullPhone = getFullPhone();
    if (phoneNumber.trim().length < 7) {
      setError('Please enter a valid phone number.');
      return;
    }

    setLoading(true);
    try {
      const res = await requestOtp(fullPhone);
      setOtpSent(true);
      setCooldown(res.cooldown_seconds || 45);
      setInfoMessage(res.message || 'Verification code sent via WhatsApp.');
    } catch (err: any) {
      setError(err.message || 'Failed to send WhatsApp verification code.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);

    const cleanOtp = otp.trim().replace(/\s/g, '');
    if (cleanOtp.length !== 6) {
      setError('Please enter the 6-digit verification code.');
      return;
    }

    setLoading(true);
    try {
      const fullPhone = getFullPhone();
      const res = await verifyOtp(fullPhone, cleanOtp);

      if (res.access_token) {
        setToken(res.access_token);
        if (res.user) {
          setUser(res.user);
        }
        router.push('/dashboard');
      } else {
        setError('Verification succeeded but no session token was received.');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid or expired verification code.');
    } finally {
      setLoading(false);
    }
  };

  const handleEditPhone = () => {
    setOtpSent(false);
    setOtp('');
    setError(null);
    setInfoMessage(null);
  };

  return (
    <AppShell showFooter={false}>
      <div className="max-w-md mx-auto px-margin py-space-2xl space-y-space-lg">
        {/* Card Container */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl space-y-space-md shadow-sm text-center">
          {/* SatyaSetu Emblem */}
          <div className="w-14 h-14 rounded-2xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center mx-auto shadow-xs">
            <span className="material-symbols-outlined text-[32px]">verified_user</span>
          </div>

          <div className="space-y-1">
            <h1 className="font-headline-lg text-2xl font-bold text-on-surface">
              SatyaSetu Login
            </h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Unified citizen verification login via official WhatsApp OTP.
            </p>
          </div>

          {/* Feedback alerts */}
          {error && (
            <div className="rounded-xl bg-error-container/20 border border-error/40 p-3 text-left flex items-start gap-2.5">
              <span className="material-symbols-outlined text-error text-[20px] shrink-0 mt-0.5">
                error
              </span>
              <div className="text-error text-body-sm text-xs leading-relaxed font-medium">
                {error}
              </div>
            </div>
          )}

          {infoMessage && (
            <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-3 text-left flex items-start gap-2.5">
              <span className="material-symbols-outlined text-emerald-600 text-[20px] shrink-0 mt-0.5">
                mark_chat_read
              </span>
              <div className="text-emerald-700 dark:text-emerald-300 text-body-sm text-xs leading-relaxed font-medium">
                {infoMessage}
              </div>
            </div>
          )}

          {!otpSent ? (
            <form onSubmit={handleSendOtp} className="space-y-space-md text-left pt-2">
              <div className="space-y-1.5">
                <label className="font-label-md text-label-md text-on-surface font-semibold flex items-center justify-between">
                  <span>Phone Number</span>
                  <span className="text-[11px] text-on-surface-variant font-normal">WhatsApp Enabled</span>
                </label>
                <div className="flex rounded-xl border border-outline-variant overflow-hidden focus-within:border-primary focus-within:ring-1 focus-within:ring-primary bg-surface-container-lowest">
                  <select
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    className="px-2.5 py-2.5 bg-surface-container-low text-on-surface font-code-sm text-[13px] border-r border-outline-variant focus:outline-none cursor-pointer"
                  >
                    <option value="+91">🇮🇳 +91</option>
                    <option value="+1">🇺🇸 +1</option>
                    <option value="+44">🇬🇧 +44</option>
                    <option value="+971">🇦🇪 +971</option>
                    <option value="+65">🇸🇬 +65</option>
                  </select>
                  <input
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="98201 23456"
                    maxLength={15}
                    required
                    disabled={loading}
                    className="flex-1 px-3 py-2.5 bg-surface-container-lowest text-on-surface font-body-md focus:outline-none placeholder:text-outline"
                  />
                </div>
                <p className="text-[11px] text-on-surface-variant">
                  We will send a one-time 6-digit code to your WhatsApp number via Twilio Verify.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-all shadow-xs flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                    <span>Sending Code...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[18px]">send</span>
                    <span>Send WhatsApp OTP</span>
                  </>
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-space-md text-left pt-2">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="font-label-md text-label-md text-on-surface font-semibold">
                    Enter 6-Digit WhatsApp OTP
                  </label>
                  <button
                    type="button"
                    onClick={handleEditPhone}
                    className="text-[12px] text-primary hover:underline font-semibold"
                  >
                    Edit Number
                  </button>
                </div>

                <div className="px-3 py-2 rounded-lg bg-surface-container-low border border-outline-variant/60 flex items-center justify-between text-xs text-on-surface-variant">
                  <span className="font-code-sm">{getFullPhone()}</span>
                  <span className="flex items-center gap-1 text-emerald-600 font-medium">
                    <span className="material-symbols-outlined text-[14px]">chat</span> WhatsApp
                  </span>
                </div>

                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  maxLength={6}
                  required
                  disabled={loading}
                  autoFocus
                  className="w-full text-center tracking-[0.5em] text-2xl py-3 rounded-xl border border-outline-variant bg-surface-container-lowest font-code-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder:tracking-normal placeholder:text-outline"
                />
              </div>

              <button
                type="submit"
                disabled={loading || otp.trim().length !== 6}
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold transition-all shadow-xs flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                    <span>Verifying Code...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[18px]">check_circle</span>
                    <span>Confirm & Enter Dashboard</span>
                  </>
                )}
              </button>

              <div className="pt-2 flex items-center justify-between text-xs text-on-surface-variant">
                <span>Didn't receive code?</span>
                <button
                  type="button"
                  disabled={cooldown > 0 || loading}
                  onClick={() => handleSendOtp()}
                  className="text-primary font-semibold hover:underline disabled:text-outline disabled:no-underline"
                >
                  {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend OTP'}
                </button>
              </div>
            </form>
          )}

          <div className="pt-4 border-t border-outline-variant/50 text-center">
            <p className="text-[12px] text-on-surface-variant">
              By logging in, you verify adherence to the SatyaSetu Misinformation Combat & Fact-Checking Framework.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
