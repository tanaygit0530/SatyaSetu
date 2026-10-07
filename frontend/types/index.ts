export type Verdict =
  | 'VERIFIED'
  | 'FALSE'
  | 'OUTDATED'
  | 'PARTLY_SUPPORTED'
  | 'CANNOT_BE_CONFIRMED';

export type InputType =
  | 'TEXT'
  | 'SCREENSHOT'
  | 'VOICE'
  | 'PDF'
  | 'LINK';

export type SourceTier =
  | 'TIER_1_PRIMARY'   // Official Gazettes, NIC portals, Ministry Circulars, PIB Fact Check
  | 'TIER_2_SECONDARY' // Tier-1 News Agencies, Statutory Authorities, High Court Orders
  | 'TIER_3_REPUTABLE'; // Reputed Fact-checking Signatories (IFCN), National Dailies

export interface SourceCitation {
  id: string;
  publisher: string;
  domain: string;
  title: string;
  date: string;
  tier: SourceTier;
  url: string;
  archiveUrl?: string;
  exactQuote: string;
  confidenceScore: number;
  jurisdiction?: string;
  archiveHash?: string;
}

export interface Claim {
  id: string;
  claimNumber: number;
  claimText: string;
  originalLanguageText?: string;
  language?: 'en' | 'hi' | 'mr';
  verdict: Verdict;
  confidence: number; // 0 - 100
  summary: string;
  detailedAnalysis: string;
  temporalStatus?: 'CURRENT' | 'OUTDATED_2022' | 'HISTORICAL';
  sourceCitations: SourceCitation[];
  counterEvidenceSummary?: string;
  ruleMatched?: string;
}

export interface VerificationResult {
  id: string; // e.g. SC-2026-8941
  publicId: string;
  inputType: InputType;
  submittedAt: string;
  completedAt: string;
  processingDurationMs: number;
  originalMessage: string;
  sourceOrigin: 'WHATSAPP' | 'WEB' | 'PORTAL' | 'MOBILE';
  overallVerdict: Verdict;
  verdictSummary: string;
  claims: Claim[];
  cacheHit: boolean;
  cachedFromId?: string;
  cachedAt?: string;
  repositoryId?: string;
  metadata?: {
    fileSizeBytes?: number;
    fileName?: string;
    mediaDurationSecs?: number;
    extractedWordCount?: number;
  };
}

export interface ProcessingStep {
  id: string;
  name: string;
  description: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  durationMs?: number;
  details?: string;
}

export interface HistoryItem {
  id: string;
  checkId: string;
  title: string;
  snippet: string;
  inputType: InputType;
  timestamp: string;
  verdict: Verdict;
  claimsCount: number;
  isBookmarked?: boolean;
}

export interface AdminMetrics {
  totalChecks24h: number;
  avgLatencyMs: number;
  cacheHitRatio: number;
  accuracyRate: number;
  activeDisputes: number;
  crawlersOnline: number;
  totalCrawlers: number;
  checksPerVerdict: {
    verified: number;
    falseClaims: number;
    outdated: number;
    partlySupported: number;
    cannotConfirm: number;
  };
}

export interface RumourCluster {
  id: string;
  clusterId: string;
  canonicalClaim: string;
  verdict: Verdict;
  firstSeen: string;
  lastSeen: string;
  totalOccurrences: number;
  languages: ('en' | 'hi' | 'mr')[];
  topSpreadPlatform: string;
  status: 'ACTIVE_DEBUNK' | 'RESOLVED' | 'UNDER_REVIEW';
  cachedHits: number;
  similarityThreshold: number;
}

export interface ReviewQueueItem {
  id: string;
  checkId: string;
  claimId: string;
  claimText: string;
  automatedVerdict: Verdict;
  confidence: number;
  disputeReason: string;
  submittedBy: string;
  createdAt: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'PENDING' | 'ACCEPTED' | 'REJECTED';
}

export interface AuthoritativeSource {
  id: string;
  name: string;
  domain: string;
  tier: SourceTier;
  category: 'MINISTRY' | 'JUDICIARY' | 'STATE_GAZETTE' | 'PIB' | 'STATUTORY_BODY';
  lastCrawledAt: string;
  recordsIndexed: number;
  precedenceRank: number;
  status: 'HEALTHY' | 'DEGRADED' | 'MAINTENANCE';
}

export type Language = 'en' | 'hi' | 'mr';
export type FontScale = 'standard' | 'medium' | 'large';
