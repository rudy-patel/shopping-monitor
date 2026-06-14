import { screen } from '@testing-library/react'
import { TrendChip } from '@/components/products/TrendChip'
import { sampleTrend } from './product-fixtures'
import { renderWithProviders } from './test-utils'

describe('TrendChip', () => {
  it('renders accessible label text for down, same, and up', () => {
    const { rerender } = renderWithProviders(
      <TrendChip trend={{ ...sampleTrend, direction: 'down', label: 'Down in the last 30 days' }} />,
    )
    expect(screen.getByLabelText('↓ Down in the last 30 days')).toBeInTheDocument()

    rerender(
      <TrendChip trend={{ ...sampleTrend, direction: 'same', label: 'Stable in the last 30 days' }} />,
    )
    expect(screen.getByLabelText('→ Stable in the last 30 days')).toBeInTheDocument()

    rerender(
      <TrendChip trend={{ ...sampleTrend, direction: 'up', label: 'Up in the last 30 days' }} />,
    )
    expect(screen.getByLabelText('↑ Up in the last 30 days')).toBeInTheDocument()
  })
})
