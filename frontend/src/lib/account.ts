import { apiFetch } from '@/lib/api'

export async function deleteAccount(): Promise<void> {
  await apiFetch('/api/account', { method: 'DELETE' })
}
