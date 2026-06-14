import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { AddProductDialog } from '@/components/add-product/AddProductDialog'
import { renderWithProviders } from './test-utils'

vi.mock('sonner', () => ({
  toast: vi.fn(),
  Toaster: () => null,
}))

describe('AddProductDialog', () => {
  beforeEach(() => {
    vi.mocked(toast).mockClear()
  })

  it('shows URL input when open and toasts on submit', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()

    renderWithProviders(
      <AddProductDialog open onOpenChange={onOpenChange} />,
      { authenticated: true },
    )

    expect(screen.getByLabelText(/product url/i)).toBeInTheDocument()

    await user.type(screen.getByLabelText(/product url/i), 'https://example.com/product')
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    expect(toast).toHaveBeenCalledWith('Coming in T2.6')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
