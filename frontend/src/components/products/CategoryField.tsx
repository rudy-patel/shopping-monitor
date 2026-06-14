import {
  CATEGORY_ORDER,
  categoryLabel,
  type ProductCategory,
} from '@/lib/categories'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUpdateProduct } from '@/hooks/useProducts'

interface CategoryFieldProps {
  productId: string
  value: ProductCategory
}

export function CategoryField({ productId, value }: CategoryFieldProps) {
  const update = useUpdateProduct(productId)

  return (
    <div className="grid gap-2">
      <Label htmlFor="category">Category</Label>
      <Select
        value={value}
        onValueChange={(next) => update.mutate({ category: next as ProductCategory })}
        disabled={update.isPending}
      >
        <SelectTrigger id="category" className="w-full max-w-xs">
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
    </div>
  )
}
