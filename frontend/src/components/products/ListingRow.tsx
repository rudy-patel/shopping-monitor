import { ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { formatPriceCents, formatRelativeTime, retailerLabel } from '@/lib/format'
import type { Listing } from '@/lib/products'

interface ListingRowProps {
  listing: Listing
}

function stockLabel(inStock: boolean | null): string {
  if (inStock === true) return 'In stock'
  if (inStock === false) return 'Out of stock'
  return 'Unknown'
}

export function ListingRow({ listing }: ListingRowProps) {
  const isGeneric = listing.retailer_slug === 'generic'

  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-3 pr-4 align-top">
        <div className="font-medium">{retailerLabel(listing.retailer_slug)}</div>
        {isGeneric ? (
          <p className="mt-1 text-xs text-muted-foreground">
            Generic scraper — may be unreliable
          </p>
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
        <a
          href={listing.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm underline-offset-4 hover:underline"
        >
          View
          <ExternalLink className="h-3 w-3" />
        </a>
      </td>
    </tr>
  )
}
