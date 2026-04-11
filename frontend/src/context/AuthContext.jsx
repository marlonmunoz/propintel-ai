import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { fetchProfile, fetchQuota } from '../services/authApi'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState(null)
  const [quota, setQuota] = useState(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  const refreshProfile = useCallback(async () => {
    if (!session?.access_token) {
      setProfile(null)
      return
    }
    try {
      const data = await fetchProfile()
      setProfile(data)
    } catch {
      setProfile(null)
    }
  }, [session?.access_token])

  const refreshQuota = useCallback(async () => {
    if (!session?.access_token) {
      setQuota(null)
      return
    }
    try {
      const data = await fetchQuota()
      setQuota(data)
    } catch {
      setQuota(null)
    }
  }, [session?.access_token])

  // Load FastAPI `profiles` row (creates on first GET /auth/me).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- refreshProfile updates profile from API when session changes
    void refreshProfile()
  }, [refreshProfile])

  // Fetch quota whenever the session changes (login / logout / token refresh).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- refreshQuota updates quota from API when session changes
    void refreshQuota()
  }, [refreshQuota])

  const signOut = async () => {
    setProfile(null)
    setQuota(null)
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider
      value={{
        session,
        user: session?.user ?? null,
        profile,
        refreshProfile,
        quota,
        refreshQuota,
        signOut,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components -- companion hook for AuthProvider
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
