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

  it('uses subtle trend color styles per direction', () => {
    const { rerender, container } = renderWithProviders(
      <TrendChip trend={{ ...sampleTrend, direction: 'down', label: 'Down in the last 30 days' }} />,
    )
    expect(container.querySelector('[aria-label="↓ Down in the last 30 days"]')).toHaveClass(
      'bg-trend-down-muted',
      'text-trend-down',
    )

    rerender(
      <TrendChip trend={{ ...sampleTrend, direction: 'same', label: 'Stable in the last 30 days' }} />,
    )
    expect(container.querySelector('[aria-label="→ Stable in the last 30 days"]')).toHaveClass(
      'bg-trend-same-muted',
      'text-trend-same',
    )

    rerender(
      <TrendChip trend={{ ...sampleTrend, direction: 'up', label: 'Up in the last 30 days' }} />,
    )
    expect(container.querySelector('[aria-label="↑ Up in the last 30 days"]')).toHaveClass(
      'bg-trend-up-muted',
      'text-trend-up',
    )
  })
})
