'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { InputType } from '@/types';
import { submitTextCheck, uploadMediaCheck, submitUrlCheck } from '@/lib/api';

interface InputTabsProps {
  initialType?: InputType;
  onSubmitted?: (inputType: InputType, content: string) => void;
}

export function InputTabs({ initialType = 'TEXT', onSubmitted }: InputTabsProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<InputType>(initialType);
  const [textInput, setTextInput] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const sampleForwards = [
    'Is UPI was developed by NPCI?',
    'IMPS is available 24 hours a day.',
    "India's national animal is the Bengal tiger.",
  ];

  const handleQuickSample = (sample: string) => {
    setTextInput(sample);
    setErrorMessage(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const handleStartVerification = async () => {
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      let createdCheckId = '';

      if (activeTab === 'TEXT') {
        const trimmed = textInput.trim();
        if (!trimmed) {
          setErrorMessage('Please enter or paste the claim or forward text to verify.');
          setIsSubmitting(false);
          return;
        }
        const resp = await submitTextCheck(trimmed, 'TEXT');
        createdCheckId = resp.check_id;
        if (onSubmitted) onSubmitted('TEXT', trimmed);

      } else if (activeTab === 'LINK') {
        const trimmed = urlInput.trim();
        if (!trimmed) {
          setErrorMessage('Please enter a valid web URL to check.');
          setIsSubmitting(false);
          return;
        }
        const resp = await submitUrlCheck(trimmed);
        createdCheckId = resp.check_id;
        if (onSubmitted) onSubmitted('LINK', trimmed);

      } else if (activeTab === 'SCREENSHOT') {
        if (!selectedFile) {
          setErrorMessage('Please select a screenshot image file (PNG/JPG).');
          setIsSubmitting(false);
          return;
        }
        const resp = await uploadMediaCheck(selectedFile, 'SCREENSHOT');
        createdCheckId = resp.check_id;
        if (onSubmitted) onSubmitted('SCREENSHOT', selectedFile.name);

      } else if (activeTab === 'VOICE') {
        if (!selectedFile) {
          setErrorMessage('Please upload an audio recording file (MP3/OGG/WAV).');
          setIsSubmitting(false);
          return;
        }
        const resp = await uploadMediaCheck(selectedFile, 'VOICE');
        createdCheckId = resp.check_id;
        if (onSubmitted) onSubmitted('VOICE', selectedFile.name);

      } else if (activeTab === 'PDF') {
        if (!selectedFile) {
          setErrorMessage('Please select an official PDF circular or document.');
          setIsSubmitting(false);
          return;
        }
        const resp = await uploadMediaCheck(selectedFile, 'PDF');
        createdCheckId = resp.check_id;
        if (onSubmitted) onSubmitted('PDF', selectedFile.name);
      }

      if (createdCheckId) {
        router.push(`/check/${createdCheckId}/processing`);
      } else {
        throw new Error('No check ID was returned by the verification backend.');
      }
    } catch (err: any) {
      console.error('Submission failed:', err);
      setErrorMessage(err?.message || 'Verification service request failed. Please check backend connection.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-sm overflow-hidden">
      {/* 5 Input Tabs Header */}
      <div className="grid grid-cols-5 border-b border-outline-variant bg-surface-container-low text-center">
        {[
          { type: 'TEXT' as InputType, label: 'Text', icon: 'notes' },
          { type: 'SCREENSHOT' as InputType, label: 'Screenshot', icon: 'photo_camera' },
          { type: 'VOICE' as InputType, label: 'Voice Memo', icon: 'mic' },
          { type: 'PDF' as InputType, label: 'PDF Notice', icon: 'picture_as_pdf' },
          { type: 'LINK' as InputType, label: 'Web Link', icon: 'link' },
        ].map((tab) => {
          const isActive = activeTab === tab.type;
          return (
            <button
              key={tab.type}
              type="button"
              onClick={() => {
                setActiveTab(tab.type);
                setErrorMessage(null);
              }}
              className={`py-3.5 px-2 flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2 font-label-md text-label-md transition-colors relative ${
                isActive
                  ? 'bg-surface-container-lowest text-primary font-bold shadow-xs'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
              }`}
            >
              <span className={`material-symbols-outlined text-[20px] ${isActive ? 'text-primary' : ''}`}>
                {tab.icon}
              </span>
              <span className="text-[12px] sm:text-[14px]">{tab.label}</span>
              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
              )}
            </button>
          );
        })}
      </div>

      {/* Hidden File Input for Image/Audio/PDF uploads */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
        accept={
          activeTab === 'SCREENSHOT'
            ? 'image/png,image/jpeg,image/webp'
            : activeTab === 'VOICE'
            ? 'audio/mpeg,audio/ogg,audio/wav,audio/mp4'
            : activeTab === 'PDF'
            ? 'application/pdf'
            : '*/*'
        }
      />

      {/* Tab Content Panels */}
      <div className="p-space-md md:p-space-lg space-y-space-md">
        {/* Error notification banner if any */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-error-container/20 border border-error/30 text-error flex items-start gap-2 text-body-sm">
            <span className="material-symbols-outlined text-[18px] shrink-0 mt-0.5">error</span>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* TAB 1: TEXT */}
        {activeTab === 'TEXT' && (
          <div className="space-y-space-md">
            <div className="space-y-1">
              <label className="font-label-md text-label-md text-on-surface font-semibold flex items-center justify-between">
                <span>Paste forwarded WhatsApp message, circular text, or claim:</span>
                <span className="font-code-sm text-[11px] text-on-surface-variant">
                  {textInput.length}/4000 characters
                </span>
              </label>
              <textarea
                value={textInput}
                onChange={(e) => {
                  setTextInput(e.target.value);
                  if (errorMessage) setErrorMessage(null);
                }}
                placeholder="e.g. UPI was developed by NPCI."
                className="w-full h-36 p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant font-serif text-[15px] sm:text-[16px] text-on-surface placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-none"
              />
            </div>

            {/* Quick Sample Forward Buttons */}
            <div className="space-y-1.5">
              <span className="font-label-sm text-[11px] text-on-surface-variant font-bold uppercase tracking-wider">
                Try verified test claim:
              </span>
              <div className="flex flex-wrap gap-2">
                {sampleForwards.map((sample, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleQuickSample(sample)}
                    className="text-left px-2.5 py-1 rounded-lg bg-surface-container-low hover:bg-surface-container border border-outline-variant font-body-sm text-[12px] text-on-surface-variant hover:text-on-surface transition-colors"
                  >
                    "{sample}"
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SCREENSHOT */}
        {activeTab === 'SCREENSHOT' && (
          <div className="space-y-space-md">
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-outline-variant hover:border-primary/60 rounded-xl p-space-xl text-center bg-surface-container-low/40 transition-colors cursor-pointer"
            >
              <div className="max-w-md mx-auto space-y-3">
                <div className="w-12 h-12 rounded-full bg-primary-fixed text-primary flex items-center justify-center mx-auto">
                  <span className="material-symbols-outlined text-[28px]">add_photo_alternate</span>
                </div>
                <div>
                  <h4 className="font-label-md text-label-md font-bold text-on-surface">
                    Upload Forwarded Screenshot
                  </h4>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                    Click to browse or drop image. Supported formats: PNG, JPG, WebP.
                  </p>
                </div>
                <div className="pt-2 flex justify-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold hover:bg-primary-container"
                  >
                    Select Screenshot File
                  </button>
                </div>
                {selectedFile && (
                  <p className="font-code-sm text-[12px] text-tertiary font-bold mt-2">
                    ✓ Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: VOICE MEMO */}
        {activeTab === 'VOICE' && (
          <div className="space-y-space-md">
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-outline-variant hover:border-primary/60 rounded-xl p-space-xl text-center bg-surface-container-low/40 transition-colors cursor-pointer"
            >
              <div className="max-w-md mx-auto space-y-3">
                <div className="w-12 h-12 rounded-full bg-primary-fixed text-primary flex items-center justify-center mx-auto">
                  <span className="material-symbols-outlined text-[28px]">mic</span>
                </div>
                <div>
                  <h4 className="font-label-md text-label-md font-bold text-on-surface">
                    Upload Audio Note or Voice Memo
                  </h4>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                    Transcribes vernacular Hindi, Marathi, or Indian English speech directly to text.
                  </p>
                </div>
                <div className="pt-2 flex justify-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold hover:bg-primary-container"
                  >
                    Select Audio File (MP3/OGG/WAV)
                  </button>
                </div>
                {selectedFile && (
                  <p className="font-code-sm text-[12px] text-tertiary font-bold mt-2">
                    ✓ Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: PDF */}
        {activeTab === 'PDF' && (
          <div className="space-y-space-md">
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-outline-variant hover:border-primary/60 rounded-xl p-space-xl text-center bg-surface-container-low/40 transition-colors cursor-pointer"
            >
              <div className="max-w-md mx-auto space-y-3">
                <div className="w-12 h-12 rounded-full bg-primary-fixed text-primary flex items-center justify-center mx-auto">
                  <span className="material-symbols-outlined text-[28px]">picture_as_pdf</span>
                </div>
                <div>
                  <h4 className="font-label-md text-label-md font-bold text-on-surface">
                    Upload Official PDF Circular or Gazette
                  </h4>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                    Multi-page PDF parsing with stamp detection and table extraction.
                  </p>
                </div>
                <div className="pt-2 flex justify-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold hover:bg-primary-container"
                  >
                    Select PDF File
                  </button>
                </div>
                {selectedFile && (
                  <p className="font-code-sm text-[12px] text-tertiary font-bold mt-2">
                    ✓ Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: LINK */}
        {activeTab === 'LINK' && (
          <div className="space-y-space-md">
            <div className="space-y-1">
              <label className="font-label-md text-label-md text-on-surface font-semibold">
                Web Link or Social Forward URL
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[20px]">
                  link
                </span>
                <input
                  type="url"
                  value={urlInput}
                  onChange={(e) => {
                    setUrlInput(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder="https://pib.gov.in/PressReleasePage.aspx?PRID=... or news link"
                  className="w-full h-11 pl-10 pr-4 rounded-xl bg-surface-container-lowest border border-outline-variant font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </div>
              <p className="font-body-sm text-[12px] text-on-surface-variant">
                Scrapes public metadata, verifies domain authenticity, and validates claims.
              </p>
            </div>
          </div>
        )}

        {/* Action Button & Disclaimer Bar */}
        <div className="pt-space-sm border-t border-outline-variant flex flex-col sm:flex-row items-center justify-between gap-space-md">
          <div className="flex items-center gap-2 text-on-surface-variant font-code-sm text-[12px]">
            <span className="material-symbols-outlined text-primary text-[16px]">security</span>
            <span>Zero personal tracking • Real-time statutory verification</span>
          </div>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleStartVerification}
            className={`w-full sm:w-auto px-6 py-2.5 rounded-xl bg-primary text-on-primary font-label-md text-label-md font-bold flex items-center justify-center gap-2 shadow-sm transition-colors ${
              isSubmitting
                ? 'opacity-70 cursor-not-allowed'
                : 'hover:bg-primary-container'
            }`}
          >
            {isSubmitting ? (
              <>
                <span className="w-4 h-4 border-2 border-on-primary border-t-transparent rounded-full animate-spin"></span>
                <span>Connecting to Engine...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">verified_user</span>
                <span>Verify with Evidence</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
