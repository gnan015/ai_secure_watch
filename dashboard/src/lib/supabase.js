import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const isDevelopment = import.meta.env.DEV;

if (isDevelopment && (!supabaseUrl || !supabaseAnonKey)) {
  console.warn(
    "Supabase dashboard client is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to enable V2 auth work."
  );
}

export const supabase = createClient(supabaseUrl || "", supabaseAnonKey || "");
