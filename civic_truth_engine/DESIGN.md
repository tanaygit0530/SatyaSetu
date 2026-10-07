---
name: Civic Truth Engine
colors:
  surface: '#faf9ff'
  surface-dim: '#cedafa'
  surface-bright: '#faf9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#e9edff'
  surface-container-high: '#e1e8ff'
  surface-container-highest: '#d8e2ff'
  on-surface: '#0f1b33'
  on-surface-variant: '#434655'
  inverse-surface: '#253049'
  inverse-on-surface: '#edf0ff'
  outline: '#747686'
  outline-variant: '#c4c5d7'
  surface-tint: '#2151da'
  primary: '#0037b0'
  on-primary: '#ffffff'
  primary-container: '#1d4ed8'
  on-primary-container: '#cad3ff'
  inverse-primary: '#b7c4ff'
  secondary: '#9a4600'
  on-secondary: '#ffffff'
  secondary-container: '#fe852f'
  on-secondary-container: '#642b00'
  tertiary: '#004f27'
  on-tertiary: '#ffffff'
  tertiary-container: '#006a36'
  on-tertiary-container: '#82ea9f'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b7c4ff'
  on-primary-fixed: '#001551'
  on-primary-fixed-variant: '#0039b5'
  secondary-fixed: '#ffdbc9'
  secondary-fixed-dim: '#ffb68c'
  on-secondary-fixed: '#321200'
  on-secondary-fixed-variant: '#753400'
  tertiary-fixed: '#90f8ad'
  tertiary-fixed-dim: '#74db92'
  on-tertiary-fixed: '#00210d'
  on-tertiary-fixed-variant: '#005228'
  background: '#faf9ff'
  on-background: '#0f1b33'
  surface-variant: '#d8e2ff'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: '0'
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: '0'
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: '0'
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: '0'
  quoted-claim:
    fontFamily: Source Serif 4
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: '0'
  quoted-claim-lg:
    fontFamily: Source Serif 4
    fontSize: 19px
    fontWeight: '400'
    lineHeight: 30px
    letterSpacing: '0'
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  code-sm:
    fontFamily: Space Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: '0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

This design system is engineered for civic accountability, absolute evidential clarity, and democratic accessibility across multilingual India. It rejects transient tech gimmicks—there are no iridescent gradients, no conversational AI chatbots with robotic avatars, no futuristic purple flares, and no distracting glassmorphic surfaces. Instead, the design system embodies the authoritative, calm, and objective demeanor of a top-tier institutional information product fused with an independent, forensic newsroom.

The aesthetic philosophy centers on:
- **Radical Transparency:** Every claim, extraction, and judgment must be visually dissectible. Sources, methodology notes, and original context are presented with scientific detachment and legibility.
- **Calm Authority:** Misinformation evokes panic, confusion, and cognitive overload. The UI acts as a cooling agent, deploying structured whitespace, balanced layouts, and crisp typographical hierarchy to restore rational inquiry.
- **Civic Inclusion:** Designed from the ground up for diverse digital literacy levels across rural, semi-urban, and metropolitan India. Interfaces support straightforward forward-ingestion (WhatsApp-style media, voice notes, screenshots, circulars) with zero ambiguity in status indicators.
- **Structural Integrity:** Crisp outlines, clean architectural dividers, and semantic surface grouping anchor the interface, prioritizing reading comfort and evidential verification over decorative styling.

## Colors

The color palette prioritizes semantic clarity, information density, and strict compliance with WCAG 2.1 AA accessibility standards (minimum 4.5:1 contrast for regular text, 3:1 for large text and graphical UI controls).

### Base Surfaces and Inks
- **Canvas (`#F6F8FB`):** A serene, ultra-cool neutral wash that grounds the viewport and reduces eye fatigue during extended reading.
- **Surface (`#FFFFFF`):** Pure white container surfaces that elevate primary evidence blocks and interactive forms against the canvas.
- **Primary Ink (`#0F1B33`):** High-contrast navy-slate for primary body copy, titles, and data values. Ensures razor-sharp legibility across standard and low-cost mobile displays.
- **Secondary Ink (`#526176`):** Balanced mid-slate for timestamps, secondary labels, metadata, and structural breadcrumbs.
- **Divider & Border (`#DDE3EC`):** A subtle, neutral architectural grey providing clean boundaries without visual clutter.

### Functional Brand & Action
- **Primary Interactive / Trust Blue (`#1D4ED8`):** Applied exclusively to functional affordances, primary actions, deep-link references, verified source anchors, and active tab indicators.
- **Civic Saffron Accent (`#E8741E`):** Deployed sparingly to highlight Indian civic context markers, national institutional registry lookups, and critical citizen advisories. Never used as a generic background wash.

