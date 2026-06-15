import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { SearchCommandDialog } from '@/components/search/SearchCommandDialog'
import { useCreateProduct } from '@/hooks/useProducts'
import * as apiModule from '@/lib/api'
import type { SearchResponse } from '@/lib/search'
import { renderWithProviders } from './test-utils'

const mockNavigate = vi.fn()

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn() }),
  Toaster: () => null,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/hooks/useProducts', () => ({
  useCreateProduct: vi.fn(),
}))

const mockMutate = vi.fn()

const baseResponse: SearchResponse = {
  query: 'airpods pro',
  cache_hit: false,
  latency_ms: 320,
  results: [
    {
      title: 'AirPods Pro (USB-C)',
      retailer_slug: 'apple_ca',
      retailer_label: 'Apple Canada',
      url: 'https://apple.com/ca/airpods-pro',
      supported: true,
      brand_hint: 'Apple',
      justification: 'Apple Canada PDP',
    },
    {
      title: 'AirPods Pro (USB-C) at Best Buy Canada',
      retailer_slug: 'bestbuy_ca',
      retailer_label: 'Best Buy Canada',
      url: 'https://bestbuy.ca/airpods-pro',
      supported: true,
      brand_hint: 'Apple',
      justification: 'Best Buy Canada PDP',
    },
    {
      title: 'AirPods Pro at Walmart.ca',
      retailer_slug: 'generic',
      retailer_label: 'Walmart Canada',
      url: 'https://walmart.ca/airpods-pro',
      supported: false,
      brand_hint: 'Apple',
      justification: 'Walmart PDP — best-effort scrape',
    },
  ],
}

describe('SearchCommandDialog', () => {
  beforeEach(() => {
    vi.mocked(toast).mockClear()
    vi.mocked(toast.error).mockClear()
    mockMutate.mockClear()
    mockNavigate.mockClear()
    vi.mocked(useCreateProduct).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as ReturnType<typeof useCreateProduct>)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockFetchOk(response: SearchResponse) {
    vi.spyOn(apiModule, 'apiFetch').mockResolvedValue(response)
  }

  it('shows the idle state with example queries on first open', () => {
    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    expect(screen.getByTestId('search-idle')).toBeInTheDocument()
    expect(screen.getAllByTestId('example-query').length).toBeGreaterThan(0)
  })

  it('shows a loading state while the search request is in flight', async () => {
    let resolveSearch: ((value: SearchResponse) => void) | undefined
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(
      () =>
        new Promise<SearchResponse>((resolve) => {
          resolveSearch = resolve
        }),
    )
    const user = userEvent.setup()

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByPlaceholderText(/search any product/i), 'airpods')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(screen.getByTestId('search-loading')).toBeInTheDocument()
    })
    expect(screen.getByText(/searching for/i)).toBeInTheDocument()

    resolveSearch?.(baseResponse)

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })
  })

  it('runs a search when the user submits a query and renders results', async () => {
    mockFetchOk(baseResponse)
    const user = userEvent.setup()

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByPlaceholderText(/search any product/i), 'airpods pro')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })

    const rows = screen.getAllByTestId('search-result-row')
    expect(rows).toHaveLength(3)
    expect(screen.getAllByTestId('retailer-badge')[2]).toHaveTextContent(/walmart canada/i)
    expect(screen.getByTestId('search-meta')).toHaveTextContent(/320ms/)
  })

  it('Track sends the chosen URL plus the other supported retailers as discovery_seed', async () => {
    mockFetchOk(baseResponse)
    const onOpenChange = vi.fn()
    const user = userEvent.setup()

    mockMutate.mockImplementation((_payload, options) => {
      options?.onSuccess?.()
    })

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={onOpenChange} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByPlaceholderText(/search any product/i), 'airpods pro')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(screen.getAllByTestId('track-button').length).toBe(3)
    })

    const trackButtons = screen.getAllByTestId('track-button')
    if (!trackButtons[1]) throw new Error('expected second track button')
    await user.click(trackButtons[1])

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        url: 'https://bestbuy.ca/airpods-pro',
        category: 'auto',
        discovery_seed: [
          { retailer_slug: 'apple_ca', url: 'https://apple.com/ca/airpods-pro' },
        ],
      }),
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    )
  })

  it('Track on an unsupported (link-only) result omits discovery_seed if no other supported results exist', async () => {
    const unsupportedOnly = baseResponse.results[2]
    if (!unsupportedOnly) throw new Error('expected third result fixture')
    mockFetchOk({
      ...baseResponse,
      results: [unsupportedOnly],
    })
    const user = userEvent.setup()

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByPlaceholderText(/search any product/i), 'walmart only')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('track-button'))

    const call = mockMutate.mock.calls[0]
    if (!call) throw new Error('expected mutate to be called')
    expect(call[0].discovery_seed).toBeUndefined()
  })

  it('shows the empty state with Add by URL fallback when no results', async () => {
    mockFetchOk({
      query: 'obscure',
      cache_hit: false,
      latency_ms: 120,
      results: [],
    })
    const onRequestUrlAdd = vi.fn()
    const user = userEvent.setup()

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={onRequestUrlAdd} />,
      { authenticated: true },
    )

    await user.type(screen.getByPlaceholderText(/search any product/i), 'obscure thing')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(screen.getByTestId('search-empty')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /add by url/i }))
    // Dialog closes, then ~180ms later we open the URL add dialog.
    await waitFor(
      () => {
        expect(onRequestUrlAdd).toHaveBeenCalled()
      },
      { timeout: 500 },
    )
  })

  it('shows an error state when the search API fails', async () => {
    vi.spyOn(apiModule, 'apiFetch').mockRejectedValue(
      new apiModule.ApiError(503, 'Search is temporarily unavailable'),
    )
    const user = userEvent.setup()

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByPlaceholderText(/search any product/i), 'anything')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    // useSearch retries transient 503s twice with backoff before surfacing the error.
    await waitFor(
      () => {
        expect(screen.getByTestId('search-error')).toHaveTextContent(/temporarily unavailable/i)
      },
      { timeout: 8000 },
    )
  })

  it('Track failure clears the pending state so the user can retry', async () => {
    mockFetchOk(baseResponse)
    const user = userEvent.setup()

    // Simulate mutation failure: call onSettled (no onSuccess) so pendingItem clears
    // and the row returns to interactive state. (Toast surfaces via useCreateProduct's
    // own onError handler in production code.)
    mockMutate.mockImplementation((_payload, options) => {
      options?.onSettled?.()
    })

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByPlaceholderText(/search any product/i), 'airpods pro')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(screen.getAllByTestId('track-button').length).toBe(3)
    })

    const trackButton = screen.getAllByTestId('track-button')[0]
    if (!trackButton) throw new Error('expected first track button')
    await user.click(trackButton)

    // Row is interactive again — not stuck on "Adding…" or success "Tracking".
    await waitFor(() => {
      const refreshed = screen.getAllByTestId('track-button')[0]
      expect(refreshed).not.toBeDisabled()
      expect(refreshed?.textContent).toMatch(/^track$/i)
    })
  })

  it('clicking an example query fills the input and runs the search', async () => {
    mockFetchOk(baseResponse)
    const user = userEvent.setup()

    renderWithProviders(
      <SearchCommandDialog open onOpenChange={vi.fn()} onRequestUrlAdd={vi.fn()} />,
      { authenticated: true },
    )

    await user.click(screen.getAllByTestId('example-query')[0])

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })
  })
})
