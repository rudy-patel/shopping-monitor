import '@testing-library/jest-dom'

vi.mock('../lib/supabase.ts', () => ({
  getSupabaseClient: vi.fn(() => null),
  isSupabaseConfigured: vi.fn(() => false),
}))
