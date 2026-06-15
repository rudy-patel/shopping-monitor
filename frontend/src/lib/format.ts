const CAD_FORMATTER = new Intl.NumberFormat('en-CA', {
  style: 'currency',
  currency: 'CAD',
})

const RETAILER_LABELS: Record<string, string> = {
  bestbuy_ca: 'Best Buy Canada',
  indigo: 'Indigo',
  apple_ca: 'Apple Canada',
  abercrombie: 'Abercrombie & Fitch',
  amazon_ca: 'Amazon.ca',
  nike_ca: 'Nike Canada',
  palmisleskate: 'Palm Isle Skate Shop',
  tikiroomskate: 'Tiki Room Skateboards',
  generic: 'Generic scraper — may be unreliable',
}

/** Slugs with human labels in `RETAILER_LABELS`, excluding the generic scraper. */
export function knownRetailerSlugs(): string[] {
  return Object.keys(RETAILER_LABELS).filter((slug) => slug !== 'generic')
}

export function formatCadCents(cents: number | null | undefined): string {
  if (cents == null) return '—'
  return CAD_FORMATTER.format(cents / 100)
}

export function formatTrackingSince(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return date.toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return 'Never'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'Unknown'

  const diffMs = Date.now() - date.getTime()
  const diffMinutes = Math.floor(diffMs / 60_000)
  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays}d ago`

  return date.toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function retailerLabel(slug: string | null | undefined): string {
  if (!slug) return 'Unknown retailer'
  return RETAILER_LABELS[slug] ?? slug.replace(/_/g, ' ')
}

/** Derive a friendly retailer label from a URL hostname (used for search results
 *  that resolve to the generic scraper, where the slug doesn't carry the retailer
 *  identity). Mirrors `services/retailer_labels.label_from_url`. */
export function retailerLabelFromUrl(url: string, fallback?: string | null): string {
  const trimmed = fallback?.trim()
  if (trimmed) return trimmed
  let host = ''
  try {
    host = new URL(url).hostname.toLowerCase()
  } catch {
    return 'Unknown retailer'
  }
  if (host.startsWith('www.')) host = host.slice(4)
  if (!host) return 'Unknown retailer'
  const primary = host.split('.')[0]
  if (!primary) return host
  return primary.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function extraRetailerCount(listingCount: number): string | null {
  const extra = listingCount - 1
  if (extra <= 0) return null
  return `+${extra} retailer${extra === 1 ? '' : 's'}`
}
