import { ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { formatRelativeTime, retailerLabel } from '@/lib/format'
import type { Listing } from '@/lib/products'

interface ListingRowProps {
  listing: Listing
  onRemove?: (listingId: string) => void
  isRemoving?: boolean
}

function stockLabel(inStock: boolean | null): string {
  if (inStock === true) return 'In stock'
  if (inStock === false) return 'Out of stock'
  return 'Unknown'
}

function canRemove(listing: Listing): boolean {
  return (
    !listing.is_primary &&
    (listing.review_status === 'auto_added' || listing.review_status === 'accepted')
  )
}

export function ListingRow({ listing, onRemove, isRemoving = false }: ListingRowProps) {
  const formatPriceCents = useFormatPriceCents()
  const isGeneric = listing.retailer_slug === 'generic'
  const matchPct =
    !listing.is_primary && listing.match_confidence != null
      ? `${Math.round(listing.match_confidence * 100)}% match`
      : null

  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-3 pr-4 align-top">
        <div className="font-medium">{retailerLabel(listing.retailer_slug)}</div>
        {isGeneric ? (
          <p className="mt-1 text-xs text-muted-foreground">
            Generic scraper — may be unreliable
          </p>
        ) : null}
        {matchPct ? (
          <p className="mt-1 text-xs text-muted-foreground">{matchPct}</p>
        ) : null}
      </td>
      <td className="py-3 pr-4 align-top">{formatPriceCents(listing.last_known_price_cents)}</td>
      <td className="py-3 pr-4 align-top text-sm text-muted-foreground">
        {stockLabel(listing.is_in_stock)}
      </td>
      <td className="py-3 pr-4 align-top text-sm text-muted-foreground">
        {formatRelativeTime(listing.last_scraped_at)}
      </td>
      <td className="py-3 pr-4 align-top">
        {listing.scrape_status ? (
          <Badge variant="outline">{listing.scrape_status}</Badge>
        ) : (
          '—'
        )}
      </td>
      <td className="py-3 align-top">
        <div className="flex flex-col items-start gap-2">
          <a
            href={listing.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm underline-offset-4 hover:underline"
          >
            View
            <ExternalLink className="h-3 w-3" />
          </a>
          {canRemove(listing) && onRemove ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-auto px-0 text-sm text-muted-foreground hover:text-foreground"
              disabled={isRemoving}
              onClick={() => onRemove(listing.id)}
            >
              Remove
            </Button>
          ) : null}
        </div>
      </td>
    </tr>
  )
}
