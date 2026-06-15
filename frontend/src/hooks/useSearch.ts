import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import {
  isSearchableQuery,
  runSearch,
  searchQueryKey,
  type SearchResponse,
} from '@/lib/search'

const SEARCH_MAX_RETRIES = 2

function isRetryableSearchError(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false
  // Transient provider/rate-limit failures — keep loading and retry before surfacing.
  return error.status === 503 || error.status === 502 || error.status === 504
}

/**
 * Search hook. Disabled until the user submits a query so we never spend Gemini
 * quota on type-ahead. Results are cached for the session by react-query plus a
 * 24h server-side cache (T8.3).
 */
export function useSearch(submittedQuery: string) {
  return useQuery<SearchResponse>({
    queryKey: searchQueryKey(submittedQuery),
    queryFn: () => runSearch(submittedQuery),
    enabled: isSearchableQuery(submittedQuery),
    // Search results don't change rapidly — match the backend TTL.
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 2,
    retry: (failureCount, error) =>
      failureCount < SEARCH_MAX_RETRIES && isRetryableSearchError(error),
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
  })
}
