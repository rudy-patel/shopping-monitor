import { ApiError, apiFetch } from '@/lib/api'

vi.mock('@/lib/supabase', () => ({
  getSupabaseClient: vi.fn(() => null),
  isSupabaseConfigured: vi.fn(() => false),
}))

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns parsed JSON on success', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'ok' }), { status: 200 }),
    )

    await expect(apiFetch('/health')).resolves.toEqual({ message: 'ok' })
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/health', {
      headers: expect.any(Headers),
    })
  })

  it('throws ApiError with status and message on failure', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }),
    )

    await expect(apiFetch('/missing')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'Not found',
    })
  })

  it('returns undefined for 204 responses', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }))

    await expect(apiFetch('/resource')).resolves.toBeUndefined()
  })
})

describe('ApiError', () => {
  it('exposes status and name', () => {
    const error = new ApiError(422, 'Validation failed')
    expect(error.status).toBe(422)
    expect(error.name).toBe('ApiError')
    expect(error.message).toBe('Validation failed')
  })
})
