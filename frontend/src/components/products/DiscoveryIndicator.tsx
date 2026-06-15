import type { ProductSummary } from '@/lib/products'

interface DiscoveryIndicatorProps {
  status: ProductSummary['discovery_status']
}

const LABELS: Record<string, string> = {
  pending: 'Looking for other retailers…',
  running: 'Looking for other retailers…',
  failed: 'Discovery unavailable',
}

export function DiscoveryIndicator({ status }: DiscoveryIndicatorProps) {
  if (status === 'complete') return null

  const label = LABELS[status] ?? status
  return <span className="text-xs text-muted-foreground">{label}</span>
}
