import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { SettingsPage } from '@/pages/SettingsPage'
import { ProductCard } from '@/components/products/ProductCard'
import { useCurrency } from '@/contexts/CurrencyContext'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import * as apiModule from '@/lib/api'
import { defaultProfileResponse } from './setup'
import { clearAuthStorage, renderWithProviders } from './test-utils'
import { makeProductSummary } from './product-fixtures'

vi.mock('@/hooks/useNotifications', () => ({
  useUnreadNotificationCount: vi.fn(() => ({
    data: 0,
    isLoading: false,
    isError: false,
  })),
  useNotifications: vi.fn(),
  useMarkNotificationsRead: vi.fn(),
  useNotificationAction: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn() }),
}))

import { toast } from 'sonner'

const FX_RATES = {
  base: 'CAD' as const,
  fetched_at: '2026-06-14T12:00:00.000Z',
  stale: false,
  rates: {
    CAD: '1',
    USD: '0.74',
    EUR: '0.68',
    GBP: '0.53',
  },
}

function PricePreview() {
  const formatPriceCents = useFormatPriceCents()
  return <p>{formatPriceCents(12999)}</p>
}

function CurrencyReader() {
  const { currency } = useCurrency()
  return <p>Currency: {currency}</p>
}

describe('display price formatting', () => {
  beforeEach(() => {
    clearAuthStorage()
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
    vi.mocked(toast.error).mockClear()
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return defaultProfileResponse
      }
      if (path === '/api/fx/rates') {
        return FX_RATES
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        return { ...defaultProfileResponse, display_currency: 'USD' }
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows CAD prices by default', async () => {
    renderWithProviders(<PricePreview />, { authenticated: true })

    expect(await screen.findByText('$129.99')).toBeInTheDocument()
  })

  it('converts prices when display currency is USD', async () => {
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path) => {
      if (path === '/api/profile') {
        return { ...defaultProfileResponse, display_currency: 'USD' }
      }
      if (path === '/api/fx/rates') {
        return FX_RATES
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    renderWithProviders(
      <>
        <CurrencyReader />
        <PricePreview />
      </>,
      { authenticated: true },
    )

    expect(await screen.findByText('Currency: USD')).toBeInTheDocument()
    expect(await screen.findByText('US$96.19')).toBeInTheDocument()
  })

  it('falls back to CAD when FX rates fail', async () => {
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path) => {
      if (path === '/api/profile') {
        return { ...defaultProfileResponse, display_currency: 'USD' }
      }
      if (path === '/api/fx/rates') {
        throw new apiModule.ApiError(503, 'FX unavailable')
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    renderWithProviders(<PricePreview />, { authenticated: true })

    expect(await screen.findByText('$129.99')).toBeInTheDocument()
  })
})

describe('currency profile sync', () => {
  beforeEach(() => {
    clearAuthStorage()
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
    localStorage.setItem('display-currency', 'CAD')
    vi.mocked(toast.error).mockClear()
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return { ...defaultProfileResponse, display_currency: 'EUR' }
      }
      if (path === '/api/fx/rates') {
        return FX_RATES
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        return { ...defaultProfileResponse, display_currency: 'USD' }
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('hydrates currency from profile on login', async () => {
    renderWithProviders(<CurrencyReader />, { authenticated: true })

    expect(await screen.findByText('Currency: EUR')).toBeInTheDocument()
    expect(localStorage.getItem('display-currency')).toBe('EUR')
  })

  it('PATCHes profile when settings currency changes', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    await screen.findByRole('heading', { name: /^display$/i })
    await user.click(screen.getByRole('radio', { name: /^usd$/i }))

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ display_currency: 'USD' }),
      })
    })
    expect(localStorage.getItem('display-currency')).toBe('USD')
  })

  it('reverts currency and shows toast when PATCH fails', async () => {
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return defaultProfileResponse
      }
      if (path === '/api/fx/rates') {
        return FX_RATES
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        throw new apiModule.ApiError(500, 'save failed')
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    await screen.findByRole('heading', { name: /^display$/i })
    await user.click(screen.getByRole('radio', { name: /^usd$/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Couldn't save currency preference")
    })
    expect(screen.getByRole('radio', { name: /^cad$/i })).toBeChecked()
    expect(localStorage.getItem('display-currency')).toBe('CAD')
  })
})

describe('ProductCard price display', () => {
  beforeEach(() => {
    clearAuthStorage()
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path) => {
      if (path === '/api/profile') return defaultProfileResponse
      if (path === '/api/fx/rates') return FX_RATES
      throw new Error(`Unexpected apiFetch: ${path}`)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders converted best price on dashboard card', async () => {
    localStorage.setItem('display-currency', 'USD')
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path) => {
      if (path === '/api/profile') {
        return { ...defaultProfileResponse, display_currency: 'USD' }
      }
      if (path === '/api/fx/rates') return FX_RATES
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    renderWithProviders(
      <ProductCard product={makeProductSummary({ best_price_cents: 10000 })} />,
      { authenticated: true },
    )

    expect(await screen.findByText('US$74.00')).toBeInTheDocument()
  })
})
