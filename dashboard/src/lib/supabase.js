import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const isDevelopment = import.meta.env.DEV;
const hasSupabaseConfig = Boolean(supabaseUrl && supabaseAnonKey);

if (isDevelopment && !hasSupabaseConfig) {
  console.warn(
    "Supabase dashboard client is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to enable V2 auth work."
  );
}

const missingConfigClient = {
  auth: {
    async getSession() {
      return { data: { session: null }, error: null };
    },
    onAuthStateChange() {
      return {
        data: {
          subscription: {
            unsubscribe() {},
          },
        },
      };
    },
    async signInWithPassword() {
      return {
        data: { session: null, user: null },
        error: {
          message:
            "Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.",
        },
      };
    },
    async signInWithOAuth() {
      return {
        data: { provider: null, url: null },
        error: {
          message:
            "Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.",
        },
      };
    },
    async signOut() {
      return { error: null };
    },
  },
};

export const supabase = hasSupabaseConfig
  ? createClient(supabaseUrl, supabaseAnonKey)
  : missingConfigClient;

export default supabase;
