import { ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { StockBadge } from '@/components/products/StockBadge'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { formatRelativeTime, retailerLabel } from '@/lib/format'
import type { Listing } from '@/lib/products'
import { cn } from '@/lib/utils'

interface ListingCardProps {
  listing: Listing
  onRemove?: (listingId: string) => void
  isRemoving?: boolean
  isBestPrice?: boolean
  priceDeltaVsBestCents?: number | null
}

function canRemove(listing: Listing): boolean {
  return (
    !listing.is_primary &&
    (listing.review_status === 'auto_added' || listing.review_status === 'accepted')
  )
}

export function ListingCard({
  listing,
  onRemove,
  isRemoving = false,
  isBestPrice = false,
  priceDeltaVsBestCents = null,
}: ListingCardProps) {
  const formatPriceCents = useFormatPriceCents()
  const isGeneric = listing.retailer_slug === 'generic'
  const matchPct =
    !listing.is_primary && listing.match_confidence != null
      ? `${Math.round(listing.match_confidence * 100)}% match`
      : null

  return (
    <div
      className={cn(
        'rounded-lg border border-border p-4 space-y-2',
        isBestPrice && 'border-l-[3px] border-l-foreground/35 pl-[calc(1rem-1px)]',
      )}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <p className="text-xl font-semibold tabular-nums tracking-tight md:text-2xl">
          {formatPriceCents(listing.last_known_price_cents)}
        </p>
        {priceDeltaVsBestCents != null ? (
          <span className="text-xs text-muted-foreground">
            +{formatPriceCents(priceDeltaVsBestCents)} vs best
          </span>
        ) : null}
        {isBestPrice ? (
          <Badge variant="outline" className="text-xs font-normal">
            Best price
          </Badge>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-sm font-medium">{retailerLabel(listing.retailer_slug)}</span>
        <StockBadge inStock={listing.is_in_stock} />
        <span className="text-xs text-muted-foreground">
          {formatRelativeTime(listing.last_scraped_at)}
        </span>
      </div>

      {isGeneric ? (
        <p className="text-xs text-muted-foreground">Generic scraper — may be unreliable</p>
      ) : null}
      {matchPct ? <p className="text-xs text-muted-foreground">{matchPct}</p> : null}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-1">
        <Button
          variant="link"
          size="sm"
          className="h-auto p-0 text-sm font-normal text-muted-foreground"
          asChild
        >
          <a href={listing.url} target="_blank" rel="noopener noreferrer">
            Open on {retailerLabel(listing.retailer_slug)}
            <ExternalLink className="ml-1 inline h-3 w-3" />
          </a>
        </Button>
        {canRemove(listing) && onRemove ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-auto p-0 text-sm font-normal text-muted-foreground"
            disabled={isRemoving}
            onClick={() => onRemove(listing.id)}
          >
            Remove
          </Button>
        ) : null}
      </div>
    </div>
  )
}
