# SatyaSetu (SachCheck)

> **"Forward it. Know if it's true. In your language, with proof."**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python)](https://python.org/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2D8?style=flat-square&logo=tailwind-css)](https://tailwindcss.com/)
[![Standards](https://img.shields.io/badge/Standards-IFCN%20Tier--1-1E8E4E?style=flat-square)](https://www.poynter.org/ifcn/)

---

## 🌟 Overview

**SachCheck** (Project: **SatyaSetu**) is an evidence-first civic claim verification platform engineered for multilingual India. It tackles viral misinformation circulating on messaging platforms (especially WhatsApp) by breaking complex forwards into atomic claims, checking them against primary statutory records (The Gazette of India, Press Information Bureau, National Portals), and rendering transparent, forensic proof.

### The Misinformation Challenge
Misinformation in India rarely arrives as a simple binary statement. Viral messages frequently bundle:
- A genuine government scheme name (e.g., *"Prime Minister Merit Scholarship"*).
- An inflated or fabricated financial figure (e.g., *"₹50,000 cash grant to every student without exam"*).
- A credential-harvesting phishing link (e.g., *"pmssy-gov.in"*).
- Recirculated historical orders (e.g., 2020 COVID lockdown orders shared without a timestamp in 2026).

Standard LLM chatbots frequently hallucinate or rely on unverified blogs. **SachCheck guarantees truth with statutory proof.**

---

## 🏛️ Core Architectural Principles

### 1. Atomic Claim Decomposition
One forward can contain multiple distinct statements. SachCheck isolates each assertion independently, so citizens see precisely which part is authentic, which part is exaggerated, and which part is a scam.

### 2. Deterministic Decision Engine (The LLM Never Decides the Verdict)
To maintain judicial-grade accountability:
- **LLM Responsibilities:** Multilingual extraction, atomic claim decomposition, query formulation, and human-friendly explanation generation.
- **Deterministic Code Responsibilities:** Statutory source validation, Tier-1 precedence ranking, temporal difference calculation, numerical discrepancy checks, and final verdict assignment.

### 3. The 5 Canonical Evidentiary Verdicts

| Verdict | Glyph | Color Token | Definition |
| :--- | :---: | :---: | :--- |
| **VERIFIED** | `Shield Check` | `#1E8E4E` | Full factual alignment with verifiable, authoritative primary gazettes. |
| **FALSE** | `X Circle` | `#C62F2F` | Fabricated claims, financial discrepancies, or phishing URLs. |
| **OUTDATED** | `Clock Alert` | `#D9730D` | Authentic historical circular misleadingly recirculated out of chronological context. |
| **PARTLY_SUPPORTED** | `Half Fill` | `#B7950B` | Core premise has factual basis, but secondary details or amounts are unverified. |
| **CANNOT_BE_CONFIRMED** | `Help Circle` | `#64748B` | Inconclusive documentary trail across official repositories. |

### 4. Authoritative Source Precedence Matrix
- **Tier 1 (Primary Statutory):** The Gazette of India (`egazette.gov.in`), Press Information Bureau (`pib.gov.in`), Supreme Court & High Court decrees, Official Ministry Portals (`scholarships.gov.in`, `indianrailways.gov.in`).
- **Tier 2 (Statutory Regulators):** UGC, AICTE, RBI, CERT-In, CBSE.
- **Tier 3 (Reputable Third-Party):** IFCN Signatories, PTI, ANI, National News Archives.

---

## 📂 Project Architecture

```
SachCheck/ (SatyaSetu)
│
├── frontend/                       # Consolidated Next.js 14 Single-Page Application
│   ├── app/
│   │   ├── layout.tsx              # Root HTML layout with Google Fonts & design tokens
│   │   ├── page.tsx                # Citizen Landing Page (Decomposition demo, 5 verdicts)
│   │   ├── check/
│   │   │   ├── page.tsx            # Unified 5-Way Intake (Text, Screenshot, Voice, PDF, Link)
│   │   │   └── [id]/
│   │   │       ├── processing/     # Live multi-stage pipeline animation with latency timer
│   │   │       ├── page.tsx        # Multi-claim verification result view
│   │   │       └── evidence/[claimId]/ # Forensic claim audit dossier with gazette quotes
│   │   ├── c/[publicId]/           # Tamper-proof read-only public shareable card
│   │   ├── history/                # Citizen local verification timeline
│   │   ├── whatsapp/               # WhatsApp tipline & bot onboarding (+91 91122 33445)
│   │   ├── how-we-decide/          # Open methodology & 5 canonical verdicts
│   │   ├── settings/               # Retention policy & civic privacy preferences
│   │   ├── login/                  # Citizen phone OTP sign-in + Demo guest access
│   │   └── admin/
│   │       ├── layout.tsx          # Auditor desk shell layout
│   │       ├── login/              # Secure Auditor Desk authentication
│   │       ├── page.tsx            # Operations Overview & KPI dashboard (Recharts)
│   │       ├── checks/             # Live Evidentiary Ingestion & diagnostic trace
│   │       ├── rumours/            # Rumour Memory & Vector Cache manager
│   │       ├── review/             # Human review & citizen dispute queue
│   │       ├── evaluation/         # Adversarial benchmark suite & confusion matrix
│   │       └── sources/            # Authoritative source registry (48 NIC crawlers)
│   ├── components/                 # Consolidated, reusable UI components
│   │   ├── layout/                 # AppShell, AdminShell, CitizenFooter
│   │   ├── navigation/             # TopNavigation, MobileNavigation, LanguageSwitcher, FontScaler
│   │   ├── input/                  # InputTabs (Text, Screenshot, Voice, PDF, Link)
│   │   ├── verification/           # ClaimCard, HighlightedMessage
│   │   ├── evidence/               # EvidenceCard, SourceTierBadge, QuoteBlock
│   │   ├── verdict/                # VerdictBadge, ConfidenceBand
│   │   └── admin/                  # AdminSidebar, AdminHeader, AdminKpiCard
│   ├── lib/
│   │   ├── mock/                   # Reusable mock datasets (checks, history, admin)
│   │   ├── utils.ts                # Styling helpers, date formatting, verdict tokens
│   │   └── constants.ts            # App metadata and navigation routes
│   └── styles/
│       └── globals.css             # Google Fonts, Material Symbols Outlined, Tailwind directives
│
├── backend/                        # Python / FastAPI Verification Engine Foundation
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory, CORS, exception handlers
│   │   ├── api/
│   │   │   ├── routes/             # API route endpoints
│   │   │   │   ├── __init__.py     # api_router aggregation
│   │   │   │   └── health.py       # GET /api/v1/health endpoint
│   │   │   └── dependencies.py     # Injected dependencies (settings, logger, security)
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic BaseSettings environment configuration
│   │   │   ├── logging.py          # Structured console logger
│   │   │   ├── exceptions.py       # SachCheckException hierarchy
│   │   │   └── security.py         # Security utilities & API key verifier
│   │   ├── schemas/
│   │   │   ├── enums.py            # 5 Verdicts, SourceTier, InputType
│   │   │   ├── claim.py            # ExtractedClaim & ClaimResult models
│   │   │   ├── evidence.py         # EvidenceItem & EvidenceInterpretation models
│   │   │   ├── verification.py     # VerificationRequest & VerificationResponse models
│   │   │   └── health.py           # HealthResponse model
│   │   ├── services/
│   │   │   ├── rule_engine.py      # Pure-code deterministic verdict decision engine
│   │   │   ├── claim_extractor.py  # Atomic claim decomposition & provider abstraction
│   │   │   ├── evidence_retriever.py # Statutory registry queries (Gazette, PIB, NSP)
│   │   │   └── verification_service.py # End-to-end verification orchestrator
│   │   ├── repositories/           # In-memory storage + Cloud Firestore sync
│   │   └── utils/
│   │       └── sanitizer.py        # Unicode normalization & Prompt Injection defense
│   ├── tests/
│   │   ├── test_health.py          # Foundation health check tests
│   │   ├── test_rule_engine.py     # Deterministic decision rules & aggregation tests
│   │   └── test_api_integration.py # Full integration tests
│   ├── scripts/
│   │   └── verify_cli.py           # Standalone command-line forward verification utility
│   ├── requirements.txt            # FastAPI, Uvicorn, Pydantic, HTTPX, Pytest, Firebase
│   └── .env.example                # Environment variable configuration template
│
└── .gitignore                      # Git ignore rules for node_modules, venv, .env, and caches
```

---

## 🚀 Quick Start Guide

### 1. Run the Frontend (Next.js)

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

* **Frontend URL:** [http://localhost:3000](http://localhost:3000)
* **Production Build:** `npm run build && npm run start`

#### Primary Frontend Routes:
* `/` — Landing page & claim decomposition demo
* `/check` — 5-way citizen intake (Text, Screenshot, Voice, PDF, Link)
* `/check/SC-2026-8941/processing` — Live pipeline processing animation
* `/check/SC-2026-8941` — Verification result with test case variant toggling
* `/check/SC-2026-8941/evidence/CLM-8941-2` — Forensic claim audit dossier
* `/c/SC-2026-8941` — Tamper-proof public shareable card
* `/whatsapp` — WhatsApp tipline connection guide (+91 91122 33445)
* `/admin` — Auditor Desk Operations Console (Live KPIs, Recharts volume trend, Rumour Memory, Review Queue)

---

### 2. Run the Backend (FastAPI)

```bash
# Navigate to the backend directory
cd backend

# Create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* **Backend URL:** [http://localhost:8000](http://localhost:8000)
* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### Test the Health Endpoint:
```bash
curl -s http://localhost:8000/api/v1/health
```
**Response:**
```json
{
  "status": "ok",
  "service": "sachcheck-backend",
  "version": "0.1.0"
}
```

#### Run the Automated Backend Test Suite:
```bash
pytest -v
```

#### Test Verification from the CLI:
```bash
python scripts/verify_cli.py "Ministry offers ₹50,000 scholarship on pmssy-gov.in"
```

---

## 🎨 Design System & Accessibility

* **Palette:**
  * Canvas: `#F6F8FB`
  * Surface: `#FFFFFF`
  * Deep Ink: `#0F1B33`
  * Trust Blue: `#1D4ED8`
  * Civic Saffron: `#E8741E`
* **Typography:**
  * Interface Headings & Body: `Plus Jakarta Sans`
  * Incoming Claims & Citations: `Source Serif 4`
  * Technical Case IDs & Timestamps: `Space Mono`
  * Multilingual Localization: `Noto Sans Devanagari`
* **Civic Accessibility Tools:**
  * Instant Language Switcher (`EN` | `हिं` | `मरा`).
  * Dynamic Font Scaler (`A` 100% | `A+` 112.5% | `A++` 125%).

---

## 🛡️ License & Standards
Engineered in compliance with the **International Fact-Checking Network (IFCN) Code of Principles** for open methodology, nonpartisanship, and transparent sourcing.
