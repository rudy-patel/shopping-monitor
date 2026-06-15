import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { FloatingSticker } from '@/components/login/FloatingSticker'

vi.mock('@/lib/motion', () => ({
  useMotionEnabled: vi.fn(() => false),
}))

import { useMotionEnabled } from '@/lib/motion'

describe('FloatingSticker', () => {
  beforeEach(() => {
    vi.mocked(useMotionEnabled).mockReturnValue(false)
  })

  it('renders children, applies position + rotation, and is decorative for SR', () => {
    render(
      <FloatingSticker position="top-[10%] left-[20%]" variant="brick" rotate={-12}>
        −20% OFF
      </FloatingSticker>,
    )

    const sticker = screen.getByText('−20% OFF').closest('[aria-hidden="true"]') as HTMLElement | null
    expect(sticker).not.toBeNull()
    expect(sticker?.className).toContain('top-[10%]')
    expect(sticker?.className).toContain('left-[20%]')
    expect(sticker?.className).toContain('hidden')
    expect(sticker?.className).toContain('md:inline-flex')
    expect(sticker?.getAttribute('aria-hidden')).toBe('true')
    // With motion disabled, rotation is applied via inline transform.
    expect(sticker?.style.transform).toContain('rotate(-12deg)')
  })

  it('renders an aria-hidden wrapper when motion is enabled', () => {
    vi.mocked(useMotionEnabled).mockReturnValue(true)
    render(
      <FloatingSticker position="top-0 left-0" rotate={5}>
        Decorative copy
      </FloatingSticker>,
    )

    const sticker = screen.getByText('Decorative copy').closest('[aria-hidden="true"]')
    expect(sticker).not.toBeNull()
  })
})
