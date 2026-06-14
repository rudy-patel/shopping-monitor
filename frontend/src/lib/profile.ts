import { apiFetch } from '@/lib/api'

export interface Profile {
  user_id: string
  display_currency: 'CAD' | 'USD' | 'EUR' | 'GBP'
  default_threshold_pct: number
  notifications_enabled: boolean
  email_digest_enabled: boolean
  theme: 'light' | 'dark'
  revisit_prompts_enabled: boolean
  revisit_on_sale_enabled: boolean
  revisit_stale_enabled: boolean
  revisit_stale_days: number
  created_at: string
  updated_at: string
}

export type ProfileUpdate = Partial<
  Omit<Profile, 'user_id' | 'created_at' | 'updated_at'>
>

export function getProfile(): Promise<Profile> {
  return apiFetch<Profile>('/api/profile')
}

export function updateProfile(patch: ProfileUpdate): Promise<Profile> {
  return apiFetch<Profile>('/api/profile', {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
}
