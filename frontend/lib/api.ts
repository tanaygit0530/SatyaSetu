import {
  VerificationResult,
  Claim,
  SourceCitation,
  Verdict,
  InputType,
  AdminMetrics,
  AuthoritativeSource,
  HistoryItem,
} from '@/types';
import { getAuthHeaders } from '@/lib/auth';

function getApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_API_URL;
  if (envUrl) {
    const clean = envUrl.replace(/\/+$/, '');
    return clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`;
  }
  return '/api/v1';
}

const API_BASE = getApiBase();

export interface CheckCreateResponse {
  check_id: string;
  status: string;
}

export interface CheckStatusResponse {
  check_id: string;
  stage: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error_code?: string;
  stages?: any[];
  error?: string;
}

export interface RawCheckDetail {
  check_id: string;
  status: string;
  input_type: string;
  text: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  claims?: any[];
  result?: any;
}

/**
 * Submits a text forward or statement to the real verification engine.
 */
export async function submitTextCheck(
  text: string,
  inputType: InputType = 'TEXT'
): Promise<CheckCreateResponse> {
  const res = await fetch(`${API_BASE}/checks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      text,
      input_type: inputType,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to submit check (${res.status}): ${errText}`);
  }

  return res.json();
}

/**
 * Uploads media (screenshot, voice note, PDF) to the real ingestion service
 * and enqueues verification.
 */
export async function uploadMediaCheck(
  file: File,
  inputType: 'SCREENSHOT' | 'VOICE' | 'PDF'
): Promise<CheckCreateResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('input_type', inputType);

  const res = await fetch(`${API_BASE}/checks/upload`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
    },
    body: formData,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Upload failed (${res.status}): ${errText}`);
  }

  return res.json();
}

/**
 * Ingests a public article URL and enqueues verification.
 */
