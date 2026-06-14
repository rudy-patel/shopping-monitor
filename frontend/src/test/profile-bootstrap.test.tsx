import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { vi } from 'vitest'
import * as apiModule from '@/lib/api'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { AuthProvider } from '@/contexts/AuthContext'
import { CurrencyProvider } from '@/contexts/CurrencyContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useUpdateProfile } from '@/hooks/useProfile'
import { clearAuthStorage, ProviderStack } from './test-utils'

const cannedProfile = {
  user_id: '00000000-0000-0000-0000-000000000001',
  display_currency: 'CAD' as const,
  default_threshold_pct: 20,
  notifications_enabled: true,
  email_digest_enabled: true,
  theme: 'light' as const,
  revisit_prompts_enabled: true,
  revisit_on_sale_enabled: true,
  revisit_stale_enabled: true,
  revisit_stale_days: 30,
  created_at: '2026-06-14T00:00:00.000Z',
  updated_at: '2026-06-14T00:00:00.000Z',
}

function ProtectedContent() {
  return <h1>Protected Content</h1>
}

function renderProtectedRouteWithSharedClient() {
  localStorage.setItem('shopping-monitor-dev-auth', 'true')
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const memoryRouter = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [{ path: '/', element: <ProtectedContent /> }],
      },
    ],
    { initialEntries: ['/'] },
  )

  const tree = (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <CurrencyProvider>
            <RouterProvider router={memoryRouter} />
          </CurrencyProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )

  return { ...render(tree), tree, queryClient }
}

describe('profile bootstrap', () => {
  beforeEach(() => {
    clearAuthStorage()
    vi.spyOn(apiModule, 'apiFetch').mockResolvedValue(cannedProfile)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('ProtectedRoute triggers GET /api/profile when authenticated', async () => {
    renderProtectedRouteWithSharedClient()

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile')
    })
    expect(apiModule.apiFetch).toHaveBeenCalledTimes(1)
  })

  it('reuses cached profile without a second GET on re-render', async () => {
    const { rerender, tree } = renderProtectedRouteWithSharedClient()

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledTimes(1)
    })

    rerender(tree)

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledTimes(1)
    })
  })
})

function UpdateProfileButton() {
  const mutation = useUpdateProfile()
  return (
    <button type="button" onClick={() => mutation.mutate({ display_currency: 'USD' })}>
      Update profile
    </button>
  )
}

describe('useUpdateProfile', () => {
  beforeEach(() => {
    clearAuthStorage()
    vi.spyOn(apiModule, 'apiFetch').mockResolvedValue({
      ...cannedProfile,
      display_currency: 'USD',
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('PATCHes profile and updates cache', async () => {
    const user = userEvent.setup()
    render(
      <ProviderStack>
        <UpdateProfileButton />
      </ProviderStack>,
    )

    await user.click(screen.getByRole('button', { name: /update profile/i }))

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ display_currency: 'USD' }),
      })
    })
  })
})
