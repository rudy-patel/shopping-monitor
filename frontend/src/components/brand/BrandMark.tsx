import { cn } from '@/lib/utils'

interface BrandMarkProps {
  /** `hero` for sign-in splash; `compact` for in-app empty states. */
  size?: 'hero' | 'compact'
  showWings?: boolean
  className?: string
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

export function BrandMark({ size = 'hero', showWings = true, className }: BrandMarkProps) {
  const isHero = size === 'hero'

  return (
    <div className={cn('relative inline-block', className)}>
      {showWings ? <WingFlourish side="left" size={size} /> : null}
      <div
        className={cn(
          'rounded-full border-2 border-dashed border-foreground/35 bg-background/95 shadow-sm backdrop-blur-sm',
          isHero ? 'px-8 py-4 sm:px-12 sm:py-5' : 'px-4 py-2',
        )}
      >
        {isHero ? (
          <h1 className="font-semibold tracking-tight text-foreground text-4xl sm:text-5xl md:text-6xl">
            Someday.
          </h1>
        ) : (
          <span className="text-lg font-semibold tracking-tight text-foreground">Someday.</span>
        )}
      </div>
      {showWings ? <WingFlourish side="right" size={size} /> : null}
    </div>
  )
}
