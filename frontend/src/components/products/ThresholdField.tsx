import { useEffect, useMemo, useState } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { useUpdateProduct } from '@/hooks/useProducts'
import type { PriceHistoryPoint } from '@/lib/products'
import {
  baselineMaxCentsFromHistory,
  effectiveThresholdPct,
  thresholdTriggerCents,
} from '@/lib/pricing'

interface ThresholdFieldProps {
  productId: string
  value: number | null
  effectiveDefault: number
  bestPriceCents?: number | null
  priceHistory?: PriceHistoryPoint[]
}

export function ThresholdField({
  productId,
  value,
  effectiveDefault,
  bestPriceCents = null,
  priceHistory = [],
}: ThresholdFieldProps) {
  const update = useUpdateProduct(productId)
  const formatPriceCents = useFormatPriceCents()
  const [draft, setDraft] = useState(value?.toString() ?? '')

  useEffect(() => {
    setDraft(value?.toString() ?? '')
  }, [value])

  const commit = () => {
    const trimmed = draft.trim()
    if (!trimmed) {
      setDraft(value?.toString() ?? '')
      return
    }
    const parsed = Number(trimmed)
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 95) {
      setDraft(value?.toString() ?? '')
      return
    }
    if (parsed === value) return
    update.mutate({ notification_threshold_pct: parsed })
  }

  const triggerHint = useMemo(() => {
    const baseline = baselineMaxCentsFromHistory(priceHistory, bestPriceCents)
    if (baseline == null || baseline <= 0) return null

    const thresholdPct = effectiveThresholdPct(draft, value, effectiveDefault)
    const triggerCents = thresholdTriggerCents(baseline, thresholdPct)
    return {
      triggerLabel: formatPriceCents(triggerCents),
      baselineLabel: formatPriceCents(baseline),
      thresholdPct,
    }
  }, [bestPriceCents, draft, effectiveDefault, formatPriceCents, priceHistory, value])

  return (
    <div className="grid gap-2">
      <Label htmlFor="threshold">Notification threshold (%)</Label>
      <Input
        id="threshold"
        type="number"
        min={1}
        max={95}
        placeholder={`Default ${effectiveDefault}%`}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        disabled={update.isPending}
      />
      {triggerHint ? (
        <p className="text-xs text-muted-foreground" data-testid="threshold-trigger-hint">
          Alert when below {triggerHint.triggerLabel} ({triggerHint.thresholdPct}% off{' '}
          {triggerHint.baselineLabel})
        </p>
      ) : null}
      <p className="text-xs text-muted-foreground">
        Leave blank to use your default of {effectiveDefault}%.
      </p>
    </div>
  )
}
