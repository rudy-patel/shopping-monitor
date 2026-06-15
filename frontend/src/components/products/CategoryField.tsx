import { Sparkles } from 'lucide-react'
import {
  CATEGORY_ORDER,
  categoryLabel,
  type ProductCategory,
} from '@/lib/categories'
import {
  revealHintLabel,
  useJustAddedCategoryThinking,
} from '@/lib/just-added-product'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUpdateProduct } from '@/hooks/useProducts'
import { CategoryFieldThinking } from './CategoryFieldThinking'

interface CategoryFieldProps {
  productId: string
  value: ProductCategory
}

export function CategoryField({ productId, value }: CategoryFieldProps) {
  const update = useUpdateProduct(productId)
  const { isThinking, showRevealHint, categorySource } =
    useJustAddedCategoryThinking(productId)

  if (isThinking) {
    return <CategoryFieldThinking />
  }

  return (
    <div className="grid gap-2">
      <Label htmlFor="category">Category</Label>
      <Select
        value={value}
        onValueChange={(next) => update.mutate({ category: next as ProductCategory })}
        disabled={update.isPending}
      >
        <SelectTrigger id="category" className="w-full max-w-xs" data-testid="category-select">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {CATEGORY_ORDER.map((category) => (
            <SelectItem key={category} value={category}>
              {categoryLabel(category)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {showRevealHint && categorySource ? (
        <p
          className="flex items-center gap-1 text-xs text-muted-foreground"
          data-testid="category-reveal-hint"
        >
          <Sparkles className="h-3 w-3" aria-hidden />
          {revealHintLabel(categorySource)}
        </p>
      ) : null}
    </div>
  )
}