### Evidentiary Verdict System
Verdicts must **never** rely solely on color. Every verdict token is strictly paired with a mandatory glyph/icon and explicit text label:
- **Verified (`#1E8E4E`):** Paired with `Shield Check`. Indicates full factual alignment with verifiable, authoritative primary records.
- **False (`#C62F2F`):** Paired with `X Circle`. Signifies fabricated claims, manipulated audiovisual assets, or wholly debunked statements.
- **Outdated (`#D9730D`):** Paired with `Clock Alert`. Signifies authentic historical information misleadingly recirculated as present reality.
- **Partly Supported (`#B7950B`):** Paired with `Circle Half-Fill`. Signifies a mixture of factual data and unverified inferences, hyperbole, or missing critical context.
- **Cannot Be Confirmed (`#64748B`):** Paired with `Help Circle`. Denotes inconclusive evidence, insufficient primary sources, or non-verifiable subjective assertion.

## Typography

The typographical structure reinforces neutral forensic clarity and absolute separation between incoming claim text and investigative verdicts.

### Font Hierarchy & Roles
- **Primary UI & Headings (Plus Jakarta Sans):** A contemporary grotesque with wide open apertures, generous counters, and crisp humanist terminals. Ideal for dense evidence trees, metadata tables, and system actions.
- **Quoted Source & Forwarded Media Text (Source Serif 4):** Reserved exclusively for incoming user claims, forwarded WhatsApp transcripts, scraped circular quotes, and speech-to-text transcripts. This distinct serif appearance immediately visually signals to the citizen: *"This is the unverified text under inspection, not the platform's editorial voice."*
- **Multilingual Localization (Noto Sans Devanagari):** Used dynamically across Hindi and Marathi interfaces. Shares matching vertical metrics and x-height proportions with Plus Jakarta Sans to maintain vertical rhythm without layout shifts.

### Rules and Accessibility
- **Casing:** Sentence case is mandated across all titles, buttons, badges, and labels. Avoid aggressive all-caps strings, which induce alarm and mimic sensationalist forwarding patterns.
- **Font Scaler Architecture:** The layout respects accessibility scaling levels:
  - Standard (`A`): 100% (root `16px`)
  - Medium (`A+`): 112.5% (root `18px`)
  - Large (`A++`): 125% (root `20px`)
  All container heights must remain fluid or use minimum heights to prevent truncation when scaling.

## Layout & Spacing

This design system uses an **8px base grid** (with a 4px half-step for precise label and badge internal alignment) to govern all dimensional spacing, component paddings, and column offsets.

### Viewport and Grid System
- **Citizen Experience Shell:** Maximum container width of `1200px`. Centered on wide screens to preserve focused, eye-tracking-optimized reading paths for evidentiary claims.
- **Investigator / Admin Workspace Shell:** Maximum container width of `1440px`. Accommodates dense tri-pane auditing layouts: Media Inspector, Claim Parser, and Source Cross-Reference Matrix.
- **Desktop (1024px+):** 12-column fluid grid, `24px` (`1.5rem`) gutters, and minimum `32px` (`2rem`) page margin.
- **Tablet (640px – 1023px):** 8-column fluid grid, `16px` (`1rem`) gutters, and `24px` (`1.5rem`) page margin.
- **Mobile (< 640px):** 4-column fluid grid, `16px` (`1rem`) gutters, and `16px` (`1rem`) page margin.

### Vertical Rhythm
- Maintain a consistent `space-lg` (24px) distance between logical claim inspection modules.
- Nested verdict evidence blocks sit within a `space-md` (16px) internal container padding.
- Touch-target padding ensures no interactive trigger drops below `44px × 44px`.

## Elevation & Depth

To maintain high institutional trust and clear reading environments, depth is achieved through **crisp architectural borders and subtle surface tinting** rather than dramatic shadows or floating blurs.

### Surface Elevation Strategy
- **Layer 0 (Canvas):** `#F6F8FB`—The underlying application frame.
- **Layer 1 (Card / Module Surface):** `#FFFFFF` with a crisp `1px solid #DDE3EC` border. Zero drop-shadow. Used for all primary content containers, claim cards, and data listings.
- **Layer 2 (Inset / Quoted Blocks):** `#F1F4F9` with a subtle inset `1px solid #DDE3EC` border or a `3px` solid left accent rail. Used inside cards to visually set apart forwarded transcripts, audio waveforms, or citation quotes.
- **Layer 3 (Overlay / Menus / Dropdowns):** `#FFFFFF` with a `1px solid #DDE3EC` border and an ambient, low-contrast shadow: `0px 4px 16px rgba(15, 27, 51, 0.08)`.
- **Layer 4 (Modals & Verification Dialogs):** `#FFFFFF` with `1px solid #DDE3EC` and `0px 12px 32px rgba(15, 27, 51, 0.14)`, centered over a semi-translucent backdrop scrim of `rgba(15, 27, 51, 0.48)`.

