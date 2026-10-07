# SachCheck — Frontend Application

> **"Forward it. Know if it's true. In your language, with proof."**

SachCheck is an AI-powered civic claim verification platform designed for multilingual India. It ingests WhatsApp forwards, screenshots, voice notes, PDF circulars, and web links, decomposes them into atomic claims, and audits them against primary statutory records (The Gazette of India, PIB Fact Check, National Portals) with deterministic decision rules.

---

## Architecture Overview

This frontend consolidates 25 individual Google Stitch design screens into **one unified Next.js App Router application** with zero backend code (mock data layer prepared for seamless future API integration).

```
frontend/
├── app/
│   ├── layout.tsx                                # Root layout with fonts & theme tokens
│   ├── page.tsx                                  # Citizen Landing Page (p3)
│   ├── check/
│   │   ├── page.tsx                              # Unified 5-Way Ingestion Intake (p4-p8)
│   │   └── [id]/
│   │       ├── processing/page.tsx               # Real-time pipeline processing stepper (p9)
│   │       ├── page.tsx                          # Multi-claim verification result view (p10, p11, p26, p27)
│   │       └── evidence/[claimId]/page.tsx       # Forensic claim audit dossier (p12)
│   ├── c/[publicId]/page.tsx                     # Read-only public shareable verdict card (p14)
│   ├── history/page.tsx                          # Citizen local verification history timeline
│   ├── whatsapp/page.tsx                         # WhatsApp tipline & bot onboarding (p16)
│   ├── how-we-decide/page.tsx                    # Open methodology & 5 canonical verdicts (p17)
│   ├── settings/page.tsx                         # Retention & civic privacy preferences (p18)
│   ├── login/page.tsx                            # Citizen mobile OTP sign in
│   └── admin/
│       ├── layout.tsx                            # Auditor desk shell layout
│       ├── login/page.tsx                        # Auditor Desk authentication (p19)
│       ├── page.tsx                              # Operations Overview & KPI dashboard (p20)
│       ├── checks/page.tsx                       # Live Evidentiary Ingestion & diagnostics (p21)
│       ├── rumours/page.tsx                      # Rumour Memory & Vector Cache manager (p22)
│       ├── review/page.tsx                       # Human review & dispute queue (p23)
│       ├── evaluation/page.tsx                   # Adversarial benchmark suite & confusion matrix (p24)
│       └── sources/page.tsx                      # Authoritative source registry (p25)
├── components/
│   ├── layout/                                   # AppShell, AdminShell, CitizenFooter
│   ├── navigation/                               # TopNavigation, MobileNavigation, LanguageSwitcher, FontScaler
│   ├── input/                                    # InputTabs (Text, Screenshot, Voice, PDF, Link)
│   ├── verification/                             # ClaimCard, HighlightedMessage
│   ├── evidence/                                 # EvidenceCard, SourceTierBadge, QuoteBlock
│   ├── verdict/                                  # VerdictBadge, ConfidenceBand
│   ├── admin/                                    # AdminSidebar, AdminHeader, AdminKpiCard
│   └── states/                                   # EmptyState, ErrorState
├── lib/
│   ├── utils.ts                                  # Verdict configs, date formatting, styling helpers
│   ├── constants.ts                              # App metadata, navigation links
│   └── mock/                                     # Isolated typed mock data (checks, history, admin)
├── types/                                        # TypeScript definitions
└── styles/
    └── globals.css                               # Google Fonts, Material Symbols, Tailwind base
```

---

## Route Map

### Citizen Portal
| Route | Source Screen | Description |
| :--- | :--- | :--- |
| `/` | `p3_sachcheck_landing_page` | Landing page, atomic claim decomposition demo, 5 verdicts |
| `/check` | `p4`–`p8` (Text, Screenshot, Voice, PDF, Link) | 5-way unified ingestion interface |
| `/check/[id]/processing` | `p9_sachcheck_verification_pipeline_processing` | Live multi-stage pipeline animation with latency timer |
| `/check/[id]` | `p10_sachcheck_main_verification_result` | Aggregate verdict masthead + atomic claims breakdown |
| `/check/[id]/evidence/[claimId]` | `p12_sachcheck_detailed_evidence_page` | Forensic claim audit dossier with gazette quotations |
| `/c/[publicId]` | `p14_sachcheck_public_shareable_verdict` | Public tamper-proof read-only verification card |
| `/history` | Local verification timeline | Device-stored history with verdict filtering and clear |
| `/whatsapp` | `p16_sachcheck_whatsapp_connect` | WhatsApp tipline guide and chat simulation |
| `/how-we-decide` | `p17_sachcheck_how_we_decide` | 5 verdict rules and source precedence hierarchy |
| `/settings` | `p18_sachcheck_settings` | Local storage retention and privacy controls |
| `/login` | Citizen Phone OTP | Authentication with instant demo guest access |

### Auditor Desk (Admin Console)
| Route | Source Screen | Description |
| :--- | :--- | :--- |
| `/admin/login` | `p19_sachcheck_admin_login` | Secure Auditor Desk authentication |
| `/admin` | `p20_sachcheck_admin_overview` | Live metrics, Recharts hourly volume chart, verdict split |
| `/admin/checks` | `p21_sachcheck_live_checks_detail` | Real-time checks feed and diagnostic trace inspector |
| `/admin/rumours` | `p22_sachcheck_rumour_memory` | Rumour memory clusters and similarity threshold controls |
| `/admin/review` | `p23_sachcheck_review_queue` | Citizen dispute adjudication queue |
| `/admin/evaluation` | `p24_sachcheck_evaluation` | Confusion matrix, F1 benchmark, adversarial suites |
| `/admin/sources` | `p25_sachcheck_source_registry` | Precedence matrix for 48 NIC/PIB crawler registries |

---

## Design System Tokens

Conforms strictly to `civic_truth_engine/DESIGN.md`:
- **Canvas Base:** `#F6F8FB`
- **Surface:** `#FFFFFF`
- **Primary Ink:** `#0F1B33`
- **Trust Blue:** `#1D4ED8` (Primary Container), `#0037B0` (Primary)
- **Civic Saffron:** `#E8741E`
- **5 Canonical Verdicts:**
  - `VERIFIED`: `#1E8E4E` (`Shield Check`)
  - `FALSE`: `#C62F2F` (`Cancel`)
  - `OUTDATED`: `#D9730D` (`Update`)
  - `PARTLY_SUPPORTED`: `#B7950B` (`Contrast`)
  - `CANNOT_BE_CONFIRMED`: `#64748B` (`Help`)
- **Typography:**
  - UI Headings & Body: `Plus Jakarta Sans`
  - Unverified Claims & Citations: `Source Serif 4`
  - Technical Audit IDs: `Space Mono`
  - Hindi & Marathi Localization: `Noto Sans Devanagari`

---

## Development Setup

```bash
cd frontend
npm install
npm run dev
```

Server runs at `http://localhost:3000`.

To create a production build:
```bash
npm run build
```
