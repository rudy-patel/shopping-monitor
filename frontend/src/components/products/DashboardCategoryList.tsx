import { useCallback, useMemo, useState, type CSSProperties, type HTMLAttributes } from 'react'
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  type DragEndEvent,
  type DragStartEvent,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { AnimatePresence } from 'framer-motion'
import { CategorySection } from '@/components/products/CategorySection'
import { ProductListRow } from '@/components/products/ProductListRow'
import { SortableProductRow } from '@/components/products/SortableProductRow'
import { useReorderDashboardProducts } from '@/hooks/useProducts'
import {
  CATEGORY_ORDER,
  groupByCategory,
  sortProductsInCategory,
  type ProductCategory,
} from '@/lib/categories'
import {
  hasStoredCollapsePreference,
  isCategoryExpanded,
  readCategoryOrder,
  readCollapsedCategories,
  saveCategoryOrder,
  saveCollapsedCategories,
} from '@/lib/dashboard-layout'
import type { ProductSummary } from '@/lib/products'

interface DashboardCategoryListProps {
  products: ProductSummary[]
  editMode: boolean
}

function categoryDragId(category: ProductCategory) {
  return `category-${category}`
}

function productDragId(productId: string) {
  return `product-${productId}`
}

function parseDragId(id: string | number): { type: 'category' | 'product'; value: string } | null {
  const raw = String(id)
  if (raw.startsWith('category-')) {
    return { type: 'category', value: raw.slice('category-'.length) }
  }
  if (raw.startsWith('product-')) {
    return { type: 'product', value: raw.slice('product-'.length) }
  }
  return null
}

function useDashboardCategories(products: ProductSummary[]) {
  const [categoryOrder, setCategoryOrder] = useState<ProductCategory[]>(() => readCategoryOrder())
  const [collapsed, setCollapsed] = useState<Set<ProductCategory>>(() => readCollapsedCategories())
  const [hasStoredCollapsePref, setHasStoredCollapsePref] = useState(hasStoredCollapsePreference)

  const itemsByCategory = useMemo(() => {
    const grouped = groupByCategory(products)
    const next = new Map<ProductCategory, ProductSummary[]>()
    for (const category of CATEGORY_ORDER) {
      next.set(category, sortProductsInCategory(grouped.get(category) ?? []))
    }
    return next
  }, [products])

  const toggleCategory = useCallback((category: ProductCategory) => {
    setHasStoredCollapsePref(true)
    setCollapsed((current) => {
      const next = new Set(current)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      saveCollapsedCategories(next)
      return next
    })
  }, [])

  return {
    categoryOrder,
    setCategoryOrder,
    collapsed,
    hasStoredCollapsePref,
    itemsByCategory,
    toggleCategory,
  }
}

interface CategoryBlockProps {
  category: ProductCategory
  count: number
  expanded: boolean
  editMode: boolean
  onToggle: () => void
  items: ProductSummary[]
  dragHandleProps?: HTMLAttributes<HTMLButtonElement>
  containerRef?: (node: HTMLElement | null) => void
  containerStyle?: CSSProperties
}

function CategoryBlock({
  category,
  count,
  expanded,
  editMode,
  onToggle,
  items,
  dragHandleProps,
  containerRef,
  containerStyle,
}: CategoryBlockProps) {
  return (
    <div ref={containerRef} style={containerStyle}>
      <CategorySection
        category={category}
        count={count}
        expanded={expanded}
        editMode={editMode}
        dragHandleProps={dragHandleProps}
        onToggle={onToggle}
      >
        {count === 0 ? (
          <p className="py-2 text-sm text-muted-foreground">No products in this category yet.</p>
        ) : editMode ? (
          <SortableContext
            items={items.map((product) => productDragId(product.id))}
            strategy={verticalListSortingStrategy}
          >
            {items.map((product) => (
              <SortableProductRow key={product.id} product={product} />
            ))}
          </SortableContext>
        ) : (
          <AnimatePresence initial={false}>
            {items.map((product) => (
              <ProductListRow key={product.id} product={product} />
            ))}
          </AnimatePresence>
        )}
      </CategorySection>
    </div>
  )
}

function SortableCategoryBlock({
  category,
  count,
  expanded,
  editMode,
  onToggle,
  items,
}: Omit<CategoryBlockProps, 'dragHandleProps' | 'containerRef' | 'containerStyle'>) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: categoryDragId(category),
    data: { type: 'category', category },
  })

  return (
    <CategoryBlock
      category={category}
      count={count}
      expanded={expanded}
      editMode={editMode}
      onToggle={onToggle}
      items={items}
      dragHandleProps={{ ...attributes, ...listeners }}
      containerRef={setNodeRef}
      containerStyle={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : undefined,
      }}
    />
  )
}

