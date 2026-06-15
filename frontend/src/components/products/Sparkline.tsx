import { useId, useMemo, useState } from 'react'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import type { PriceHistoryPoint, TrendChip } from '@/lib/products'
import { cn } from '@/lib/utils'

interface SparklineProps {
  history: PriceHistoryPoint[]
  currentPriceCents: number | null
  direction: TrendChip['direction']
  daysOfData: number
  width?: number
  height?: number
  windowDays?: number
  className?: string
  ariaLabel?: string
  /** Greyed-out styling for archived products with paused tracking. */
  paused?: boolean
}

interface SparklinePoint {
  date: Date
  priceCents: number
  isObserved: boolean
  x: number
  y: number
}

const STROKE_CLASS: Record<TrendChip['direction'], string> = {
  down: 'text-trend-down',
  same: 'text-trend-same',
  up: 'text-trend-up',
}

const DEFAULT_WIDTH = 140
const DEFAULT_HEIGHT = 36
const DEFAULT_WINDOW_DAYS = 30
const PADDING = 3
const MIN_HISTORY_DAYS_FOR_DELTA = 7

function startOfUtcDay(date: Date): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()))
}

function formatYMD(date: Date): string {
  const year = date.getUTCFullYear()
  const month = String(date.getUTCMonth() + 1).padStart(2, '0')
  const day = String(date.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseObservedOn(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, (month ?? 1) - 1, day ?? 1))
}

interface BuildOptions {
  history: PriceHistoryPoint[]
  currentPriceCents: number | null
  windowDays: number
  width: number
  height: number
}

/**
 * Build a fixed-length array of one point per day in the trailing window.
 *
 * - Leading days with no observed price fall back to `currentPriceCents`
 *   so newly-tracked products render a flat "Same in the last 30 days" line.
 * - Trailing/middle gaps carry forward the last known price so a single
 *   missed scrape doesn't flatten an otherwise informative line.
 */
export function buildSparklinePoints(opts: BuildOptions): SparklinePoint[] | null {
  const { history, currentPriceCents, windowDays, width, height } = opts
  const anchorPrice = currentPriceCents
  // Use most recent observation as right edge when present; otherwise today.
  const sortedDates = history
    .map((h) => parseObservedOn(h.observed_on))
    .sort((a, b) => a.getTime() - b.getTime())
  const today = startOfUtcDay(new Date())
  const lastObserved = sortedDates.at(-1)
  const endDate = lastObserved && lastObserved > today ? lastObserved : today

  const byDate = new Map(history.map((p) => [p.observed_on, p.price_cents]))

  const dates: Date[] = []
  for (let i = windowDays - 1; i >= 0; i -= 1) {
    const d = new Date(endDate)
    d.setUTCDate(d.getUTCDate() - i)
    dates.push(d)
  }

  const prices: { date: Date; priceCents: number; isObserved: boolean }[] = []
  let lastKnown: number | null = null
  for (const date of dates) {
    const observed = byDate.get(formatYMD(date))
    if (observed != null) {
      lastKnown = observed
      prices.push({ date, priceCents: observed, isObserved: true })
    } else if (lastKnown != null) {
      prices.push({ date, priceCents: lastKnown, isObserved: false })
    } else if (anchorPrice != null) {
      prices.push({ date, priceCents: anchorPrice, isObserved: false })
    } else {
      // No data and no anchor price — cannot render.
    }
  }

  if (prices.length < 2) {
    return null
  }

  const values = prices.map((p) => p.priceCents)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const innerHeight = Math.max(0, height - PADDING * 2)
  const innerWidth = Math.max(0, width - PADDING * 2)
  const xStep = innerWidth / (prices.length - 1)

  return prices.map((point, idx) => {
    const x = PADDING + xStep * idx
    let y: number
    if (max === min) {
      y = PADDING + innerHeight / 2
    } else {
      const ratio = (point.priceCents - min) / (max - min)
      y = PADDING + innerHeight - ratio * innerHeight
    }
    return { ...point, x, y }
  })
}

