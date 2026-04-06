import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    '[PropIntel] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY is not set. ' +
      'Add them to frontend/.env (Supabase Dashboard → Project Settings → API).'
  )
}

export const supabase = createClient(supabaseUrl ?? '', supabaseAnonKey ?? '')
