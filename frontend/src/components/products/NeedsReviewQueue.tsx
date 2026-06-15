import { ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StockBadge } from '@/components/products/StockBadge'
import {
  useAcceptListing,
  useRejectListing,
} from '@/hooks/useProducts'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { RetailerLogo } from '@/components/retailers/RetailerLogo'
import { retailerLabel } from '@/lib/format'
import type { Listing, ProductDetail } from '@/lib/products'
import { needsReviewListings } from '@/lib/products'

interface NeedsReviewQueueProps {
  product: ProductDetail
}

function candidateTitle(listing: Listing): string {
  return listing.review_title ?? retailerLabel(listing.retailer_slug)
}

export function NeedsReviewQueue({ product }: NeedsReviewQueueProps) {
  const formatPriceCents = useFormatPriceCents()
  const queue = needsReviewListings(product.listings)
  const accept = useAcceptListing(product.id)
  const reject = useRejectListing(product.id)

  if (queue.length === 0) {
    return null
  }

  const acceptingId = accept.isPending ? accept.variables : undefined
  const rejectingId = reject.isPending ? reject.variables : undefined

  return (
    <section className="space-y-4" aria-labelledby="needs-review-heading">
      <h2
        id="needs-review-heading"
        className="border-b border-border pb-2 text-lg font-semibold tracking-tight"
      >
        Needs review ({queue.length})
      </h2>
      <ul className="space-y-3">
        {queue.map((listing) => {
          const reason = listing.review_reason ?? 'Possible match'
          const confidencePct =
            listing.match_confidence != null
              ? `${Math.round(listing.match_confidence * 100)}% match`
              : null
          const cardPending =
            acceptingId === listing.id || rejectingId === listing.id

          return (
            <li
              key={listing.id}
              className="rounded-lg border border-border p-4"
            >
              <div className="space-y-2">
                <div className="inline-flex min-w-0 items-center gap-1.5">
                  <RetailerLogo slug={listing.retailer_slug} />
                  <p className="truncate font-medium">{candidateTitle(listing)}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="tabular-nums">
                    {formatPriceCents(listing.last_known_price_cents)}
                  </span>
                  <StockBadge inStock={listing.is_in_stock} />
                </div>
                <p className="text-sm italic text-muted-foreground">&ldquo;{reason}&rdquo;</p>
                {confidencePct ? (
                  <p className="text-xs text-muted-foreground">{confidencePct}</p>
                ) : null}
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button
                    size="sm"
                    className="h-11"
                    disabled={cardPending}
                    onClick={() => accept.mutate(listing.id)}
                  >
                    Accept
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-11"
                    disabled={cardPending}
                    onClick={() => reject.mutate(listing.id)}
                  >
                    Reject
                  </Button>
                  <Button size="sm" variant="outline" className="h-11" asChild>
                    <a
                      href={listing.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open on {retailerLabel(listing.retailer_slug)}
                      <ExternalLink className="ml-1 h-3 w-3" />
                    </a>
                  </Button>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