export async function submitUrlCheck(url: string): Promise<CheckCreateResponse> {
  // 1. Ingest URL to extract article text
  const ingestRes = await fetch(`${API_BASE}/ingest/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });

  if (!ingestRes.ok) {
    const errText = await ingestRes.text();
    throw new Error(`URL ingestion failed (${ingestRes.status}): ${errText}`);
  }

  const ingestData = await ingestRes.json();
  const extractedText = ingestData.extracted_text || `[Article Link]: ${url}`;

  // 2. Submit extracted article text for verification
  return submitTextCheck(extractedText, 'LINK');
}

/**
 * Polls the current live verification status of a check.
 */
export async function getCheckStatus(checkId: string): Promise<CheckStatusResponse> {
  const res = await fetch(`${API_BASE}/checks/${encodeURIComponent(checkId)}/status`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(`Check ${checkId} not found.`);
    }
    throw new Error(`Failed to fetch status: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Retrieves the full check detail dossier from the backend.
 */
export async function getCheckDetail(checkId: string): Promise<RawCheckDetail> {
  const res = await fetch(`${API_BASE}/checks/${encodeURIComponent(checkId)}`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(`Check record ${checkId} not found.`);
    }
    throw new Error(`Failed to fetch check: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Lists real checks from the repository.
 */
export async function listChecks(limit: number = 50): Promise<RawCheckDetail[]> {
  try {
    const res = await fetch(`${API_BASE}/checks?limit=${limit}`, {
      cache: 'no-store',
    });

    if (!res.ok) {
      return [];
    }

    return res.json();
  } catch (err) {
    console.error('Failed to list checks:', err);
    return [];
  }
}

/**
 * Retrieves genuine aggregate statistics computed by the backend.
 */
export async function getAdminMetrics(): Promise<AdminMetrics> {
  const res = await fetch(`${API_BASE}/checks/stats/summary`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch metrics: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Retrieves registered authoritative and secondary sources.
 */
export async function listAuthoritativeSources(): Promise<AuthoritativeSource[]> {
  try {
    const res = await fetch(`${API_BASE}/sources`, {
      cache: 'no-store',
    });

    if (!res.ok) {
      return [];
    }

    const raw = await res.json();
    return raw.map((s: any, idx: number) => ({
      id: `SRC-${idx + 1}`,
      name: s.organization_name || s.name || s.domain,
      domain: s.domain,
      tier: s.tier === 1 ? 'TIER_1_PRIMARY' : s.tier === 2 ? 'TIER_2_SECONDARY' : 'TIER_3_REPUTABLE',
      category: (s.category || 'STATUTORY_BODY').toUpperCase(),
      lastCrawledAt: s.last_crawled_at || new Date().toISOString(),
      recordsIndexed: s.records_indexed || 120,
      precedenceRank: s.tier || 1,
      status: s.allowed ? 'HEALTHY' : 'MAINTENANCE',
    }));
  } catch (err) {
    console.error('Failed to load sources:', err);
    return [];
  }
}

/**
 * Transforms a backend check record into the frontend VerificationResult model.
 */
export function adaptCheckToUi(raw: RawCheckDetail): VerificationResult {
  const result = raw.result || {};
  const rawClaims = result.claims || raw.claims || [];

  const rawVerdict = result.overall_verdict || (rawClaims[0]?.verdict) || 'CANNOT_BE_CONFIRMED';
  const cleanVerdict = (typeof rawVerdict === 'string' ? rawVerdict : rawVerdict.value || 'CANNOT_BE_CONFIRMED')
    .toUpperCase() as Verdict;

  const claims: Claim[] = rawClaims.map((c: any, index: number) => {
    const cVerdict = (typeof c.verdict === 'string' ? c.verdict : c.verdict?.value || cleanVerdict).toUpperCase() as Verdict;

    // Numerical confidence
    let confidenceNum = 85;
    if (typeof c.confidence === 'number') {
      confidenceNum = c.confidence;
    } else if (typeof c.confidence === 'string') {
      if (c.confidence.toUpperCase() === 'HIGH') confidenceNum = 95;
      else if (c.confidence.toUpperCase() === 'MEDIUM') confidenceNum = 70;
      else if (c.confidence.toUpperCase() === 'LOW') confidenceNum = 40;
    }

    const rawEvidence = c.evidence || [];
    const sourceCitations: SourceCitation[] = rawEvidence.map((ev: any, evIdx: number) => {
      const url = ev.source_url || ev.url || '';
      let domain = ev.domain || '';
      if (!domain && url) {
        try {
          domain = new URL(url).hostname;
        } catch {
          domain = url;
        }
      }

      const quote = ev.verbatim_quote || ev.exact_quote || ev.snippet || '';
      const publisher = ev.source_name || ev.publisher || ev.source_title || domain || 'Authoritative Source';

      let tier: 'TIER_1_PRIMARY' | 'TIER_2_SECONDARY' | 'TIER_3_REPUTABLE' = 'TIER_1_PRIMARY';
      const tierVal = ev.tier || ev.source_tier;
      if (tierVal === 2 || String(tierVal).includes('2')) tier = 'TIER_2_SECONDARY';
      else if (tierVal === 3 || String(tierVal).includes('3')) tier = 'TIER_3_REPUTABLE';

      return {
        id: ev.id || `EV-${index + 1}-${evIdx + 1}`,
        publisher,
        domain,
        title: ev.source_title || publisher,
        date: ev.retrieved_at || ev.published_date || new Date().toISOString(),
        tier,
        url,
        exactQuote: quote,
        confidenceScore: confidenceNum,
      };
    });

    const ruleTrace = c.rule_trace || [];
    const ruleMatched = ruleTrace.length > 0 ? (typeof ruleTrace[0] === 'string' ? ruleTrace.join(' → ') : ruleTrace[0]?.rule_name || 'RULE-VERIFIED') : undefined;

    return {
      id: c.claim_id || `CLM-${index + 1}`,
      claimNumber: index + 1,
      claimText: c.claim_text || c.normalized_claim || raw.text,
      language: (c.language || 'en') as 'en' | 'hi' | 'mr',
      verdict: cVerdict,
      confidence: confidenceNum,
      summary: c.explanation || result.summary || 'Evidentiary determination completed.',
      detailedAnalysis: c.explanation || result.summary || '',
      sourceCitations,
      ruleMatched,
    };
  });

  const durationMs = result.processing_duration_ms || result.processing_time_ms || 0;
  const isCacheHit = Boolean(result.cache_hit || result.is_cached);

  let mappedInputType: InputType = 'TEXT';
  const rawInp = (raw.input_type || 'TEXT').toUpperCase();
  if (rawInp === 'SCREENSHOT' || rawInp === 'IMAGE') mappedInputType = 'SCREENSHOT';
  else if (rawInp === 'VOICE' || rawInp === 'AUDIO') mappedInputType = 'VOICE';
  else if (rawInp === 'PDF') mappedInputType = 'PDF';
  else if (rawInp === 'LINK' || rawInp === 'URL') mappedInputType = 'LINK';

  return {
    id: raw.check_id,
    publicId: raw.check_id,
    inputType: mappedInputType,
    submittedAt: raw.created_at || new Date().toISOString(),
    completedAt: raw.completed_at || raw.updated_at || new Date().toISOString(),
    processingDurationMs: durationMs,
    originalMessage: raw.text,
    sourceOrigin: 'WEB',
    overallVerdict: cleanVerdict,
    verdictSummary: result.summary || (claims[0]?.summary) || 'Verification process completed.',
    claims,
    cacheHit: isCacheHit,
  };
}

/**
 * Transforms a raw check into a history item.
 */
export function adaptCheckToHistory(raw: RawCheckDetail): HistoryItem {
  const adapted = adaptCheckToUi(raw);
  return {
    id: raw.check_id,
    checkId: raw.check_id,
    title: adapted.claims[0]?.claimText || raw.text.slice(0, 80),
    snippet: raw.text.slice(0, 150),
    inputType: adapted.inputType,
    timestamp: adapted.submittedAt,
    verdict: adapted.overallVerdict,
    claimsCount: adapted.claims.length || 1,
  };
}

export interface UserAnalyticsSummary {
  user_id: string;
  total_checks: number;
  verdict_counts: {
    VERIFIED: number;
    FALSE: number;
    OUTDATED: number;
    PARTLY_SUPPORTED: number;
    CANNOT_BE_CONFIRMED: number;
  };
  activity_timeline: Array<{
    date: string;
    count: number;
  }>;
  recent_checks: Array<{
    check_id: string;
    text: string;
    verdict: string;
    input_type: string;
    created_at: string;
    completed_at: string | null;
  }>;
}

export async function requestOtp(phoneNumber: string): Promise<{ success: boolean; message: string; cooldown_seconds?: number }> {
  const res = await fetch(`${API_BASE}/auth/request-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to send OTP (${res.status})`);
  }
  return data;
}

export async function verifyOtp(phoneNumber: string, code: string): Promise<{ success: boolean; access_token: string; token_type: string; user: any; message: string }> {
  const res = await fetch(`${API_BASE}/auth/verify-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number: phoneNumber, code }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Verification failed (${res.status})`);
  }
  return data;
}

export async function fetchCurrentUser(): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch current user (${res.status})`);
  }
  return res.json();
}

