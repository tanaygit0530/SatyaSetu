'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { InputType } from '@/types';

interface InputTabsProps {
  initialType?: InputType;
  onSubmitted?: (inputType: InputType, content: string) => void;
}

export function InputTabs({ initialType = 'TEXT', onSubmitted }: InputTabsProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<InputType>(initialType);
  const [textInput, setTextInput] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

  const sampleForwards = [
    'URGENT: Ministry of Education offers ₹50,000 scholarship on pmssy-gov.in',
    'Railway board orders total suspension of trains from midnight',
    'RBI declares 10-rupee coins without symbol invalid for bank deposits',
  ];

  const handleQuickSample = (sample: string) => {
    setTextInput(sample);
  };

  const handleStartVerification = () => {
    const targetCheckId = 'SC-2026-8941';
    if (onSubmitted) {
      onSubmitted(activeTab, textInput || urlInput || uploadedFileName || 'sample');
    }
    router.push(`/check/${targetCheckId}/processing`);
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
              onClick={() => setActiveTab(tab.type)}
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

      {/* Tab Content Panels */}
      <div className="p-space-md md:p-space-lg space-y-space-md">
        {/* TAB 1: TEXT */}
        {activeTab === 'TEXT' && (
          <div className="space-y-space-md">
            <div className="space-y-1">
              <label className="font-label-md text-label-md text-on-surface font-semibold flex items-center justify-between">
                <span>Paste forwarded WhatsApp message, circular text, or SMS:</span>
                <span className="font-code-sm text-[11px] text-on-surface-variant">
                  {textInput.length}/4000 characters
                </span>
              </label>
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="e.g. URGENT FORWARD: Ministry of Education has launched Prime Minister Special Higher Merit Scholarship for 2026-27 batch. Every student will get ₹50,000 cash grant..."
                className="w-full h-36 p-space-md rounded-xl bg-surface-container-lowest border border-outline-variant font-serif text-[15px] sm:text-[16px] text-on-surface placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-none"
              />
            </div>

            {/* Quick Sample Forward Buttons */}
            <div className="space-y-1.5">
              <span className="font-label-sm text-[11px] text-on-surface-variant font-bold uppercase tracking-wider">
                Try verified test forward:
              </span>
              <div className="flex flex-wrap gap-2">
                {sampleForwards.map((sample, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleQuickSample(sample)}
                    className="text-left px-2.5 py-1 rounded-lg bg-surface-container-low hover:bg-surface-container border border-outline-variant font-body-sm text-[12px] text-on-surface-variant hover:text-on-surface transition-colors"
                  >
                    "{sample.slice(0, 48)}..."
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SCREENSHOT */}
        {activeTab === 'SCREENSHOT' && (
          <div className="space-y-space-md">
            <div className="border-2 border-dashed border-outline-variant hover:border-primary/60 rounded-xl p-space-xl text-center bg-surface-container-low/40 transition-colors cursor-pointer">
              <div className="max-w-md mx-auto space-y-3">
                <div className="w-12 h-12 rounded-full bg-primary-fixed text-primary flex items-center justify-center mx-auto">
                  <span className="material-symbols-outlined text-[28px]">add_photo_alternate</span>
                </div>
                <div>
                  <h4 className="font-label-md text-label-md font-bold text-on-surface">
                    Upload Forwarded Screenshot
                  </h4>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                    Drag and drop image or browse device. Supported formats: PNG, JPG, WebP up to 15MB.
                  </p>
                </div>
                <div className="pt-2 flex justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => setUploadedFileName('whatsapp_circular_forward_2026.png')}
                    className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold hover:bg-primary-container"
                  >
                    Select Image File
                  </button>
                  <button
                    type="button"
                    onClick={() => setUploadedFileName('pm_merit_scholarship_screenshot.png')}
                    className="px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface font-label-sm text-label-sm hover:bg-surface-container-low"
                  >
                    Load Sample Circular
                  </button>
                </div>
                {uploadedFileName && (
                  <p className="font-code-sm text-[12px] text-tertiary font-bold mt-2">
                    ✓ Attached: {uploadedFileName}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: VOICE MEMO */}
        {activeTab === 'VOICE' && (
          <div className="space-y-space-md">
            <div className="border border-outline-variant rounded-xl p-space-lg bg-surface-container-low/30 text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-surface-container-high mx-auto flex items-center justify-center text-primary">
                <span className={`material-symbols-outlined text-[32px] ${isRecording ? 'text-error animate-pulse' : ''}`}>
                  mic
                </span>
              </div>
              <div>
                <h4 className="font-label-md text-label-md font-bold text-on-surface">
                  {isRecording ? 'Listening & Transcribing Voice Memo...' : 'Upload or Record Audio Note'}
                </h4>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                  Transcribes vernacular Hindi, Marathi, or Indian English speech directly to text.
                </p>
              </div>
              <div className="flex justify-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsRecording(!isRecording)}
                  className={`px-4 py-2 rounded-lg font-label-md text-label-md font-semibold transition-colors flex items-center gap-2 ${
                    isRecording
                      ? 'bg-error text-on-error'
                      : 'bg-primary text-on-primary hover:bg-primary-container'
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {isRecording ? 'stop' : 'radio_button_checked'}
                  </span>
                  <span>{isRecording ? 'Stop Recording' : 'Record Audio Note'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setUploadedFileName('forwarded_voice_memo_ward14.mp3')}
                  className="px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface font-label-sm text-label-sm"
                >
                  Upload Audio (MP3/OGG)
                </button>
              </div>
              {uploadedFileName && (
                <p className="font-code-sm text-[12px] text-tertiary font-bold">
                  ✓ Attached: {uploadedFileName}
                </p>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: PDF */}
        {activeTab === 'PDF' && (
          <div className="space-y-space-md">
            <div className="border-2 border-dashed border-outline-variant hover:border-primary/60 rounded-xl p-space-xl text-center bg-surface-container-low/40">
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
                    onClick={() => setUploadedFileName('Gazette_Notification_MoE_2026.pdf')}
                    className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold hover:bg-primary-container"
                  >
                    Select PDF File
                  </button>
                </div>
                {uploadedFileName && (
                  <p className="font-code-sm text-[12px] text-tertiary font-bold mt-2">
                    ✓ Attached: {uploadedFileName}
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
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://pmssy-gov.in/scholarship-form or news URL"
                  className="w-full h-11 pl-10 pr-4 rounded-xl bg-surface-container-lowest border border-outline-variant font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </div>
              <p className="font-body-sm text-[12px] text-on-surface-variant">
                Scrapes public metadata, domain WHOIS records, and verifies authenticity against CERT-In registry.
              </p>
            </div>
          </div>
        )}

        {/* Action Button & Disclaimer Bar */}
        <div className="pt-space-sm border-t border-outline-variant flex flex-col sm:flex-row items-center justify-between gap-space-md">
          <div className="flex items-center gap-2 text-on-surface-variant font-code-sm text-[12px]">
            <span className="material-symbols-outlined text-primary text-[16px]">security</span>
            <span>Zero personal tracking • Immediate cryptographic hashing</span>
          </div>

          <button
            type="button"
            onClick={handleStartVerification}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-bold flex items-center justify-center gap-2 shadow-sm transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">verified_user</span>
            <span>Verify with Evidence</span>
          </button>
        </div>
      </div>
    </div>
  );
}
