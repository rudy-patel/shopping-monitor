import { screen } from '@testing-library/react'
import { ListingCard } from '@/components/products/ListingCard'
import { makeProductDetail } from './product-fixtures'
import { renderWithProviders } from './test-utils'

const listing = makeProductDetail().listings[0]

describe('ListingCard', () => {
  it('renders price, retailer, stock, and relative time without scrape status', () => {
    renderWithProviders(
      <ListingCard listing={{ ...listing, scrape_status: 'ok' }} />,
    )

    expect(screen.getByText('$129.99')).toBeInTheDocument()
    expect(screen.getByText('Best Buy Canada')).toBeInTheDocument()
    expect(document.querySelector('img[src*="bestbuy"]')).toBeInTheDocument()
    expect(screen.getByText('In stock')).toBeInTheDocument()
    expect(screen.queryByText('ok')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open on best buy canada/i })).toBeInTheDocument()
  })

  it('does not show comparison hints by default', () => {
    renderWithProviders(<ListingCard listing={listing} />)

    expect(screen.queryByText('Best price')).not.toBeInTheDocument()
    expect(screen.queryByText(/vs best/i)).not.toBeInTheDocument()
  })

  it('highlights the cheapest listing when comparison hints are enabled', () => {
    renderWithProviders(
      <ListingCard listing={listing} isBestPrice priceDeltaVsBestCents={null} />,
    )

    expect(screen.getByText('Best price')).toBeInTheDocument()
    expect(screen.queryByText(/vs best/i)).not.toBeInTheDocument()
  })

  it('shows a delta label for more expensive listings', () => {
    renderWithProviders(
      <ListingCard
        listing={{ ...listing, last_known_price_cents: 14999 }}
        priceDeltaVsBestCents={2000}
      />,
    )

    expect(screen.getByText('+$20.00 vs best')).toBeInTheDocument()
    expect(screen.queryByText('Best price')).not.toBeInTheDocument()
  })
})
