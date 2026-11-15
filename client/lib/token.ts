/**
 * Access-token storage shared by the client and server components.
 *
 * The token lives in localStorage for browser fetches and is mirrored into a
 * same-origin cookie so React Server Components (the competitor brief page) can
 * forward it to the API. The cookie is intentionally JS-readable because this
 * setup has no same-origin Next proxy; move to an httpOnly cookie + route
 * handler before production if XSS is a concern.
 */

const TOKEN_KEY = "nexus-intel:token";
export const TOKEN_COOKIE = "nexus_intel_token";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

export function readStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage can be disabled (private mode); the session still works for the
    // current tab because the cookie below is set independently.
  }
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}; Path=/; Max-Age=${MAX_AGE_SECONDS}; SameSite=Lax`;
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Ignore storage failures.
  }
  document.cookie = `${TOKEN_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}
