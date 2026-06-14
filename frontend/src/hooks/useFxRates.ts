import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { getFxRates } from '@/lib/fx'

export const FX_RATES_QUERY_KEY = ['fx', 'rates'] as const

export function useFxRates() {
  const { isAuthenticated } = useAuth()
  return useQuery({
    queryKey: FX_RATES_QUERY_KEY,
    queryFn: getFxRates,
    enabled: isAuthenticated,
    staleTime: 24 * 60 * 60 * 1000,
    gcTime: 25 * 60 * 60 * 1000,
    retry: 1,
  })
}