function formatDateShort(date: Date): string {
  // Dates are constructed in UTC from the backend's YYYY-MM-DD payload;
  // format in UTC so the tooltip day matches the price_history row.
  return date.toLocaleDateString('en-CA', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

export function Sparkline({
  history,
  currentPriceCents,
  direction,
  daysOfData,
  width = DEFAULT_WIDTH,
  height = DEFAULT_HEIGHT,
  windowDays = DEFAULT_WINDOW_DAYS,
  className,
  ariaLabel,
  paused = false,
}: SparklineProps) {
  const formatPriceCents = useFormatPriceCents()
  const titleId = useId()
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)

  const points = useMemo(
    () =>
      buildSparklinePoints({
        history,
        currentPriceCents,
        windowDays,
        width,
        height,
      }),
    [history, currentPriceCents, windowDays, width, height],
  )

  if (!points) return null

  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`)
    .join(' ')

  const first = points[0]
  const last = points[points.length - 1]
  const startPriceLabel = formatPriceCents(first.priceCents)
  const endPriceLabel = formatPriceCents(last.priceCents)

  let deltaLabel: string | null = null
  if (
    daysOfData >= MIN_HISTORY_DAYS_FOR_DELTA &&
    first.priceCents > 0 &&
    last.priceCents !== first.priceCents
  ) {
    const deltaPct = ((last.priceCents - first.priceCents) / first.priceCents) * 100
    const sign = deltaPct > 0 ? '+' : '−'
    deltaLabel = `${sign}${Math.abs(deltaPct).toFixed(deltaPct > -1 && deltaPct < 1 ? 1 : 0)}%`
  }

  const accessibleSummary =
    ariaLabel ??
    `30-day price trend: ${startPriceLabel} 30 days ago, ${endPriceLabel} today`

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (event.pointerType === 'touch' || event.pointerType === 'pen') return
    const svg = event.currentTarget
    const rect = svg.getBoundingClientRect()
    const relativeX = ((event.clientX - rect.left) / rect.width) * width
    let nearest = 0
    let nearestDist = Infinity
    points.forEach((p, idx) => {
      const dist = Math.abs(p.x - relativeX)
      if (dist < nearestDist) {
        nearest = idx
        nearestDist = dist
      }
    })
    setHoverIndex(nearest)
  }

  const handlePointerLeave = () => setHoverIndex(null)

  const tooltipPoint = hoverIndex != null ? points[hoverIndex] : null
  const tooltipDate = tooltipPoint ? formatDateShort(tooltipPoint.date) : ''
  const tooltipPrice = tooltipPoint ? formatPriceCents(tooltipPoint.priceCents) : ''

  const strokeClass = paused ? 'text-muted-foreground' : STROKE_CLASS[direction]

  return (
    <div
      className={cn(
        'relative inline-flex items-center gap-2 text-xs text-muted-foreground tabular-nums',
        paused && 'opacity-60',
        className,
      )}
    >
      <span aria-hidden="true" className="hidden sm:inline">
        {startPriceLabel}
      </span>
      <div className="relative">
        <svg
          role="img"
          aria-labelledby={titleId}
          viewBox={`0 0 ${width} ${height}`}
          width={width}
          height={height}
          className={cn('block overflow-visible', strokeClass)}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
        >
          <title id={titleId}>{accessibleSummary}</title>
          <path
            d={path}
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
          <circle
            cx={last.x}
            cy={last.y}
            r={2}
            fill="currentColor"
            stroke="hsl(var(--background))"
            strokeWidth={1}
          />
          {tooltipPoint ? (
            <g pointerEvents="none">
              <line
                x1={tooltipPoint.x}
                y1={PADDING}
                x2={tooltipPoint.x}
                y2={height - PADDING}
                stroke="currentColor"
                strokeOpacity={0.25}
                strokeDasharray="2 2"
              />
              <circle
                cx={tooltipPoint.x}
                cy={tooltipPoint.y}
                r={3}
                fill="currentColor"
                stroke="hsl(var(--background))"
                strokeWidth={1.5}
              />
            </g>
          ) : null}
        </svg>
        {tooltipPoint ? (
          <div
            role="tooltip"
            className="pointer-events-none absolute -top-10 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-popover px-2 py-1 text-[11px] font-medium text-popover-foreground shadow-sm sm:block"
            style={{
              left: `${(tooltipPoint.x / width) * 100}%`,
            }}
          >
            <span className="block text-muted-foreground">{tooltipDate}</span>
            <span className="block text-foreground">{tooltipPrice}</span>
          </div>
        ) : null}
      </div>
      <span aria-hidden="true" className="hidden sm:inline">
        {endPriceLabel}
      </span>
      {deltaLabel && !paused ? (
        <span
          aria-hidden="true"
          className={cn('text-[11px] font-medium', strokeClass)}
        >
          {deltaLabel}
        </span>
      ) : null}
    </div>
  )
}
