import { render, screen } from '@testing-library/react'
import { RetailerIdentity, RetailerLogo } from '@/components/retailers/RetailerLogo'
import { knownRetailerSlugs } from '@/lib/format'
import { RETAILER_LOGOS } from '@/lib/retailer-logos'

describe('retailer logos', () => {
  it('covers every known retailer slug from format labels', () => {
    for (const slug of knownRetailerSlugs()) {
      expect(RETAILER_LOGOS[slug]).toBeTruthy()
    }
  })

  it('renders a logo for supported retailers and nothing for generic', () => {
    const { container, rerender } = render(<RetailerLogo slug="bestbuy_ca" />)
    expect(container.querySelector('img')).toBeInTheDocument()

    rerender(<RetailerLogo slug="generic" />)
    expect(container.querySelector('img')).not.toBeInTheDocument()
  })

  it('renders logo plus label together', () => {
    render(<RetailerIdentity slug="amazon_ca" />)
    expect(screen.getByText('Amazon.ca')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeInTheDocument()
  })

  it('links the retailer label when href is provided', () => {
    render(<RetailerIdentity slug="bestbuy_ca" href="https://www.bestbuy.ca/example" />)
    const link = screen.getByRole('link', { name: /best buy canada/i })
    expect(link).toHaveAttribute('href', 'https://www.bestbuy.ca/example')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
