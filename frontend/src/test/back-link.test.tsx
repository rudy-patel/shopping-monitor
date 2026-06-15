import { screen } from '@testing-library/react'
import { BackLink } from '@/components/layout/BackLink'
import { renderWithProviders } from './test-utils'

describe('BackLink', () => {
  it('renders a navigable link with a decorative back icon', () => {
    renderWithProviders(<BackLink to="/history">Back to archived</BackLink>)

    const link = screen.getByRole('link', { name: /back to archived/i })
    expect(link).toHaveAttribute('href', '/history')
    expect(link.querySelector('svg[aria-hidden="true"]')).toBeInTheDocument()
  })
})