## Shapes

The design system employs a functional, calibrated shape scale that communicates reliability and precision without appearing toy-like or sterile.

- **Primary Cards & Containers:** Standardized at `12px` (`0.75rem`) border radius. This subtle curvature balances contemporary digital ergonomics with authoritative, document-like structure.
- **Interactive Inputs, Dropdowns, and Buttons:** Standardized at `8px` (`0.5rem`) border radius. Sharp enough to feel exact and systematic; rounded enough to denote immediate touch friendliness.
- **Status Pills, Claim Verdict Badges, and Filter Chips:** Standardized at `999px` (Full Pill). Creates instantaneous visual differentiation between interactive buttons (rectilinear) and evidentiary status markers (capsular).
- **Focus Rings:** Unbroken `2px` offset with `2px` solid `#1D4ED8` outline around all focusable boundaries on keyboard navigation.

## Components

### 1. Buttons
- **Primary:** Solid `#1D4ED8` background, white label, `8px` radius, `0px` border. Hover: `#173EB0`. Active: `#143596`. Minimum height `44px`, horizontal padding `20px`.
- **Secondary / Outline:** Surface white background, `#0F1B33` text, `1px solid #DDE3EC` border. Hover: `#F1F4F9` background, `#1D4ED8` border.
- **Ghost:** Transparent background, `#1D4ED8` text. Hover: `#F1F4F9`. For tertiary actions like *"View Methodology"*.
- **Touch Standard:** All interactive triggers have a guaranteed hit-box of at least `44px × 44px`.

### 2. Verdict Badges & Claim Pills
- **Structure:** Pill shape (`999px` radius), strictly composed of `[Icon] + [Verdict Label]`.
- **Verified:** Background `#EAF6EE`, border `1px solid #B8E4C8`, text `#146336`, icon `Shield Check`.
- **False:** Background `#FDF2F2`, border `1px solid #F6B8B8`, text `#991B1B`, icon `X Circle`.
- **Outdated:** Background `#FEF7ED`, border `1px solid #FCD4A5`, text `#A04F05`, icon `Clock Alert`.
- **Partly Supported:** Background `#FEFCE8`, border `1px solid #FBE89B`, text `#856807`, icon `Circle Half-Fill`.
- **Cannot Be Confirmed:** Background `#F1F5F9`, border `1px solid #CBD5E1`, text `#475569`, icon `Help Circle`.

### 3. Claim Inspection Card
- **Container:** Pure `#FFFFFF` background, `12px` border radius, `1px solid #DDE3EC` outer border, `space-md` (16px) or `space-lg` (24px) internal padding.
- **Claim Extraction Sub-Box:** Inset `#F1F4F9` background, `8px` radius, styled using `quoted-claim` (Source Serif 4) typography, with a distinct `3px solid #DDE3EC` left boundary rail.
- **Verdict Header:** Displays the Verdict Badge paired with a human-readable summary statement in `headline-sm` (Plus Jakarta Sans, 600 weight).
- **Citation Accordion:** Expandable source verification cards citing publication, verifiable archive link, date of record, and direct factual quote.

### 4. Input Fields & Ingestion Dropzones
- **Text & Link Input:** `#FFFFFF` background, `1px solid #DDE3EC` border, `8px` radius, `44px` minimum height, `12px` horizontal padding. Placeholder color `#526176`. Focus state transitions to `2px solid #1D4ED8`.
- **Forwarded Media Dropzone (Screenshots, PDFs, Voice Memos):** `#F6F8FB` canvas, dashed `2px solid #DDE3EC` border, `12px` radius. Features unambiguous dual actions: drag-and-drop zone and explicit *"Browse Files"* trigger. Includes helper text listing accepted citizen formats (PNG, JPG, MP3, WAV, PDF).

### 5. Checkboxes, Radio Buttons, and Toggles
- **Form Controls:** Fixed `20px × 20px` bounds with `8px` roundedness for toggles and `4px` for checkboxes. Selected state filled with `#1D4ED8` containing high-contrast white check indicator.

### 6. Multilingual Language Selector & Font Scaler Toolbar
- **Language Switcher:** Compact pill-grouped or select button allowing instant toggle between English, Hindi, and Marathi without page refresh.
- **Civic Font Scaler Widget:** Persistent utility control offering `A` (Default), `A+` (Medium), and `A++` (Large) to immediately scale base root text variables, ensuring full access for elderly and visually impaired citizens.