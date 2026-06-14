import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '@/contexts/AuthContext'
import { deleteAccount } from '@/lib/account'

export function useDeleteAccount() {
  const { signOut } = useAuth()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: deleteAccount,
    onSuccess: async () => {
      await signOut()
      navigate('/login')
    },
    onError: () => {
      toast.error('Could not delete account')
    },
  })
}
