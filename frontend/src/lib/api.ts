import { getApiUrl } from '@/lib/env'
import { getSupabaseClient } from '@/lib/supabase'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers)

  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json')
  }

  const supabase = getSupabaseClient()
  if (supabase) {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  const response = await fetch(`${getApiUrl()}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    let message = response.statusText
    try {
      const body = (await response.json()) as { detail?: string; message?: string }
      message = body.detail ?? body.message ?? message
    } catch {
      // keep statusText
    }
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
