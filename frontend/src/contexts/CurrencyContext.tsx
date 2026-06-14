/**
 * Display currency is stored locally. T4.1/T4.2: hydrate from profiles.display_currency and persist via PATCH /api/profile.
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

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<Currency>(() => readStoredCurrency())

  useEffect(() => {
    try {
      localStorage.setItem(CURRENCY_STORAGE_KEY, currency)
    } catch {
      // ignore storage errors
    }
  }, [currency])

  const setCurrency = useCallback((next: Currency) => {
    setCurrencyState(next)
  }, [])

  const value = useMemo(() => ({ currency, setCurrency }), [currency, setCurrency])

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>
}

export function useCurrency(): CurrencyContextValue {
  const context = useContext(CurrencyContext)
  if (!context) {
    throw new Error('useCurrency must be used within CurrencyProvider')
  }
  return context
}
