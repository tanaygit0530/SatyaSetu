import React from 'react';
import Link from 'next/link';
import { APP_CONFIG } from '@/lib/constants';

export function CitizenFooter() {
  return (
    <footer className="w-full bg-surface-container-lowest border-t border-outline-variant mt-auto">
      <div className="max-w-7xl mx-auto px-margin md:px-margin-desktop py-space-xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-space-xl mb-space-xl">
          {/* Col 1: Brand & Tagline */}
          <div className="md:col-span-1 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-primary-container flex items-center justify-center text-on-primary">
                <span className="material-symbols-outlined text-[18px]">verified_user</span>
              </div>
              <span className="font-headline-sm text-headline-sm text-on-surface font-bold">
                SachCheck
              </span>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              "{APP_CONFIG.tagline}"
            </p>
            <div className="pt-2 flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed-variant font-code-sm text-[11px] font-bold">
                IFCN Signatory Tier-1
              </span>
              <span className="px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-code-sm text-[11px]">
                v4.2 LTS
              </span>
            </div>
          </div>

          {/* Col 2: Citizen Ingestion */}
          <div className="space-y-2.5">
            <h4 className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider">
              Verification Engine
            </h4>
            <ul className="space-y-2 font-body-sm text-body-sm text-on-surface-variant">
              <li>
                <Link href="/check" className="hover:text-primary transition-colors">
                  Check a Forward
                </Link>
              </li>
              <li>
                <Link href="/whatsapp" className="hover:text-primary transition-colors">
                  WhatsApp Forward Bot
                </Link>
              </li>
              <li>
                <Link href="/history" className="hover:text-primary transition-colors">
                  Verification History
                </Link>
              </li>
              <li>
                <Link href="/c/SC-2026-8941" className="hover:text-primary transition-colors">
                  Sample Public Verdict
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Transparency & Standards */}
          <div className="space-y-2.5">
            <h4 className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider">
              Methodology
            </h4>
            <ul className="space-y-2 font-body-sm text-body-sm text-on-surface-variant">
              <li>
                <Link href="/how-we-decide" className="hover:text-primary transition-colors">
                  How We Decide (5 Verdicts)
                </Link>
              </li>
              <li>
                <Link href="/how-we-decide#precedence" className="hover:text-primary transition-colors">
                  Authoritative Source Hierarchy
                </Link>
              </li>
              <li>
                <Link href="/how-we-decide#rules" className="hover:text-primary transition-colors">
                  Deterministic Rule Engine
                </Link>
              </li>
              <li>
                <Link href="/settings" className="hover:text-primary transition-colors">
                  Privacy & Data Retention
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Auditor & Governance */}
          <div className="space-y-2.5">
            <h4 className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider">
              Civic Governance
            </h4>
            <ul className="space-y-2 font-body-sm text-body-sm text-on-surface-variant">
              <li>
                <Link href="/admin/login" className="hover:text-secondary font-semibold transition-colors">
                  Auditor Desk Login
                </Link>
              </li>
              <li>
                <Link href="/admin" className="hover:text-primary transition-colors">
                  Live Operations Console
                </Link>
              </li>
              <li>
                <Link href="/admin/evaluation" className="hover:text-primary transition-colors">
                  Benchmark Evaluations
                </Link>
              </li>
              <li>
                <Link href="/admin/sources" className="hover:text-primary transition-colors">
                  Source Registry (NIC/PIB)
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-space-md border-t border-outline-variant flex flex-col sm:flex-row items-center justify-between gap-space-sm text-on-surface-variant font-body-sm text-body-sm">
          <p>© 2026 SachCheck Civic Truth Engine. Dedicated to public fact verification across India.</p>
          <p className="font-code-sm text-code-sm">
            Node: NIC-DELHI-GW4 • Repository: {APP_CONFIG.repositoryId}
          </p>
        </div>
      </div>
    </footer>
  );
}
