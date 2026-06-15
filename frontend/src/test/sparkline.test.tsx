import { render, screen, fireEvent } from '@testing-library/react'
import { buildSparklinePoints, Sparkline } from '@/components/products/Sparkline'
import { ProviderStack } from './test-utils'
import type { PriceHistoryPoint } from '@/lib/products'

function isoOffset(daysAgo: number): string {
  const d = new Date()
  d.setUTCHours(0, 0, 0, 0)
  d.setUTCDate(d.getUTCDate() - daysAgo)
  return d.toISOString().slice(0, 10)
}

describe('buildSparklinePoints', () => {
  const baseOpts = {
    windowDays: 30,
    width: 140,
    height: 36,
  }

  it('returns null when there is no anchor price and no history', () => {
    expect(
      buildSparklinePoints({
        ...baseOpts,
        history: [],
        currentPriceCents: null,
      }),
    ).toBeNull()
  })

  it('pads left with the current best price when only one day of data exists', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(0), price_cents: 27999 },
    ]
    const points = buildSparklinePoints({
      ...baseOpts,
      history,
      currentPriceCents: 27999,
    })
    expect(points).not.toBeNull()
    if (!points) return
    expect(points).toHaveLength(30)
    expect(points.every((p) => p.priceCents === 27999)).toBe(true)
    expect(points.at(-1)?.isObserved).toBe(true)
    expect(points[0].isObserved).toBe(false)
  })

  it('carries forward through middle gaps after first real observation', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(20), price_cents: 25000 },
      { observed_on: isoOffset(10), price_cents: 24000 },
      { observed_on: isoOffset(0), price_cents: 23000 },
    ]
    const points = buildSparklinePoints({
      ...baseOpts,
      history,
      currentPriceCents: 23000,
    })
    expect(points).not.toBeNull()
    if (!points) return
    expect(points.length).toBe(30)
    expect(points.at(-1)?.priceCents).toBe(23000)
    expect(points[0].priceCents).toBe(23000)
    const middleIdx = points.findIndex((p) => p.priceCents === 25000)
    expect(middleIdx).toBeGreaterThan(0)
    expect(points[middleIdx + 1].priceCents).toBe(25000)
    expect(points[middleIdx + 1].isObserved).toBe(false)
  })

  it('places min price at bottom and max price at top of inner area', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(20), price_cents: 30000 },
      { observed_on: isoOffset(0), price_cents: 20000 },
    ]
    const points = buildSparklinePoints({
      ...baseOpts,
      history,
      currentPriceCents: 20000,
    })
    if (!points) throw new Error('expected points')
    const high = points.find((p) => p.priceCents === 30000)
    const low = points.find((p) => p.priceCents === 20000)
    if (!high || !low) throw new Error('expected both prices in points')
    expect(high.y).toBeLessThan(low.y)
  })
})

describe('Sparkline component', () => {
  it('renders an SVG path with role img and accessible label', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(20), price_cents: 25000 },
      { observed_on: isoOffset(0), price_cents: 23000 },
    ]
    render(
      <ProviderStack>
        <Sparkline
          history={history}
          currentPriceCents={23000}
          direction="down"
          daysOfData={20}
        />
      </ProviderStack>,
    )

    const svg = screen.getByRole('img')
    expect(svg.querySelector('path')?.getAttribute('d')).toBeTruthy()
    expect(svg.querySelector('title')?.textContent).toMatch(/30-day price trend/)
  })

  it('shows a tooltip with date and price on pointer move (mouse only)', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(20), price_cents: 25000 },
      { observed_on: isoOffset(10), price_cents: 24000 },
      { observed_on: isoOffset(0), price_cents: 23000 },
    ]
    render(
      <ProviderStack>
        <Sparkline
          history={history}
          currentPriceCents={23000}
          direction="down"
          daysOfData={20}
        />
      </ProviderStack>,
    )

    const svg = screen.getByRole('img') as unknown as SVGSVGElement
    svg.getBoundingClientRect = () =>
      ({
        left: 0,
        top: 0,
        right: 140,
        bottom: 36,
        width: 140,
        height: 36,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      }) as DOMRect

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    fireEvent.pointerMove(svg, { pointerType: 'mouse', clientX: 70, clientY: 18 })
    const tooltip = screen.getByRole('tooltip')
    expect(tooltip).toBeInTheDocument()
    expect(tooltip.textContent).toMatch(/\$/)

    fireEvent.pointerLeave(svg)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('does not render anything if history is empty and no current price', () => {
    const { container } = render(
      <ProviderStack>
        <Sparkline
          history={[]}
          currentPriceCents={null}
          direction="same"
          daysOfData={0}
        />
      </ProviderStack>,
    )
    expect(container.querySelector('svg')).toBeNull()
  })

  it('renders a flat line at current best price when only anchor is available', () => {
    render(
      <ProviderStack>
        <Sparkline
          history={[]}
          currentPriceCents={27999}
          direction="same"
          daysOfData={0}
        />
      </ProviderStack>,
    )

    expect(screen.getByRole('img')).toBeInTheDocument()
    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
  })

  it('shows a signed delta percentage when daysOfData >= 7 and endpoints differ', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(29), price_cents: 30000 },
      { observed_on: isoOffset(0), price_cents: 27000 },
    ]
    render(
      <ProviderStack>
        <Sparkline
          history={history}
          currentPriceCents={27000}
          direction="down"
          daysOfData={28}
        />
      </ProviderStack>,
    )

    expect(screen.getByText(/−10%/)).toBeInTheDocument()
  })

  it('hides the delta label when daysOfData is below the 7-day threshold', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(3), price_cents: 30000 },
      { observed_on: isoOffset(0), price_cents: 27000 },
    ]
    render(
      <ProviderStack>
        <Sparkline
          history={history}
          currentPriceCents={27000}
          direction="same"
          daysOfData={4}
        />
      </ProviderStack>,
    )

    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
  })

  it('does not open the tooltip for touch or pen pointer types', () => {
    const history: PriceHistoryPoint[] = [
      { observed_on: isoOffset(20), price_cents: 25000 },
      { observed_on: isoOffset(0), price_cents: 23000 },
    ]
    render(
      <ProviderStack>
        <Sparkline
          history={history}
          currentPriceCents={23000}
          direction="down"
          daysOfData={20}
        />
      </ProviderStack>,
    )

    const svg = screen.getByRole('img') as unknown as SVGSVGElement
    svg.getBoundingClientRect = () =>
      ({
        left: 0,
        top: 0,
        right: 140,
        bottom: 36,
        width: 140,
        height: 36,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      }) as DOMRect

    const dispatchPointer = (pointerType: 'touch' | 'pen') => {
      const event = new Event('pointermove', { bubbles: true })
      Object.assign(event, { pointerType, clientX: 70, clientY: 18 })
      svg.dispatchEvent(event)
    }
    dispatchPointer('touch')
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    dispatchPointer('pen')
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })
})
