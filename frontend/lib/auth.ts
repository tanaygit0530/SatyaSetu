/**
 * SatyaSetu Authentication Client Utilities
 * Manages JWT tokens, user profiles, and session storage safely with SSR guards.
 */

export interface AuthUser {
  user_id: string;
  phone_number: string;
  created_at?: string;
  updated_at?: string;
  verified?: boolean;
  status?: string;
}

const TOKEN_KEY = 'satyasetu_jwt_token';
const USER_KEY = 'satyasetu_auth_user';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(TOKEN_KEY, token);
    window.dispatchEvent(new Event('auth-change'));
  } catch (e) {
    console.error('Failed to store auth token:', e);
  }
}

export function getUser(): AuthUser | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setUser(user: AuthUser): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    window.dispatchEvent(new Event('auth-change'));
  } catch (e) {
    console.error('Failed to store auth user:', e);
  }
}

export function clearAuth(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.dispatchEvent(new Event('auth-change'));
  } catch (e) {
    console.error('Failed to clear auth:', e);
  }
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return {
      Authorization: `Bearer ${token}`,
    };
  }
  return {};
}
