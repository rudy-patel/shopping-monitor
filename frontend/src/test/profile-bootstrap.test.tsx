import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { vi } from 'vitest'
import * as apiModule from '@/lib/api'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { useUpdateProfile } from '@/hooks/useProfile'
import { clearAuthStorage, createTestQueryClient, ProviderStack } from './test-utils'
import { defaultProfileResponse } from './setup'

function ProtectedContent() {
  return <h1>Protected Content</h1>
}

function renderProtectedRouteWithSharedClient() {
  localStorage.setItem('shopping-monitor-dev-auth', 'true')
  const queryClient = createTestQueryClient()
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
    <ProviderStack queryClient={queryClient}>
      <RouterProvider router={memoryRouter} />
    </ProviderStack>
  )

  return { ...render(tree), tree, queryClient }
}

describe('profile bootstrap', () => {
  beforeEach(() => {
    clearAuthStorage()
    vi.spyOn(apiModule, 'apiFetch').mockResolvedValue(defaultProfileResponse)
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
      ...defaultProfileResponse,
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
