import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical } from 'lucide-react'
import { ProductListRow } from '@/components/products/ProductListRow'
import type { ProductSummary } from '@/lib/products'
import { cn } from '@/lib/utils'

interface SortableProductRowProps {
  product: ProductSummary
}

export function SortableProductRow({ product }: SortableProductRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `product-${product.id}`,
    data: { type: 'product', productId: product.id, category: product.category },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(isDragging && 'relative z-20 opacity-90')}
    >
      <div className="flex items-stretch gap-2">
        <button
          type="button"
          className="inline-flex w-8 shrink-0 cursor-grab items-center justify-center self-center rounded-md text-muted-foreground hover:bg-muted active:cursor-grabbing"
          aria-label={`Drag ${product.title}`}
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <div className="min-w-0 flex-1">
          <ProductListRow product={product} />
        </div>
      </div>
    </div>
  )
}
