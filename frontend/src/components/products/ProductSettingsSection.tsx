import { useEffect, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { CategoryField } from '@/components/products/CategoryField'
import { ThresholdField } from '@/components/products/ThresholdField'
import { useJustAddedCategoryThinking } from '@/lib/just-added-product'
import type { ProductDetail } from '@/lib/products'
import { cn } from '@/lib/utils'

interface ProductSettingsSectionProps {
  product: ProductDetail
}

export function ProductSettingsSection({ product }: ProductSettingsSectionProps) {
  const { isThinking } = useJustAddedCategoryThinking(product.id)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (isThinking) {
      setOpen(true)
    }
  }, [isThinking])

  return (
    <section className="space-y-3">
      <h2
        id="settings-heading"
        className="border-b border-border pb-2 text-lg font-semibold tracking-tight"
      >
        <button
          type="button"
          className="flex w-full items-center justify-between text-left"
          aria-expanded={open}
          aria-controls="settings-panel"
          onClick={() => setOpen((prev) => !prev)}
        >
          Settings
          <ChevronDown
            className={cn(
              'h-5 w-5 text-muted-foreground transition-transform',
              open && 'rotate-180',
            )}
            aria-hidden
          />
        </button>
      </h2>
      {open ? (
        <div id="settings-panel" role="region" aria-labelledby="settings-heading">
          <div className="grid gap-6 pt-2 sm:grid-cols-2">
            <CategoryField productId={product.id} value={product.category} />
            <ThresholdField
              productId={product.id}
              value={product.notification_threshold_pct}
              effectiveDefault={product.effective_threshold_pct}
              bestPriceCents={product.best_price_cents}
              priceHistory={product.price_history_30d}
            />
          </div>
        </div>
      ) : null}
    </section>
  )
}
