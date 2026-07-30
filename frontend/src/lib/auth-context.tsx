"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  type User as FirebaseUser,
} from "firebase/auth";
import { getFirebaseAuth, isFirebaseConfigured } from "@/lib/firebase/client";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

export type AuthUserSummary = {
  id: string;
  email: string | null;
  displayName?: string | null;
};

type AuthContextValue = {
  user: AuthUserSummary | null;
  session: unknown | null;
  loading: boolean;
  configured: boolean;
  accessToken: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const fbConfigured = isFirebaseConfigured();
  const sbConfigured = isSupabaseConfigured();
  const configured = fbConfigured || sbConfigured;

  const [user, setUser] = useState<AuthUserSummary | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(configured);

  useEffect(() => {
    if (!configured) {
      setLoading(false);
      return;
    }

    if (fbConfigured) {
      const auth = getFirebaseAuth();
      if (!auth) {
        setLoading(false);
        return;
      }
      const unsubscribe = onAuthStateChanged(auth, async (fbUser: FirebaseUser | null) => {
        if (fbUser) {
          const idToken = await fbUser.getIdToken();
          setToken(idToken);
          setUser({
            id: fbUser.uid,
            email: fbUser.email,
            displayName: fbUser.displayName,
          });
        } else {
          setToken(null);
          setUser(null);
        }
        setLoading(false);
      });

      return () => unsubscribe();
    } else if (sbConfigured) {
      const supabase = createClient();
      if (!supabase) {
        setLoading(false);
        return;
      }

      supabase.auth.getSession().then(({ data }) => {
        if (data.session?.user) {
          setToken(data.session.access_token);
          setUser({
            id: data.session.user.id,
            email: data.session.user.email ?? null,
          });
        }
        setLoading(false);
      });

      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((_event, next) => {
        if (next?.user) {
          setToken(next.access_token);
          setUser({
            id: next.user.id,
            email: next.user.email ?? null,
          });
        } else {
          setToken(null);
          setUser(null);
        }
        setLoading(false);
      });

      return () => subscription.unsubscribe();
    }
  }, [configured, fbConfigured, sbConfigured]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (fbConfigured) {
        const auth = getFirebaseAuth();
        if (!auth) throw new Error("Firebase non configuré");
        const cred = await signInWithEmailAndPassword(auth, email, password);
        const idToken = await cred.user.getIdToken();
        setToken(idToken);
        setUser({
          id: cred.user.uid,
          email: cred.user.email,
          displayName: cred.user.displayName,
        });
      } else if (sbConfigured) {
        const supabase = createClient();
        if (!supabase) throw new Error("Supabase non configuré");
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        setToken(data.session.access_token);
        setUser({
          id: data.user.id,
          email: data.user.email ?? null,
        });
      }
    },
    [fbConfigured, sbConfigured]
  );

  const signUp = useCallback(
    async (email: string, password: string, fullName?: string) => {
      if (fbConfigured) {
        const auth = getFirebaseAuth();
        if (!auth) throw new Error("Firebase non configuré");
        const cred = await createUserWithEmailAndPassword(auth, email, password);
        if (fullName) {
          await updateProfile(cred.user, { displayName: fullName });
        }
        const idToken = await cred.user.getIdToken();
        setToken(idToken);
        setUser({
          id: cred.user.uid,
          email: cred.user.email,
          displayName: fullName || cred.user.displayName,
        });
      } else if (sbConfigured) {
        const supabase = createClient();
        if (!supabase) throw new Error("Supabase non configuré");
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: fullName || "" } },
        });
        if (error) throw error;
        if (data.session) {
          setToken(data.session.access_token);
          setUser({
            id: data.user.id,
            email: data.user.email ?? null,
          });
        }
      }
    },
    [fbConfigured, sbConfigured]
  );

  const signOut = useCallback(async () => {
    if (fbConfigured) {
      const auth = getFirebaseAuth();
      if (auth) await firebaseSignOut(auth);
    } else if (sbConfigured) {
      const supabase = createClient();
      if (supabase) await supabase.auth.signOut();
    }
    setToken(null);
    setUser(null);
  }, [fbConfigured, sbConfigured]);

  const getAccessToken = useCallback(async () => {
    if (fbConfigured) {
      const auth = getFirebaseAuth();
      if (!auth || !auth.currentUser) return null;
      return auth.currentUser.getIdToken(true);
    } else if (sbConfigured) {
      const supabase = createClient();
      if (!supabase) return null;
      const { data } = await supabase.auth.getSession();
      return data.session?.access_token ?? null;
    }
    return token;
  }, [fbConfigured, sbConfigured, token]);

  const value = useMemo(
    () => ({
      user,
      session: token ? { access_token: token } : null,
      loading,
      configured,
      accessToken: token,
      signIn,
      signUp,
      signOut,
      getAccessToken,
    }),
    [
      user,
      token,
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