function DashboardCategorySections({
  categoryOrder,
  itemsByCategory,
  collapsed,
  hasStoredCollapsePref,
  editMode,
  toggleCategory,
}: {
  categoryOrder: ProductCategory[]
  itemsByCategory: Map<ProductCategory, ProductSummary[]>
  collapsed: Set<ProductCategory>
  hasStoredCollapsePref: boolean
  editMode: boolean
  toggleCategory: (category: ProductCategory) => void
}) {
  return (
    <div className="space-y-5 md:space-y-6">
      {categoryOrder.map((category) => {
        const items = itemsByCategory.get(category) ?? []
        const count = items.length
        const expanded = isCategoryExpanded(category, count, collapsed, hasStoredCollapsePref)
        const common = {
          category,
          count,
          expanded,
          editMode,
          onToggle: () => toggleCategory(category),
          items,
        }

        return editMode ? (
          <SortableCategoryBlock key={category} {...common} />
        ) : (
          <CategoryBlock key={category} {...common} />
        )
      })}
    </div>
  )
}

export function DashboardCategoryList({ products, editMode }: DashboardCategoryListProps) {
  const reorder = useReorderDashboardProducts()
  const {
    categoryOrder,
    setCategoryOrder,
    collapsed,
    hasStoredCollapsePref,
    itemsByCategory,
    toggleCategory,
  } = useDashboardCategories(products)
  const [activeProduct, setActiveProduct] = useState<ProductSummary | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const persistProductOrder = useCallback(
    (category: ProductCategory, items: ProductSummary[]) => {
      reorder.mutate(
        items.map((product, index) => ({
          id: product.id,
          dashboard_sort_order: index,
        })),
      )
    },
    [reorder],
  )

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const parsed = parseDragId(event.active.id)
      if (parsed?.type !== 'product') {
        setActiveProduct(null)
        return
      }
      for (const items of itemsByCategory.values()) {
        const match = items.find((product) => product.id === parsed.value)
        if (match) {
          setActiveProduct(match)
          break
        }
      }
    },
    [itemsByCategory],
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveProduct(null)
      const { active, over } = event
      if (!over || active.id === over.id) return

      const activeParsed = parseDragId(active.id)
      const overParsed = parseDragId(over.id)
      if (!activeParsed || !overParsed) return

      if (activeParsed.type === 'category' && overParsed.type === 'category') {
        setCategoryOrder((current) => {
          const oldIndex = current.indexOf(activeParsed.value as ProductCategory)
          const newIndex = current.indexOf(overParsed.value as ProductCategory)
          if (oldIndex < 0 || newIndex < 0) return current
          const next = arrayMove(current, oldIndex, newIndex)
          saveCategoryOrder(next)
          return next
        })
        return
      }

      if (activeParsed.type !== 'product' || overParsed.type !== 'product') return

      const activeCategory = active.data.current?.category as ProductCategory | undefined
      const overCategory = over.data.current?.category as ProductCategory | undefined
      if (!activeCategory || activeCategory !== overCategory) return

      const items = itemsByCategory.get(activeCategory) ?? []
      const oldIndex = items.findIndex((product) => product.id === activeParsed.value)
      const newIndex = items.findIndex((product) => product.id === overParsed.value)
      if (oldIndex < 0 || newIndex < 0 || oldIndex === newIndex) return

      persistProductOrder(activeCategory, arrayMove(items, oldIndex, newIndex))
    },
    [itemsByCategory, persistProductOrder, setCategoryOrder],
  )

  const sections = (
    <DashboardCategorySections
      categoryOrder={categoryOrder}
      itemsByCategory={itemsByCategory}
      collapsed={collapsed}
      hasStoredCollapsePref={hasStoredCollapsePref}
      editMode={editMode}
      toggleCategory={toggleCategory}
    />
  )

  if (!editMode) {
    return sections
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={categoryOrder.map(categoryDragId)}
        strategy={verticalListSortingStrategy}
      >
        {sections}
      </SortableContext>
      <DragOverlay>
        {activeProduct ? (
          <div className="rounded-lg border border-border bg-background shadow-lg">
            <ProductListRow product={activeProduct} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
