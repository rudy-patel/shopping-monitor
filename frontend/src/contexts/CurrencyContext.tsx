/**
 * Display currency is synced across React state, localStorage, and profiles.display_currency.
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

export const CURRENCIES = ['CAD', 'USD', 'EUR', 'GBP'] as const
export type Currency = (typeof CURRENCIES)[number]

const CURRENCY_STORAGE_KEY = 'display-currency'
const DEFAULT_CURRENCY: Currency = 'CAD'

interface CurrencyContextValue {
  currency: Currency
  setCurrency: (currency: Currency) => void
}

const CurrencyContext = createContext<CurrencyContextValue | null>(null)

function isCurrency(value: string): value is Currency {
  return (CURRENCIES as readonly string[]).includes(value)
}

function readStoredCurrency(): Currency {
  try {
    const stored = localStorage.getItem(CURRENCY_STORAGE_KEY)
    if (stored && isCurrency(stored)) {
      return stored
    }
  } catch {
    // ignore storage errors
  }
  return DEFAULT_CURRENCY
}

function writeStoredCurrency(currency: Currency) {
  try {
    localStorage.setItem(CURRENCY_STORAGE_KEY, currency)
  } catch {
    // ignore storage errors
  }
}

function CurrencyProfileSync({
  onHydrate,
}: {
  onHydrate: (currency: Currency) => void
}) {
  const { isAuthenticated } = useAuth()
  const { data: profile } = useProfile()
  const hydratedUserRef = useRef<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated || !profile) return
    if (hydratedUserRef.current === profile.user_id) return
    hydratedUserRef.current = profile.user_id
    onHydrate(profile.display_currency)
  }, [isAuthenticated, onHydrate, profile])

  return null
}

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<Currency>(() => readStoredCurrency())
  const { isAuthenticated } = useAuth()
  const updateProfile = useUpdateProfile()
  const pendingCurrencyRef = useRef<Currency | null>(null)

  const hydrateFromProfile = useCallback((next: Currency) => {
    setCurrencyState(next)
    writeStoredCurrency(next)
  }, [])

  const setCurrency = useCallback(
    (next: Currency) => {
      if (next === currency) return

      const previous = currency
      pendingCurrencyRef.current = next
      setCurrencyState(next)
      writeStoredCurrency(next)

      if (!isAuthenticated) return

      updateProfile.mutate(
        { display_currency: next },
        {
          onSuccess: () => {
            pendingCurrencyRef.current = null
          },
          onError: () => {
            if (pendingCurrencyRef.current === next) {
              setCurrencyState(previous)
              writeStoredCurrency(previous)
              pendingCurrencyRef.current = null
            }
            toast.error("Couldn't save currency preference")
          },
        },
      )
    },
    [currency, isAuthenticated, updateProfile],
  )

  const value = useMemo(() => ({ currency, setCurrency }), [currency, setCurrency])

  return (
    <CurrencyContext.Provider value={value}>
      <CurrencyProfileSync onHydrate={hydrateFromProfile} />
      {children}
    </CurrencyContext.Provider>
  )
}

export function useCurrency(): CurrencyContextValue {
  const context = useContext(CurrencyContext)
  if (!context) {
    throw new Error('useCurrency must be used within CurrencyProvider')
  }
  return context
}
