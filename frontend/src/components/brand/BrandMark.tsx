import { cn } from '@/lib/utils'

type BrandMarkSize = 'hero' | 'nav' | 'compact'

interface BrandMarkProps {
  /** `hero` for sign-in splash; `nav` for header; `compact` for in-app empty states. */
  size?: BrandMarkSize
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

export function BrandMark({ size = 'hero', className }: BrandMarkProps) {
  const labelClass = cn('font-semibold tracking-tight text-foreground', TEXT_CLASS[size])

  return (
    <div
      className={cn(
        'inline-block rounded-full border-2 border-dashed border-foreground/35 bg-background/95 shadow-sm backdrop-blur-sm',
        PILL_CLASS[size],
        className,
      )}
    >
      {size === 'hero' ? (
        <h1 className={labelClass}>Someday.</h1>
      ) : (
        <span className={labelClass}>Someday.</span>
      )}
    </div>
  )
}
