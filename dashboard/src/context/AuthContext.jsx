import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import supabase from "../lib/supabase.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadSession() {
      const { data, error } = await supabase.auth.getSession();

      if (!isMounted) {
        return;
      }

      if (error) {
        console.warn("Supabase session could not be loaded.", error.message);
      }

      const currentSession = data?.session ?? null;
      setSession(currentSession);
      setUser(currentSession?.user ?? null);
      setLoading(false);
    }

    loadSession();

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setUser(nextSession?.user ?? null);
      setLoading(false);
    });

    return () => {
      isMounted = false;
      data?.subscription?.unsubscribe();
    };
  }, []);

  async function signOut() {
    return supabase.auth.signOut();
  }

  const value = useMemo(
    () => ({
      session,
      user,
      loading,
      signOut,
    }),
    [loading, session, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
