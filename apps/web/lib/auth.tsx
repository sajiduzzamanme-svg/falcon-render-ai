"use client";

import type { Session, User } from "@supabase/supabase-js";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getSupabase, isSupabaseConfigured } from "./supabase";

interface AuthContextValue {
  configured: boolean;
  loading: boolean;
  user: User | null;
  session: Session | null;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  configured: false,
  loading: true,
  user: null,
  session: null,
  signOut: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    if (!isSupabaseConfigured()) {
      setLoading(false);
      return;
    }
    const supabase = getSupabase();
    let mounted = true;
    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (mounted) {
          setSession(data.session);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, next) => {
      if (mounted) setSession(next);
    });
    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const signOut = useCallback(async () => {
    if (!isSupabaseConfigured()) return;
    await getSupabase().auth.signOut();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      configured: isSupabaseConfigured(),
      loading,
      user: session?.user ?? null,
      session,
      signOut,
    }),
    [loading, session, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
