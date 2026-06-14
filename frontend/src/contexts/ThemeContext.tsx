/**
 * Theme preference is synced across React state, localStorage, and profiles.theme.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/contexts/AuthContext'
import { useProfile, useUpdateProfile } from '@/hooks/useProfile'

export type Theme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'theme'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function readStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    return stored === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

function writeStoredTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // ignore storage errors
  }
}

function applyThemeClass(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

function ThemeProfileSync({ onHydrate }: { onHydrate: (theme: Theme) => void }) {
  const { isAuthenticated } = useAuth()
  const { data: profile } = useProfile()
  const hydratedUserRef = useRef<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated || !profile) return
    if (hydratedUserRef.current === profile.user_id) return
    hydratedUserRef.current = profile.user_id
    onHydrate(profile.theme)
  }, [isAuthenticated, onHydrate, profile])

  return null
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => readStoredTheme())
  const { isAuthenticated } = useAuth()
  const updateProfile = useUpdateProfile()
  const pendingThemeRef = useRef<Theme | null>(null)

  useEffect(() => {
    applyThemeClass(theme)
    writeStoredTheme(theme)
  }, [theme])

  const hydrateFromProfile = useCallback((next: Theme) => {
    setThemeState(next)
  }, [])

  const setTheme = useCallback(
    (next: Theme) => {
      if (next === theme) return

      const previous = theme
      pendingThemeRef.current = next
      setThemeState(next)
      writeStoredTheme(next)
      applyThemeClass(next)

      if (!isAuthenticated) return

      updateProfile.mutate(
        { theme: next },
        {
          onSuccess: () => {
            pendingThemeRef.current = null
          },
          onError: () => {
            if (pendingThemeRef.current === next) {
              setThemeState(previous)
              writeStoredTheme(previous)
              applyThemeClass(previous)
              pendingThemeRef.current = null
            }
            toast.error("Couldn't save theme preference")
          },
        },
      )
    },
    [isAuthenticated, theme, updateProfile],
  )

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }, [setTheme, theme])

  const value = useMemo(
    () => ({ theme, toggleTheme, setTheme }),
    [theme, toggleTheme, setTheme],
  )

  return (
    <ThemeContext.Provider value={value}>
      <ThemeProfileSync onHydrate={hydrateFromProfile} />
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}
