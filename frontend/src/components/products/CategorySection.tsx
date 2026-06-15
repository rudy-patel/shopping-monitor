import type { ReactNode } from 'react'
import { categoryLabel, type ProductCategory } from '@/lib/categories'

interface CategorySectionProps {
  category: ProductCategory
  count: number
  children: ReactNode
}

export function CategorySection({ category, count, children }: CategorySectionProps) {
  const headingId = `category-${category}`

  return (
    <section className="space-y-3" aria-labelledby={headingId}>
      <div className="sticky top-14 z-10 -mx-4 border-b border-border bg-background/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <h2 id={headingId} className="text-lg font-semibold tracking-tight">
          {categoryLabel(category)} · {count}
        </h2>
      </div>
      <div className="space-y-3 border-l-2 border-foreground/10 pl-3">{children}</div>
    </section>
  )
}
