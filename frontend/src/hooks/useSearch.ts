import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import {
  isSearchableQuery,
  runSearch,
  searchQueryKey,
  type SearchResponse,
} from '@/lib/search'

// react-query's `failureCount` argument starts at 0 for the first retry decision
// (= count of failures BEFORE this one). `failureCount < 1` → exactly one retry,
// for a total of two attempts on transient errors. Two strikes the right balance:
// short user wait on transient 503/504s, but never an open-ended retry loop that
// burns Gemini quota or makes the spinner linger.
const SEARCH_RETRY_LIMIT = 1

export function isQuotaExhaustedError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 429
}

function isRetryableSearchError(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false
  // Transient provider/timeout failures get one retry. Quota (429) is a real
  // daily cap — retrying just burns more quota and makes the user wait, so we
  // never retry it; the dialog surfaces a specific "daily limit" message.
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
      failureCount < SEARCH_RETRY_LIMIT && isRetryableSearchError(error),
    // Keep the gap between attempts short so users don't stare at a spinner.
    retryDelay: (attempt) => Math.min(800 * 2 ** attempt, 3000),
  })
}
