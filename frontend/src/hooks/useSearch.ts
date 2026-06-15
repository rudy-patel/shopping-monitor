import { useQuery } from '@tanstack/react-query'
import {
  isSearchableQuery,
  runSearch,
  searchQueryKey,
  type SearchResponse,
} from '@/lib/search'

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
    retry: false,
  })
}
