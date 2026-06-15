import { render } from '@testing-library/react'
import { vi } from 'vitest'
import { LoginSplashStickers } from '@/components/login/LoginSplashStickers'
import { loginSplashStickers } from '@/lib/login-stickers'

vi.mock('@/lib/motion', () => ({
  useMotionEnabled: vi.fn(() => false),
}))

describe('LoginSplashStickers', () => {
  it('renders one aria-hidden sticker per config entry', () => {
    const { container } = render(<LoginSplashStickers />)

    const stickers = container.querySelectorAll('[data-testid="login-splash-sticker"]')
    expect(stickers).toHaveLength(loginSplashStickers.length)
  })
})
