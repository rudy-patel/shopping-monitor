import { screen } from '@testing-library/react'
import { TrendChip, trendPriceClass } from '@/components/products/TrendChip'
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

  it('maps trendPriceClass to matching text color utilities', () => {
    expect(trendPriceClass('down')).toBe('text-trend-down')
    expect(trendPriceClass('same')).toBe('text-trend-same')
    expect(trendPriceClass('up')).toBe('text-trend-up')
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

  it('appends a percent suffix when delta_pct is known', () => {
    renderWithProviders(
      <TrendChip
        trend={{
          ...sampleTrend,
          direction: 'down',
          delta_pct: -0.08,
          label: 'Down in the last 30 days',
        }}
      />,
    )
    expect(screen.getByLabelText('↓ Down 8%')).toBeInTheDocument()
  })

  it('renders shorter visible copy in compact mode while keeping full aria-label', () => {
    renderWithProviders(
      <TrendChip
        compact
        trend={{
          ...sampleTrend,
          direction: 'same',
          delta_pct: null,
          label: 'Same in the last 30 days',
        }}
      />,
    )
    expect(screen.getByLabelText('→ Same in the last 30 days')).toBeInTheDocument()
    expect(screen.getByText('→ Same')).toBeInTheDocument()
  })
})
