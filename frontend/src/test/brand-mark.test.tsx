import { render, screen } from '@testing-library/react'
import { BrandMark } from '@/components/brand/BrandMark'

describe('BrandMark', () => {
  it('renders hero size as the page heading', () => {
    render(<BrandMark size="hero" />)

    const heading = screen.getByRole('heading', { level: 1, name: /someday\./i })
    expect(heading).toBeInTheDocument()
  })

  it('renders compact size without a heading role', () => {
    render(<BrandMark size="compact" showWings={false} />)

    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
    expect(screen.getByText('Someday.')).toBeInTheDocument()
  })
})
