import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { getProfile, updateProfile, type Profile } from '@/lib/profile'

export const PROFILE_QUERY_KEY = ['profile'] as const

export function useProfile() {
  const { isAuthenticated } = useAuth()
  return useQuery({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: getProfile,
    enabled: isAuthenticated,
    staleTime: 60_000,
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateProfile,
    onSuccess: (next) => {
      queryClient.setQueryData<Profile>(PROFILE_QUERY_KEY, next)
    },
  })
}
