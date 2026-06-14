const CAD_FORMATTER = new Intl.NumberFormat('en-CA', {
  style: 'currency',
  currency: 'CAD',
})

const RETAILER_LABELS: Record<string, string> = {
  bestbuy_ca: 'Best Buy Canada',
  indigo: 'Indigo',
  apple_ca: 'Apple Canada',
  abercrombie: 'Abercrombie & Fitch',
  palmisleskate: 'Palm Isle Skate Shop',
  tikiroomskate: 'Tiki Room Skateboards',
  generic: 'Generic scraper — may be unreliable',
}

export function formatCadCents(cents: number | null | undefined): string {
  if (cents == null) return '—'
  return CAD_FORMATTER.format(cents / 100)
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

export function extraRetailerCount(listingCount: number): string | null {
  const extra = listingCount - 1
  if (extra <= 0) return null
  return `+${extra} retailer${extra === 1 ? '' : 's'}`
}
