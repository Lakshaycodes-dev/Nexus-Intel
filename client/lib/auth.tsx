"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  getCurrentUser,
  loginAccount,
  logoutAccount,
  registerAccount,
  type AuthUser,
  type RegisterInput,
} from "./api";
import { clearRecentAnalyses } from "./recent";
import { clearStoredToken, readStoredToken, storeToken } from "./token";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (input: RegisterInput) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Holds the signed-in account for the whole app.
 *
 * On mount the stored token is validated against `GET /auth/me`; an expired or
 * tampered token is discarded so the UI never trusts stale localStorage.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function restore() {
      // Yield first so the state updates below are not synchronous renders
      // inside the effect body.
      await Promise.resolve();
      if (!active) return;

      const token = readStoredToken();
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const current = await getCurrentUser();
        if (active) setUser(current);
      } catch {
        if (!active) return;
        clearStoredToken();
        setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    }

    restore();

    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const response = await loginAccount({ email, password });
    storeToken(response.access_token);
    setUser(response.user);
  }, []);

  const signUp = useCallback(async (input: RegisterInput) => {
    const response = await registerAccount(input);
    storeToken(response.access_token);
    setUser(response.user);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logoutAccount();
    } catch {
      // Logout is stateless: clear the local session even if the API is down.
    }
    clearStoredToken();
    clearRecentAnalyses();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, signIn, signUp, signOut }),
    [user, loading, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider.");
  }
  return context;
}
