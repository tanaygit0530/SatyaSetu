'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { APP_CONFIG } from '@/lib/constants';
import { getUser, isAuthenticated, setToken, setUser, AuthUser } from '@/lib/auth';
import {
  changePhoneRequestOtp,
  changePhoneVerifyOtp,
  fetchCurrentUser,
  fetchWhatsAppLinkStatus,
  initiateWhatsAppLink,
  unlinkWhatsApp,
  WhatsAppLinkStatus,
} from '@/lib/api';
import { formatDate } from '@/lib/utils';

export default function WhatsAppPage() {
  const [currentUser, setCurrentUserState] = useState<AuthUser | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [linkStatus, setLinkStatus] = useState<WhatsAppLinkStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  // WhatsApp Linking Flow state
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkingLoading, setLinkingLoading] = useState(false);
  const [linkingData, setLinkingData] = useState<{
    linking_code: string;
    verified_phone_number: string;
    bot_number: string;
    deep_link: string;
    expires_in_seconds: number;
    is_sandbox: boolean;
    instructions: string;
  } | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);

  // Change phone state
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [countryCode, setCountryCode] = useState('+91');
  const [newPhone, setNewPhone] = useState('');
  const [changeOtpSent, setChangeOtpSent] = useState(false);
  const [changeOtp, setChangeOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initial load: retrieve authoritative authenticated profile and WhatsApp status
  useEffect(() => {
    const authed = isAuthenticated();
    setIsLoggedIn(authed);
    const cachedUser = getUser();
    setCurrentUserState(cachedUser);

    if (authed) {
      loadAuthoritativeStatus();
    }
  }, []);

  async function loadAuthoritativeStatus() {
    setStatusLoading(true);
    try {
      // 1. Fetch fresh authenticated profile from backend
      const meRes = await fetchCurrentUser();
      if (meRes?.user) {
        setUser(meRes.user);
        setCurrentUserState(meRes.user);
      }

      // 2. Fetch authoritative WhatsApp link status
      const statusRes = await fetchWhatsAppLinkStatus();
      setLinkStatus(statusRes);
    } catch (err) {
      console.error('Failed to load authoritative status:', err);
    } finally {
      setStatusLoading(false);
    }
  }

  // Cooldown countdown
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  // Polling for WhatsApp confirmation while linking modal is active
  useEffect(() => {
    if (!showLinkModal) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const freshStatus = await fetchWhatsAppLinkStatus();
        setLinkStatus(freshStatus);
        if (freshStatus.whatsapp_linked) {
          setShowLinkModal(false);
          setSuccessMsg('Your WhatsApp account has been linked successfully!');
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        }
      } catch (err) {
        console.error('Polling WhatsApp status notice:', err);
      }
    }, 3500);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [showLinkModal]);

  // Initiate WhatsApp linking flow
  const handleStartLinking = async () => {
    setError(null);
    setSuccessMsg(null);
    setLinkingLoading(true);
    try {
      const data = await initiateWhatsAppLink();
      setLinkingData(data);
      setShowLinkModal(true);
    } catch (err: any) {
      setError(err.message || 'Failed to start WhatsApp linking. Please try again.');
    } finally {
      setLinkingLoading(false);
    }
  };

  // Unlink WhatsApp
  const handleUnlink = async () => {
    if (!window.confirm('Are you sure you want to disconnect your WhatsApp account from SatyaSetu?')) {
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLinkingLoading(true);
    try {
      const res = await unlinkWhatsApp();
      setLinkStatus(res.status);
      setSuccessMsg('Your WhatsApp account has been disconnected.');
      // Refresh user profile
      const meRes = await fetchCurrentUser();
      if (meRes?.user) {
        setUser(meRes.user);
        setCurrentUserState(meRes.user);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to unlink WhatsApp account.');
    } finally {
      setLinkingLoading(false);
    }
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const getFullNewPhone = () => {
    const rawDigits = newPhone.trim().replace(/\D/g, '');
    const cleanCode = countryCode.trim().startsWith('+') ? countryCode.trim() : `+${countryCode.trim()}`;
    return `${cleanCode}${rawDigits}`;
  };

  const handleRequestChangeOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const fullPhone = getFullNewPhone();
    if (newPhone.trim().length < 7) {
      setError('Please enter a valid new phone number.');
      return;
    }

    setLoading(true);
    try {
      const res = await changePhoneRequestOtp(fullPhone);
      setChangeOtpSent(true);
      setCooldown(res.cooldown_seconds || 45);
      setSuccessMsg(res.message || 'Verification code sent to your new WhatsApp number.');
    } catch (err: any) {
      setError(err.message || 'Failed to send WhatsApp verification code.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChangeOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanCode = changeOtp.trim().replace(/\s/g, '');
    if (cleanCode.length !== 6) {
      setError('Please enter the 6-digit verification code.');
      return;
    }

    setLoading(true);
    try {
      const fullPhone = getFullNewPhone();
      const res = await changePhoneVerifyOtp(fullPhone, cleanCode);

      if (res.access_token) {
        setToken(res.access_token);
      }
      if (res.user) {
        setUser(res.user);
        setCurrentUserState(res.user);
      }

      setSuccessMsg('Your verified phone number has been updated successfully! Please link your new WhatsApp account.');
      setShowChangeModal(false);
      setChangeOtpSent(false);
      setNewPhone('');
      setChangeOtp('');
      await loadAuthoritativeStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to verify new phone number.');
    } finally {
      setLoading(false);
    }
  };

  // Authoritative user phone identity (strictly from backend authenticated profile)
  const userVerifiedNumber =
    currentUser?.phone_number || linkStatus?.verified_login_number || null;
  const isWhatsAppLinked = Boolean(linkStatus?.whatsapp_linked ?? currentUser?.whatsapp_linked);
  const botNumberDisplay = linkStatus?.bot_tipline_number || APP_CONFIG.whatsappNumber;
  const botDeepLink = linkStatus?.bot_deep_link || APP_CONFIG.whatsappDeepLink;

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-margin md:px-margin-desktop py-space-xl space-y-space-xl">
        {/* Header */}
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950 text-[#146336] dark:text-emerald-300 font-code-sm text-[12px] font-bold border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-[#1E8E4E]"></span>
            Official WhatsApp Verification Tipline
          </div>
          <h1 className="font-headline-xl text-3xl sm:text-4xl font-extrabold text-on-surface">
            Verify forwards where they already arrive.
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Forward any suspicious WhatsApp message, viral circular screenshot, or voice note to our verified tipline number. Receive a tamper-proof evidence dossier in seconds.
          </p>
        </div>

        {/* Global Feedback Messages */}
        {error && (
          <div className="p-3.5 rounded-xl bg-error-container/20 border border-error/40 text-error text-xs flex items-center justify-between gap-2 shadow-2xs">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] shrink-0">error</span>
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-error font-bold hover:underline">
              Dismiss
            </button>
          </div>
        )}

        {successMsg && !showChangeModal && !showLinkModal && (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 text-xs font-medium flex items-center justify-between gap-2 shadow-2xs">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-emerald-600">verified</span>
              <span>{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg(null)} className="font-bold hover:underline">
              Dismiss
            </button>
          </div>
        )}

        {/* USER ACCOUNT & VERIFIED WHATSAPP CONNECTION CARD */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg space-y-5 shadow-2xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-outline-variant">
            <div className="space-y-0.5">
              <h2 className="font-headline-sm text-lg font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[22px]">phonelink_lock</span>
                <span>Verified Account & WhatsApp Identity</span>
              </h2>
              <p className="text-xs text-on-surface-variant">
                Your authenticated login profile and connected WhatsApp citizen identity
              </p>
            </div>

            {isLoggedIn ? (
              <button
                onClick={() => {
                  setShowChangeModal(!showChangeModal);
                  setError(null);
                  setSuccessMsg(null);
                }}
                className="px-3.5 py-1.5 rounded-xl border border-outline-variant hover:bg-surface-container-low text-xs font-bold text-on-surface transition-colors flex items-center gap-1.5 self-start sm:self-auto"
              >
                <span className="material-symbols-outlined text-[16px]">phone_iphone</span>
                <span>{showChangeModal ? 'Cancel Change' : 'Change Login Number'}</span>
              </button>
            ) : (
              <Link
                href="/login"
                className="px-3.5 py-1.5 rounded-xl bg-primary text-on-primary text-xs font-bold transition-colors flex items-center gap-1.5 self-start sm:self-auto"
              >
                <span className="material-symbols-outlined text-[16px]">login</span>
                <span>Log in to Link Account</span>
              </Link>
            )}
          </div>

          {/* TWO PRIMARY NUMBER COLUMNS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 1. Verified Login Number */}
            <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/60 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-outline uppercase text-[10px] font-bold tracking-wider">
                  Verified Login Number
                </span>
                {isLoggedIn && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-500/15 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    <span className="material-symbols-outlined text-[12px]">check_circle</span>
                    Twilio Verified
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {isLoggedIn ? (
                  <div className="space-y-0.5">
                    <span className="font-code-sm text-base font-bold text-on-surface">
                      {userVerifiedNumber || 'Loading verified number...'}
                    </span>
                    <p className="text-[11px] text-on-surface-variant">
                      Authenticated through Twilio Verify WhatsApp OTP
                    </p>
                  </div>
                ) : (
                  <span className="text-on-surface-variant text-xs italic">
                    Not signed in.{' '}
                    <Link href="/login" className="text-primary underline font-semibold">
                      Sign in
                    </Link>{' '}
                    to access your verified number.
                  </span>
                )}
              </div>
            </div>

            {/* 2. WhatsApp Account Identity (MUST MATCH THE USER'S VERIFIED NUMBER) */}
            <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/60 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-outline uppercase text-[10px] font-bold tracking-wider">
                  WhatsApp Account Identity
                </span>
                {isLoggedIn && (
                  <span
                    className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      isWhatsAppLinked
                        ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/15 border-emerald-500/20'
                        : 'text-amber-800 dark:text-amber-300 bg-amber-500/15 border-amber-500/20'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[12px]">
                      {isWhatsAppLinked ? 'link' : 'link_off'}
                    </span>
                    {isWhatsAppLinked ? 'Linked & Synchronized' : 'Not Connected Yet'}
                  </span>
                )}
              </div>

              <div className="space-y-1">
                {isLoggedIn ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="font-code-sm text-base font-bold text-on-surface">
                        {userVerifiedNumber || 'Loading identity...'}
                      </span>
                    </div>

                    {isWhatsAppLinked ? (
                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                        <p className="text-[11px] text-emerald-700 dark:text-emerald-300">
                          {linkStatus?.whatsapp_linked_at
                            ? `Confirmed on ${formatDate(linkStatus.whatsapp_linked_at)}`
                            : 'All incoming forwards automatically map to your dashboard.'}
                        </p>
                        <button
                          onClick={handleUnlink}
                          disabled={linkingLoading}
                          className="text-[11px] font-bold text-error hover:underline transition-colors"
                        >
                          Disconnect
                        </button>
                      </div>
                    ) : (
                      <div className="pt-1.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <p className="text-[11px] text-on-surface-variant max-w-xs">
                          Connect this WhatsApp identity to sync forwards with your personal dashboard.
                        </p>
                        <button
                          onClick={handleStartLinking}
                          disabled={linkingLoading}
                          className="px-3 py-1.5 rounded-xl bg-primary hover:bg-primary-container text-on-primary text-xs font-bold transition-colors flex items-center gap-1 shrink-0 self-start sm:self-auto"
                        >
                          {linkingLoading ? (
                            <span className="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>
                          ) : (
                            <span className="material-symbols-outlined text-[14px]">add_link</span>
                          )}
                          <span>Connect WhatsApp</span>
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <span className="text-on-surface-variant text-xs italic">
                    Log in with your mobile number to connect your WhatsApp tipline forwards.
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* ACTIVE LINKING INSTRUCTION MODAL / CARD */}
          {showLinkModal && linkingData && (
            <div className="p-4 sm:p-5 rounded-xl border border-primary/30 bg-primary/5 space-y-4 transition-all">
              <div className="flex items-center justify-between border-b border-primary/20 pb-2">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">mark_chat_unread</span>
                  <h3 className="text-sm font-bold text-on-surface">
                    Confirm WhatsApp Account Ownership
                  </h3>
                </div>
                <button
                  onClick={() => setShowLinkModal(false)}
                  className="text-xs text-on-surface-variant hover:text-on-surface font-semibold"
                >
                  Close
                </button>
              </div>

              <p className="text-xs text-on-surface-variant leading-relaxed">
                To guarantee that you control the WhatsApp account for <strong>{userVerifiedNumber}</strong>,
                please send the single-use linking code to our official bot from that number.
              </p>

              {/* Code Box */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-3 rounded-xl bg-surface-container-lowest border border-outline-variant">
                <div className="flex-1 space-y-1">
                  <span className="text-[10px] text-outline uppercase font-bold tracking-wider">
                    Single-Use Confirmation Code (Valid for 10m)
                  </span>
                  <div className="font-code-sm text-lg font-extrabold text-primary tracking-wider">
                    {linkingData.linking_code}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyCode(linkingData.linking_code)}
                    className="px-3 py-2 rounded-lg border border-outline-variant hover:bg-surface-container-low text-xs font-bold text-on-surface flex items-center gap-1.5"
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {copiedCode ? 'check' : 'content_copy'}
                    </span>
                    <span>{copiedCode ? 'Copied' : 'Copy Code'}</span>
                  </button>

                  <a
                    href={linkingData.deep_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 rounded-lg bg-[#1E8E4E] hover:bg-[#146336] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
                  >
                    <span className="material-symbols-outlined text-[16px]">send</span>
                    <span>Send Code in WhatsApp</span>
                  </a>
                </div>
              </div>

              {/* Live Polling Alert */}
              <div className="flex items-center gap-2.5 text-xs text-on-surface-variant pt-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span>
                <span>
                  Waiting for incoming confirmation from <strong>{userVerifiedNumber}</strong>...
                  This page will update automatically once verified.
                </span>
              </div>

              {linkingData.is_sandbox && (
                <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-[11px]">
                  <strong>Twilio Sandbox Mode Notice:</strong> If this is your first time messaging this Twilio sandbox bot,
                  you must first send your sandbox join phrase (e.g. <code>join &lt;keyword&gt;</code>) to the bot, then send{' '}
                  <code>{linkingData.linking_code}</code>.
                </div>
              )}
            </div>
          )}

          {/* CHANGE PHONE NUMBER SUB-FORM */}
          {showChangeModal && (
            <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 space-y-3 mt-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-on-surface flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-primary text-[18px]">update</span>
                  <span>Update Account Phone Number via WhatsApp OTP</span>
                </h3>
              </div>
              <p className="text-xs text-on-surface-variant">
                We will send an OTP via Twilio Verify to your new WhatsApp number. Your past verification history and analytics will remain securely attached to your account.
              </p>

              {!changeOtpSent ? (
                <form onSubmit={handleRequestChangeOtp} className="space-y-3">
                  <div className="flex rounded-xl border border-outline-variant overflow-hidden bg-surface-container-lowest max-w-md">
                    <select
                      value={countryCode}
                      onChange={(e) => setCountryCode(e.target.value)}
                      className="px-2.5 py-2 bg-surface-container-low text-on-surface text-xs border-r border-outline-variant focus:outline-none"
                    >
                      <option value="+91">🇮🇳 +91</option>
                      <option value="+1">🇺🇸 +1</option>
                      <option value="+44">🇬🇧 +44</option>
                      <option value="+971">🇦🇪 +971</option>
                    </select>
                    <input
                      type="tel"
                      value={newPhone}
                      onChange={(e) => setNewPhone(e.target.value)}
                      placeholder="New WhatsApp Number"
                      required
                      disabled={loading}
                      className="flex-1 px-3 py-2 text-xs bg-surface-container-lowest text-on-surface focus:outline-none"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 rounded-xl bg-primary hover:bg-primary-container text-on-primary text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                        <span>Sending OTP...</span>
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-[16px]">send</span>
                        <span>Send WhatsApp OTP to New Number</span>
                      </>
                    )}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyChangeOtp} className="space-y-3">
                  <div className="max-w-md space-y-1.5">
                    <label className="text-xs font-semibold text-on-surface">
                      Enter 6-digit OTP sent to {getFullNewPhone()}
                    </label>
                    <input
                      type="text"
                      value={changeOtp}
                      onChange={(e) => setChangeOtp(e.target.value.replace(/\D/g, ''))}
                      placeholder="123456"
                      maxLength={6}
                      required
                      disabled={loading}
                      autoFocus
                      className="w-full text-center tracking-[0.4em] text-lg py-2 rounded-xl border border-outline-variant bg-surface-container-lowest font-code-sm focus:outline-none focus:border-primary"
                    />
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="submit"
                      disabled={loading || changeOtp.trim().length !== 6}
                      className="px-4 py-2 rounded-xl bg-primary hover:bg-primary-container text-on-primary text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {loading ? (
                        <>
                          <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                          <span>Verifying...</span>
                        </>
                      ) : (
                        <>
                          <span className="material-symbols-outlined text-[16px]">check</span>
                          <span>Confirm & Update Number</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      disabled={cooldown > 0 || loading}
                      onClick={() => handleRequestChangeOtp()}
                      className="text-xs text-primary font-semibold hover:underline disabled:text-outline disabled:no-underline"
                    >
                      {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Code'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>

        {/* SATYASETU BOT TIPLINE ACTION BOX (SEPARATE & EXPLICITLY LABELED) */}
        <div className="rounded-2xl bg-surface-container-lowest border border-outline-variant p-space-lg md:p-space-xl grid grid-cols-1 md:grid-cols-2 gap-space-lg items-center shadow-sm">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-code-sm text-[11px] font-bold border border-outline-variant">
                <span className="material-symbols-outlined text-[14px] text-primary">smart_toy</span>
                <span>Official SatyaSetu Bot Tipline Number</span>
              </div>
              <h2 className="font-headline-lg text-2xl sm:text-3xl font-extrabold text-on-surface">
                {botNumberDisplay}
              </h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                This is the civic bot tipline number you send rumors to. Available 24/7 across India in Hindi, Marathi, and English.
              </p>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row gap-3">
              <a
                href={botDeepLink}
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

            {/* SatyaSetu Bot Reply */}
            <div className="bg-[#EAF6EE] rounded-lg p-2.5 rounded-tl-none shadow-xs max-w-[90%] border border-[#B8E4C8] space-y-1.5 font-sans">
              <div className="flex items-center gap-1 text-[#146336] font-bold text-[13px]">
                <span>🔴 FALSE</span>
              </div>
              <p className="text-slate-800 text-[12px] font-medium">
                "Education Ministry giving ₹50,000 scholarship cash grant."
              </p>
              <div className="text-[12px] text-slate-700">
                <strong>Why:</strong>
                <p>No reliable official evidence supports this. Genuine scholarship amount is ₹12,000/yr on scholarships.gov.in.</p>
              </div>
              <div className="pt-1 border-t border-[#B8E4C8]/60 flex items-center justify-between text-[11px] text-[#146336] font-semibold">
                <span>View Full Evidence Proof:</span>
                <span className="underline">satyasetu.in/c/chk_example</span>
              </div>
              <div className="text-right text-[10px] text-slate-400">09:42 AM • SatyaSetu Bot</div>
            </div>
          </div>
        </div>

        {/* 3 Step Instructions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md pt-2">
          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
            <span className="font-code-sm text-primary font-bold text-[14px]">STEP 01</span>
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Save the Tipline Contact
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Save {botNumberDisplay} in your phone contacts as &quot;SatyaSetu Civic Tipline&quot;.
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
            <span className="font-code-sm text-primary font-bold text-[14px]">STEP 02</span>
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Forward Any Message
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Forward unverified WhatsApp messages, images, PDF circulars, or voice memos directly to the tipline.
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant space-y-2">
            <span className="font-code-sm text-primary font-bold text-[14px]">STEP 03</span>
            <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
              Receive Proof Card
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Get an instant verdict with official citations. If linked, it appears in your personal dashboard.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
