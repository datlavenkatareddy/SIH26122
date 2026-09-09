import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase, isSupabaseConfigured } from '@/lib/supabase';
import { authApi } from '@/api';

export type UserRole = 'SITE_ENGINEER' | 'SUPERVISOR';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  isLoading: boolean;
  error: string | null;
  devMode: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const TOKEN_KEY = 'supabase_access_token';
const DEV_EMAIL_KEY = 'setu_dev_email_v1';

// Local dev-mode fallback, used only when VITE_SUPABASE_URL/ANON_KEY aren't
// configured (see lib/supabase.ts). These ids are the same fixed
// TEST_SITE_ENGINEER_ID/TEST_SUPERVISOR_ID backend/shared/seed.py seeds
// into the real `profiles` table for local/test environments -- login here
// mints an unsigned dev token carrying one of these as its `sub` claim and
// hands it to the real backend, which resolves the actual role from that
// profiles row via shared/auth.py's explicit AUTH_DEV_MODE fallback. This
// is not a UI-only fake: it round-trips through the real backend and its
// real database, so a misconfigured/missing profile genuinely fails.
//
// ─── REGRESSION GUARD ───────────────────────────────────────────────────────
// The role shown in the UI is NOT determined by anything in this map.
// It is resolved exclusively by the backend from the `profiles` DB row whose
// `id` matches the `sub` claim in the minted dev token (via authApi.getMe()
// → GET /api/v1/auth/me). The `id` field here is the only thing that matters.
//
// When adding a new demo account:
//   1. Add an entry here with the correct UUID from the `profiles` table.
//   2. Ensure backend/shared/seed.py seeds a matching row with that UUID,
//      the correct `role` ('SITE_ENGINEER' or 'SUPERVISOR'), and `full_name`.
//   3. Do NOT assume the role from another account's UUID will carry over —
//      each UUID maps to exactly one `profiles` row and therefore one role.
//   4. Verify by logging in and confirming the redirect:
//      SITE_ENGINEER  →  /intake
//      SUPERVISOR     →  /digest
// ────────────────────────────────────────────────────────────────────────────
const DEV_MODE_ACCOUNTS: Record<string, { password: string; id: string }> = {
  'site.engineer@sih26122.internal': { password: 'Demo123456!', id: '811a1e0f-976d-42ea-a37f-1096186daf36' },
  'supervisor@sih26122.internal': { password: 'Demo123456!', id: '4b8e6901-de81-490c-8bec-9761f62bee70' },
  'engineer@setu.ai': { password: 'Demo123456!', id: '811a1e0f-976d-42ea-a37f-1096186daf36' },
  'planner@setu.ai': { password: 'Demo123456!', id: '4b8e6901-de81-490c-8bec-9761f62bee70' },
};

function base64UrlEncode(obj: unknown): string {
  const json = JSON.stringify(obj);
  const b64 = btoa(unescape(encodeURIComponent(json)));
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// An unsigned JWT-shaped token: three dot-separated segments so PyJWT's
// jwt.decode(..., options={"verify_signature": False}) on the backend can
// parse it structurally. It carries no real signature -- backend/shared/
// auth.py only accepts this path when AUTH_DEV_MODE=true AND no real
// Supabase verification config is present; every other path (JWKS, HMAC
// secret, live Supabase HTTP check) rejects it outright.
function mintDevToken(userId: string): string {
  const header = base64UrlEncode({ alg: 'none', typ: 'JWT' });
  const payload = base64UrlEncode({ sub: userId, iat: Math.floor(Date.now() / 1000) });
  return `${header}.${payload}.`;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  // Resolves the authenticated role/profile from the REAL backend --
  // never trusted from anything set client-side, in either auth mode.
  const hydrateFromBackend = async (email: string): Promise<User> => {
    const profile = await authApi.getMe();
    return {
      id: profile.id,
      email,
      full_name: profile.full_name,
      role: profile.role,
    };
  };

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      try {
        if (isSupabaseConfigured && supabase) {
          const { data } = await supabase.auth.getSession();
          const session = data.session;
          if (session?.access_token) {
            localStorage.setItem(TOKEN_KEY, session.access_token);
            const restored = await hydrateFromBackend(session.user?.email ?? '');
            if (!cancelled) setUser(restored);
          }
        } else {
          const token = localStorage.getItem(TOKEN_KEY);
          const email = localStorage.getItem(DEV_EMAIL_KEY);
          if (token && email) {
            const restored = await hydrateFromBackend(email);
            if (!cancelled) setUser(restored);
          }
        }
      } catch {
        // Stale/invalid token -- clear it and fall through to the login screen
        // rather than getting stuck on a broken session.
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(DEV_EMAIL_KEY);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    restoreSession();

    if (isSupabaseConfigured && supabase) {
      const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.access_token) {
          localStorage.setItem(TOKEN_KEY, session.access_token);
        } else {
          localStorage.removeItem(TOKEN_KEY);
          setUser(null);
        }
      });
      return () => {
        cancelled = true;
        subscription.subscription.unsubscribe();
      };
    }

    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    setError(null);
    setLoading(true);
    const emailTrimmed = email.trim().toLowerCase();

    try {
      if (isSupabaseConfigured && supabase) {
        const { data, error: authError } = await supabase.auth.signInWithPassword({
          email: emailTrimmed,
          password,
        });
        if (authError || !data.session) {
          throw new Error(authError?.message || 'Sign-in failed.');
        }
        localStorage.setItem(TOKEN_KEY, data.session.access_token);
        const loggedInUser = await hydrateFromBackend(data.session.user?.email ?? emailTrimmed);
        setUser(loggedInUser);
        return;
      }

      // Dev-mode fallback (no Supabase project configured).
      const account = DEV_MODE_ACCOUNTS[emailTrimmed];
      if (!account || account.password !== password) {
        throw new Error('Incorrect email or password.');
      }
      const devToken = mintDevToken(account.id);
      localStorage.setItem(TOKEN_KEY, devToken);
      localStorage.setItem(DEV_EMAIL_KEY, emailTrimmed);
      const loggedInUser = await hydrateFromBackend(emailTrimmed);
      setUser(loggedInUser);
    } catch (err: any) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(DEV_EMAIL_KEY);
      const message = err?.message || 'Login failed.';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    if (isSupabaseConfigured && supabase) {
      await supabase.auth.signOut();
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(DEV_EMAIL_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        isLoading: loading,
        error,
        devMode: !isSupabaseConfigured,
        login,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
