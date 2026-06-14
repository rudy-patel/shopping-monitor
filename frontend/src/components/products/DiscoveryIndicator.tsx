import type { ProductSummary } from '@/lib/products'

interface DiscoveryIndicatorProps {
  status: ProductSummary['discovery_status']
}

const LABELS: Record<string, string> = {
  pending: 'Finding more retailers',
  complete: 'Discovery complete',
  failed: 'Discovery unavailable',
}

export function DiscoveryIndicator({ status }: DiscoveryIndicatorProps) {
  const label = LABELS[status] ?? status
  return <span className="text-xs text-muted-foreground">{label}</span>
}
