import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  SearchTrigger,
  SearchTriggerMobile,
} from '@/components/search/SearchTrigger'
import { renderWithProviders } from './test-utils'

describe('SearchTrigger', () => {
  it('calls onActivate when clicked', async () => {
    const onActivate = vi.fn()
    const user = userEvent.setup()

    renderWithProviders(<SearchTrigger onActivate={onActivate} />, {
      authenticated: true,
    })

    await user.click(screen.getByRole('button', { name: /open search/i }))
    expect(onActivate).toHaveBeenCalledTimes(1)
  })

  it('renders the keyboard shortcut hint', () => {
    renderWithProviders(<SearchTrigger onActivate={vi.fn()} />, {
      authenticated: true,
    })

    expect(screen.getByText(/⌘K|Ctrl K/)).toBeInTheDocument()
  })
})

describe('SearchTriggerMobile', () => {
  it('renders an icon-only button', async () => {
    const onActivate = vi.fn()
    const user = userEvent.setup()

    renderWithProviders(<SearchTriggerMobile onActivate={onActivate} />, {
      authenticated: true,
    })

    await user.click(screen.getByRole('button', { name: /open search/i }))
    expect(onActivate).toHaveBeenCalledTimes(1)
  })
})
