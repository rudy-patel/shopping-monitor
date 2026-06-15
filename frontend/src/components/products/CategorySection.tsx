import type { ReactNode } from 'react'
import { ChevronRight, GripVertical } from 'lucide-react'
import { categoryLabel, type ProductCategory } from '@/lib/categories'
import { cn } from '@/lib/utils'

interface CategorySectionProps {
  category: ProductCategory
  count: number
  expanded: boolean
  editMode?: boolean
  dragHandleProps?: React.HTMLAttributes<HTMLButtonElement>
  onToggle: () => void
  children: ReactNode
}

export function CategorySection({
  category,
  count,
  expanded,
  editMode = false,
  dragHandleProps,
  onToggle,
  children,
}: CategorySectionProps) {
  const headingId = `category-${category}`

  return (
    <section className="space-y-0" aria-labelledby={headingId}>
      <div className="sticky top-14 z-10 -mx-4 border-b border-border bg-background/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="flex items-center gap-1">
          {editMode ? (
            <button
              type="button"
              className="inline-flex h-8 w-8 shrink-0 cursor-grab items-center justify-center rounded-md text-muted-foreground hover:bg-muted active:cursor-grabbing"
              aria-label={`Drag ${categoryLabel(category)} section`}
              {...dragHandleProps}
            >
              <GripVertical className="h-4 w-4" />
            </button>
          ) : null}
          <button
            type="button"
            id={headingId}
            className="flex min-w-0 flex-1 items-center gap-2 text-left"
            aria-expanded={expanded}
            onClick={onToggle}
          >
            <ChevronRight
              className={cn(
                'h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200',
                expanded && 'rotate-90',
              )}
              aria-hidden
            />
            <span className="truncate text-lg font-semibold tracking-tight">
              {categoryLabel(category)}
            </span>
            <span className="shrink-0 text-sm font-normal text-muted-foreground">· {count}</span>
          </button>
        </div>
      </div>
      {expanded ? (
        <div className="space-y-3 border-l-2 border-foreground/10 py-3 pl-3">{children}</div>
      ) : null}
    </section>
  )
}
