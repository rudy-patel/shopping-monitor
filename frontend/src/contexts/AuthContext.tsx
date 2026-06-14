/**
 * Google OAuth via Supabase is live on the login page.
 * signInDev remains for the no-Supabase local-agent path (non-production builds only).
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { useQueryClient } from '@tanstack/react-query'
import { isDevBuild } from '@/lib/env'
import { getSupabaseClient, isSupabaseConfigured } from '@/lib/supabase'

const DEV_AUTH_STORAGE_KEY = 'shopping-monitor-dev-auth'

const DEV_PLACEHOLDER_USER: User = {
  id: 'dev-user',
  email: 'dev@local',
  app_metadata: {},
  user_metadata: {},
  aud: 'authenticated',
  created_at: new Date().toISOString(),
}

export interface AuthContextValue {
  session: Session | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  signInWithGoogle: () => Promise<void>
  signInDev: () => void
  signOut: () => Promise<void>
  isDevLoginAvailable: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readDevAuthFlag(): boolean {
  try {
    return localStorage.getItem(DEV_AUTH_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function writeDevAuthFlag(enabled: boolean): void {
  try {
    if (enabled) {
      localStorage.setItem(DEV_AUTH_STORAGE_KEY, 'true')
    } else {
      localStorage.removeItem(DEV_AUTH_STORAGE_KEY)
    }
  } catch {
    // ignore storage errors in restricted environments
  }
}

function createDevSession(): Session {
  return {
    access_token: 'dev-token',
    refresh_token: 'dev-refresh',
    expires_in: 3600,
    token_type: 'bearer',
    user: DEV_PLACEHOLDER_USER,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSession] = useState<Session | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const isDevLoginAvailable = isDevBuild()

  useEffect(() => {
    const supabase = getSupabaseClient()

    if (!supabase) {
      if (isDevLoginAvailable && readDevAuthFlag()) {
        const devSession = createDevSession()
        setSession(devSession)
        setUser(DEV_PLACEHOLDER_USER)
      }
      setIsLoading(false)
      return
    }

    let mounted = true

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return
      setSession(data.session)
      setUser(data.session?.user ?? null)
      setIsLoading(false)
    })

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setUser(nextSession?.user ?? null)
      setIsLoading(false)
    })

    return () => {
      mounted = false
      subscription.subscription.unsubscribe()
    }
  }, [isDevLoginAvailable])

  const signInWithGoogle = useCallback(async () => {
    const supabase = getSupabaseClient()
    if (!supabase) {
      throw new Error('Supabase is not configured')
    }
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  }, [])

  const signInDev = useCallback(() => {
    if (!isDevLoginAvailable) {
      throw new Error('Dev login is only available in local development builds')
    }
    const devSession = createDevSession()
    writeDevAuthFlag(true)
    setSession(devSession)
    setUser(DEV_PLACEHOLDER_USER)
    setIsLoading(false)
  }, [isDevLoginAvailable])

  const signOut = useCallback(async () => {
    writeDevAuthFlag(false)
    const supabase = getSupabaseClient()
    if (supabase && isSupabaseConfigured()) {
      await supabase.auth.signOut()
    }
    setSession(null)
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      signInWithGoogle,
      signInDev,
      signOut,
      isDevLoginAvailable,
    }),
    [session, user, isLoading, signInWithGoogle, signInDev, signOut, isDevLoginAvailable],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
