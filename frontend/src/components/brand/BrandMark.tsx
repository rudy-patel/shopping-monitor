import { cn } from '@/lib/utils'

type BrandMarkSize = 'hero' | 'nav' | 'compact'

interface BrandMarkProps {
  /** `hero` for sign-in splash; `nav` for header; `compact` for in-app empty states. */
  size?: BrandMarkSize
  showWings?: boolean
  className?: string
}

const PILL_CLASS: Record<BrandMarkSize, string> = {
  hero: 'px-8 py-4 sm:px-12 sm:py-5',
  nav: 'px-2.5 py-0.5',
  compact: 'px-4 py-2',
}

const TEXT_CLASS: Record<BrandMarkSize, string> = {
  hero: 'text-4xl sm:text-5xl md:text-6xl',
  nav: 'text-sm',
  compact: 'text-lg',
}

function WingFlourish({
  side,
  size,
}: {
  side: 'left' | 'right'
  size: 'hero' | 'compact'
}) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 96 56"
      className={cn(
        'pointer-events-none absolute top-1/2 hidden -translate-y-1/2 text-foreground/40 sm:block',
        size === 'hero' ? 'h-10 w-20' : 'h-6 w-12',
        side === 'left' ? '-scale-x-100' : undefined,
        side === 'left'
          ? size === 'hero'
            ? '-left-24'
            : '-left-14'
          : size === 'hero'
            ? '-right-24'
            : '-right-14',
      )}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    >
      <path d="M4 30 Q 22 12, 40 22 T 78 16" />
      <path d="M2 40 Q 22 48, 42 38" />
      <path d="M14 28 Q 28 22, 44 26" />
      <circle cx="82" cy="14" r="1.5" fill="currentColor" />
    </svg>
  )
}

export function BrandMark({ size = 'hero', showWings, className }: BrandMarkProps) {
  const wingsVisible = showWings ?? size === 'hero'
  const wingSize = size === 'nav' ? 'compact' : size
  const labelClass = cn('font-semibold tracking-tight text-foreground', TEXT_CLASS[size])

  return (
    <div className={cn('relative inline-block', className)}>
      {wingsVisible ? <WingFlourish side="left" size={wingSize} /> : null}
      <div
        className={cn(
          'rounded-full border-2 border-dashed border-foreground/35 bg-background/95 shadow-sm backdrop-blur-sm',
          PILL_CLASS[size],
        )}
      >
        {size === 'hero' ? (
          <h1 className={labelClass}>Someday.</h1>
        ) : (
          <span className={labelClass}>Someday.</span>
        )}
      </div>
      {wingsVisible ? <WingFlourish side="right" size={wingSize} /> : null}
    </div>
  )
}
