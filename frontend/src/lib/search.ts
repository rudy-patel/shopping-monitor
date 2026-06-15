import { apiFetch } from '@/lib/api'

export interface SearchResultItem {
  title: string
  retailer_slug: string
  retailer_label: string
  url: string
  supported: boolean
  brand_hint: string | null
  justification: string
}

export interface SearchResponse {
  query: string
  results: SearchResultItem[]
  cache_hit: boolean
  latency_ms: number
}

export function runSearch(query: string): Promise<SearchResponse> {
  return apiFetch<SearchResponse>('/api/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

export function searchQueryKey(query: string) {
  return ['search', query.trim().toLowerCase()] as const
}

export function isSearchableQuery(value: string): boolean {
  return value.trim().length >= 2
}
