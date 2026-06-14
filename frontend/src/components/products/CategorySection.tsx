import type { ReactNode } from 'react'
import { categoryLabel, type ProductCategory } from '@/lib/categories'

interface CategorySectionProps {
  category: ProductCategory
  children: ReactNode
}

export function CategorySection({ category, children }: CategorySectionProps) {
  return (
    <section className="space-y-4">
      <div className="border-b border-border pb-2">
        <h2 className="text-lg font-semibold tracking-tight">{categoryLabel(category)}</h2>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  )
}