export async function changePhoneRequestOtp(newPhoneNumber: string): Promise<{ success: boolean; message: string; cooldown_seconds?: number }> {
  const res = await fetch(`${API_BASE}/auth/change-phone/request-otp`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ new_phone_number: newPhoneNumber }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to request OTP for new phone (${res.status})`);
  }
  return data;
}

export async function changePhoneVerifyOtp(newPhoneNumber: string, code: string): Promise<{ success: boolean; access_token: string; user: any; message: string }> {
  const res = await fetch(`${API_BASE}/auth/change-phone/verify-otp`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ new_phone_number: newPhoneNumber, code }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to verify new phone (${res.status})`);
  }
  return data;
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
      },
    });
  } catch (err) {
    console.warn('Logout request failed on server:', err);
  }
}

export async function fetchUserAnalytics(): Promise<UserAnalyticsSummary> {
  const res = await fetch(`${API_BASE}/users/me/analytics`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to fetch personal analytics (${res.status})`);
  }
  return res.json();
}

export async function fetchUserChecks(limit = 20, offset = 0): Promise<{ checks: any[]; total: number }> {
  const res = await fetch(`${API_BASE}/users/me/checks?limit=${limit}&offset=${offset}`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to fetch personal checks (${res.status})`);
  }
  const rawData = await res.json();
  if (Array.isArray(rawData)) {
    return { checks: rawData, total: rawData.length };
  }
  return { checks: rawData.checks || [], total: rawData.total || 0 };
}
