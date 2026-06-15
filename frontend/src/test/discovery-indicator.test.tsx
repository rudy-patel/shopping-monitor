import { render, screen } from '@testing-library/react'
import { DiscoveryIndicator } from '@/components/products/DiscoveryIndicator'

describe('DiscoveryIndicator', () => {
  it('renders nothing when discovery is complete', () => {
    const { container } = render(<DiscoveryIndicator status="complete" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows in-flight copy while discovery runs', () => {
    render(<DiscoveryIndicator status="pending" />)
    expect(screen.getByText('Looking for other retailers…')).toBeInTheDocument()
  })

  it('shows failure copy when discovery fails', () => {
    render(<DiscoveryIndicator status="failed" />)
    expect(screen.getByText('Discovery unavailable')).toBeInTheDocument()
  })
})
