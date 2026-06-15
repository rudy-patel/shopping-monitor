import { retailerLabel } from '@/lib/format'
import { retailerLogoSrc } from '@/lib/retailer-logos'
import { cn } from '@/lib/utils'

const SIZE_CLASS = {
  xs: 'h-3.5 w-3.5',
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
} as const

interface RetailerLogoProps {
  slug: string | null | undefined
  size?: keyof typeof SIZE_CLASS
  className?: string
}

export function RetailerLogo({ slug, size = 'sm', className }: RetailerLogoProps) {
  const src = retailerLogoSrc(slug)
  if (!src) return null

  return (
    <img
      src={src}
      alt=""
      aria-hidden
      className={cn('shrink-0 rounded-[3px] object-contain', SIZE_CLASS[size], className)}
    />
  )
}

interface RetailerIdentityProps {
  slug: string | null | undefined
  size?: keyof typeof SIZE_CLASS
  className?: string
  labelClassName?: string
}

/** Logo + human-readable retailer name for inline display. */
export function RetailerIdentity({
  slug,
  size = 'sm',
  className,
  labelClassName,
}: RetailerIdentityProps) {
  return (
    <span className={cn('inline-flex min-w-0 items-center gap-1.5', className)}>
      <RetailerLogo slug={slug} size={size} />
      <span className={cn('truncate', labelClassName)}>{retailerLabel(slug)}</span>
    </span>
  )
}
