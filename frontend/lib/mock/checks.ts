import { VerificationResult } from '@/types';

export const MOCK_VERIFICATION_RESULTS: Record<string, VerificationResult> = {
  'SC-2026-8941': {
    id: 'SC-2026-8941',
    publicId: 'SC-2026-8941',
    inputType: 'TEXT',
    submittedAt: '2026-10-07T09:42:15Z',
    completedAt: '2026-10-07T09:42:18Z',
    processingDurationMs: 2420,
    sourceOrigin: 'WHATSAPP',
    overallVerdict: 'FALSE',
    verdictSummary:
      'Scholarship scheme exists, but monetary amount and portal link are fabricated. Official payout is ₹12,000 via scholarships.gov.in, not ₹50,000 on phishing site.',
    repositoryId: '0x9AF...41B',
    cacheHit: false,
    originalMessage:
      'URGENT FORWARD: Ministry of Education has launched Prime Minister Special Higher Merit Scholarship for 2026-27 batch. Every undergraduate student enrolled in UGC college will get ₹50,000 cash grant directly in bank account through DBT without entrance exam. Last date to register on pmssy-gov.in is 15th October.',
    claims: [
      {
        id: 'CLM-8941-1',
        claimNumber: 1,
        claimText:
          'Ministry of Education has notified the Prime Minister Special Higher Merit Scholarship for the 2026-27 academic session.',
        originalLanguageText:
          'शिक्षा मंत्रालय ने 2026-27 शैक्षणिक सत्र के लिए प्रधानमंत्री विशेष उच्च योग्यता छात्रवृत्ति अधिसूचित की है।',
        language: 'en',
        verdict: 'VERIFIED',
        confidence: 99.4,
        summary:
          'Gazette Notification MoE/HE/2026/04 confirms the notification of the renewed PM Higher Education Merit scheme.',
        detailedAnalysis:
          'Cross-referencing the official Department of Higher Education repository confirms that Notification No. 14-02/2026-Scholarships was officially gazetted on 12 September 2026.',
        temporalStatus: 'CURRENT',
        ruleMatched: 'RULE-GOV-GAZETTE-CORROBORATION',
        sourceCitations: [
          {
            id: 'CIT-01',
            publisher: 'The Gazette of India',
            domain: 'egazette.gov.in',
            title: 'Ministry of Education Special Scheme Circular No. 14/2026',
            date: '12 Sep 2026',
            tier: 'TIER_1_PRIMARY',
            url: 'https://egazette.gov.in/circ/2026/moe-14',
            exactQuote:
              'The Department of Higher Education hereby notifies the continuation of the Central Sector Scheme of Scholarship for College and University Students for academic session 2026-27.',
            confidenceScore: 0.99,
          },
          {
            id: 'CIT-02',
            publisher: 'Press Information Bureau (PIB)',
            domain: 'pib.gov.in',
            title: 'PIB FactCheck & Higher Education Release',
            date: '14 Sep 2026',
            tier: 'TIER_1_PRIMARY',
            url: 'https://pib.gov.in/PressReleasePage.aspx?PRID=205128',
            exactQuote:
              'Applications for National Merit Higher Education Scholarships are now open through the National Scholarship Portal.',
            confidenceScore: 0.98,
          },
        ],
      },
      {
        id: 'CLM-8941-2',
        claimNumber: 2,
        claimText:
          'Every undergraduate college student will receive ₹50,000 lump sum DBT grant without entrance examination.',
        originalLanguageText:
          'हर कॉलेज छात्र को बिना किसी प्रवेश परीक्षा के ₹50,000 की राशि सीधे बैंक खाते में दी जाएगी।',
        language: 'en',
        verdict: 'FALSE',
        confidence: 98.7,
        summary:
          'The official scheme provides ₹12,000 per annum for general degree courses, capped at 82,000 total merit quotas.',
        detailedAnalysis:
          'The claim exaggerates both the amount and universal eligibility. According to Section 4.2 of Scheme Guidelines, scholarships are restricted to students above the 80th percentile in Class XII with parental income under ₹4.5 lakh. The amount is ₹12,000/yr for graduation, not ₹50,000.',
        temporalStatus: 'CURRENT',
        ruleMatched: 'RULE-EXACT-FINANCIAL-DISCREPANCY',
        counterEvidenceSummary:
          'Discrepancy: ₹50,000 claimed vs ₹12,000 sanctioned in Gazette. Universal DBT claimed vs strict 80th percentile merit cutoff.',
        sourceCitations: [
          {
            id: 'CIT-03',
            publisher: 'National Scholarship Portal (NSP)',
            domain: 'scholarships.gov.in',
            title: 'Operational Guidelines: Central Sector Scholarship for College Students',
            date: '15 Sep 2026',
            tier: 'TIER_1_PRIMARY',
            url: 'https://scholarships.gov.in/guidelines/css-2026.pdf',
            exactQuote:
              'The rate of scholarship is Rs. 12,000/- per annum at Graduation level for first three years of College and University courses.',
            confidenceScore: 0.99,
          },
        ],
      },
      {
        id: 'CLM-8941-3',
        claimNumber: 3,
        claimText:
          'Citizens should register and submit bank details on domain pmssy-gov.in before 15th October.',
        originalLanguageText:
          'नागरिक 15 अक्टूबर से पहले pmssy-gov.in पर पंजीकरण करें।',
        language: 'en',
        verdict: 'FALSE',
        confidence: 100,
        summary:
          'Malicious phishing URL. The genuine application portal is solely scholarships.gov.in.',
        detailedAnalysis:
          'Domain WHOIS and NIC records confirm that pmssy-gov.in is an unauthorized third-party site registered via private offshore proxy. Indian Computer Emergency Response Team (CERT-In) has issued Phishing Advisory CI-2026-882 warning citizens not to enter Aadhaar or bank credentials.',
        temporalStatus: 'CURRENT',
        ruleMatched: 'RULE-PHISHING-DOMAIN-MATCH',
        sourceCitations: [
          {
            id: 'CIT-04',
            publisher: 'CERT-In & PIB Fact Check',
            domain: 'cert-in.org.in',
            title: 'Advisory CI-2026-882: Malicious Imitation Portals Posing as Ministry of Education',
            date: '02 Oct 2026',
            tier: 'TIER_1_PRIMARY',
            url: 'https://cert-in.org.in/advisories/CI-2026-882',
            exactQuote:
              'Citizens are strictly advised that pmssy-gov.in is a credential-harvesting phishing site. All genuine disbursements occur exclusively through scholarships.gov.in.',
            confidenceScore: 1.0,
          },
        ],
      },
    ],
  },
  'SC-2026-9021': {
    id: 'SC-2026-9021',
    publicId: 'SC-2026-9021',
    inputType: 'SCREENSHOT',
    submittedAt: '2026-10-07T08:14:00Z',
    completedAt: '2026-10-07T08:14:02Z',
    processingDurationMs: 1840,
    sourceOrigin: 'WHATSAPP',
    overallVerdict: 'OUTDATED',
    verdictSummary:
      'Authentic circular from COVID-19 period (March 2020) recirculated falsely as a 2026 railway lockdown order.',
    repositoryId: '0x3CB...11D',
    cacheHit: true,
    cachedFromId: 'SC-2025-1049',
    cachedAt: '2026-10-06T14:22:00Z',
    originalMessage:
      '[Forwarded Image] Ministry of Railways circular declaring suspension of all passenger train operations across zone starting midnight.',
    claims: [
      {
        id: 'CLM-9021-1',
        claimNumber: 1,
        claimText:
          'Indian Railways has ordered complete suspension of passenger train operations nationwide starting tomorrow.',
        language: 'en',
        verdict: 'OUTDATED',
        confidence: 96.2,
        summary:
          'This is a recirculated circular originally issued on 22 March 2020 during the nationwide COVID lockdown.',
        detailedAnalysis:
          'OCR comparison against Railway Board archives identifies exact text and circular number matching Order No. 2020/Tele/15/4 issued on 22.03.2020. No such restriction exists in 2026.',
        temporalStatus: 'OUTDATED_2022',
        ruleMatched: 'RULE-TEMPORAL-TIMESTAMP-MISMATCH',
        sourceCitations: [
          {
            id: 'CIT-05',
            publisher: 'Ministry of Railways (Railway Board)',
            domain: 'indianrailways.gov.in',
            title: 'Historical Order No. 2020/Tele/15/4',
            date: '22 Mar 2020',
            tier: 'TIER_1_PRIMARY',
            url: 'https://indianrailways.gov.in/railwayboard/historic/2020',
            exactQuote:
              'In view of the measures taken for COVID-19, all passenger train services were suspended till 31st March 2020.',
            confidenceScore: 0.98,
          },
        ],
      },
    ],
  },
  'SC-2026-7712': {
    id: 'SC-2026-7712',
    publicId: 'SC-2026-7712',
    inputType: 'VOICE',
    submittedAt: '2026-10-06T18:22:00Z',
    completedAt: '2026-10-06T18:22:04Z',
    processingDurationMs: 3100,
    sourceOrigin: 'PORTAL',
    overallVerdict: 'CANNOT_BE_CONFIRMED',
    verdictSummary:
      'Voice memo claims local water supply pipeline in Ward 14 contains chemical contaminants. Municipal Corporation has published no test advisories.',
    repositoryId: '0x712...99E',
    cacheHit: false,
    originalMessage:
      '[Audio Note 42s] "Dosto Ward 14 mein pani mat pina, tanker walon ne bola hai koi chemical mil gaya hai subah se."',
    claims: [
      {
        id: 'CLM-7712-1',
        claimNumber: 1,
        claimText:
          'Drinking water pipeline in Ward 14 has been chemically contaminated.',
        language: 'hi',
        verdict: 'CANNOT_BE_CONFIRMED',
        confidence: 48.0,
        summary:
          'No official municipal notice or laboratory quality test records corroborate contamination.',
        detailedAnalysis:
          'Searches across Municipal Corporation notices, Jal Board emergency bulletins, and regional district magistrate advisories yielded zero recorded water hazard warnings for this location.',
        ruleMatched: 'RULE-INSUFFICIENT-PRIMARY-RECORD',
        sourceCitations: [],
      },
    ],
  },
};

export const DEFAULT_CHECK = MOCK_VERIFICATION_RESULTS['SC-2026-8941'];
