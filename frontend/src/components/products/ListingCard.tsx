import { ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { StockBadge } from '@/components/products/StockBadge'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { formatRelativeTime, retailerLabel } from '@/lib/format'
import type { Listing } from '@/lib/products'

interface ListingCardProps {
  listing: Listing
  onRemove?: (listingId: string) => void
  isRemoving?: boolean
}

function canRemove(listing: Listing): boolean {
  return (
    !listing.is_primary &&
    (listing.review_status === 'auto_added' || listing.review_status === 'accepted')
  )
}

export function ListingCard({ listing, onRemove, isRemoving = false }: ListingCardProps) {
  const formatPriceCents = useFormatPriceCents()
  const isGeneric = listing.retailer_slug === 'generic'
  const matchPct =
    !listing.is_primary && listing.match_confidence != null
      ? `${Math.round(listing.match_confidence * 100)}% match`
      : null

  return (
    <div className="rounded-lg border border-border p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium">{retailerLabel(listing.retailer_slug)}</p>
          {isGeneric ? (
            <p className="mt-1 text-xs text-muted-foreground">
              Generic scraper — may be unreliable
            </p>
          ) : null}
          {matchPct ? (
            <p className="mt-1 text-xs text-muted-foreground">{matchPct}</p>
          ) : null}
        </div>
        <p className="shrink-0 font-medium tabular-nums">
          {formatPriceCents(listing.last_known_price_cents)}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <StockBadge inStock={listing.is_in_stock} />
        {listing.scrape_status ? (
          <Badge variant="outline">{listing.scrape_status}</Badge>
        ) : null}
        <span className="text-xs text-muted-foreground">
          {formatRelativeTime(listing.last_scraped_at)}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" className="h-11" asChild>
          <a href={listing.url} target="_blank" rel="noopener noreferrer">
            Open on {retailerLabel(listing.retailer_slug)}
            <ExternalLink className="ml-1 h-3 w-3" />
          </a>
        </Button>
        {canRemove(listing) && onRemove ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-11"
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
