import { apiFetch } from '@/lib/api'

export interface FxRatesResponse {
  base: 'CAD'
  fetched_at: string
  stale: boolean
  rates: Record<'CAD' | 'USD' | 'EUR' | 'GBP', string>
}

export function getFxRates(): Promise<FxRatesResponse> {
  return apiFetch<FxRatesResponse>('/api/fx/rates')
}
