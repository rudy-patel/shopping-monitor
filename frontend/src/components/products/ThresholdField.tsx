import { useEffect, useState } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { useUpdateProduct } from '@/hooks/useProducts'

interface ThresholdFieldProps {
  productId: string
  value: number | null
  effectiveDefault: number
}

export function ThresholdField({ productId, value, effectiveDefault }: ThresholdFieldProps) {
  const update = useUpdateProduct(productId)
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
      <p className="text-xs text-muted-foreground">
        Leave blank to use your default of {effectiveDefault}%.
      </p>
    </div>
  )
}
