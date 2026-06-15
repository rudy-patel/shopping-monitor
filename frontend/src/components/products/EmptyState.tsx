import type { ReactNode } from 'react'
import { BrandMark } from '@/components/brand/BrandMark'

interface EmptyStateProps {
  title: string
  description: string
  action?: ReactNode
  /** When true, shows the compact dashed Someday pill above the title. */
  showBrandMark?: boolean
}

export function EmptyState({ title, description, action, showBrandMark = false }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-border px-6 py-12 text-center">
      {showBrandMark ? (
        <div className="mb-6 flex justify-center">
          <BrandMark size="compact" showWings={false} />
        </div>
      ) : null}
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  )
}
