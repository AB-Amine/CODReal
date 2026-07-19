"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  configured: boolean;
  accessToken: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Fresh access token (refreshes session if needed). */
  getAccessToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const configured = isSupabaseConfigured();
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(configured);

  useEffect(() => {
    if (!configured) {
      setLoading(false);
      return;
    }
    const supabase = createClient();
    if (!supabase) {
      setLoading(false);
      return;
    }

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setUser(next?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, [configured]);

  const signIn = useCallback(async (email: string, password: string) => {
    const supabase = createClient();
    if (!supabase) throw new Error("Supabase non configuré");
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
    setSession(data.session);
    setUser(data.user);
  }, []);

  const signUp = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const supabase = createClient();
      if (!supabase) throw new Error("Supabase non configuré");
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { full_name: fullName || "" } },
      });
      if (error) throw error;
      // If email confirmation is disabled, session is returned immediately
      if (data.session) {
        setSession(data.session);
        setUser(data.user);
      } else {
        // Try sign-in in case confirm is off but session missing
        const login = await supabase.auth.signInWithPassword({ email, password });
        if (!login.error && login.data.session) {
          setSession(login.data.session);
          setUser(login.data.user);
        }
      }
    },
    []
  );

  const signOut = useCallback(async () => {
    const supabase = createClient();
    if (!supabase) return;
    await supabase.auth.signOut();
    setSession(null);
    setUser(null);
  }, []);

  const getAccessToken = useCallback(async () => {
    const supabase = createClient();
    if (!supabase) return null;
    const { data, error } = await supabase.auth.getSession();
    if (error) return null;
    const s = data.session;
    if (!s) return null;
    // Refresh if expiring within 60s
    const exp = s.expires_at ? s.expires_at * 1000 : 0;
    if (exp && exp - Date.now() < 60_000) {
      const refreshed = await supabase.auth.refreshSession();
      if (refreshed.data.session) {
        setSession(refreshed.data.session);
        setUser(refreshed.data.session.user);
        return refreshed.data.session.access_token;
      }
    }
    setSession(s);
    setUser(s.user);
    return s.access_token;
  }, []);

  const value = useMemo(
    () => ({
      user,
      session,
      loading,
      configured,
      accessToken: session?.access_token ?? null,
      signIn,
      signUp,
      signOut,
      getAccessToken,
    }),
    [
      user,
      session,
      loading,
      configured,
      signIn,
      signUp,
      signOut,
      getAccessToken,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
