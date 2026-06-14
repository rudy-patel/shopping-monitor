import {
  CATEGORY_ORDER,
  categoryLabel,
  type ProductCategory,
} from '@/lib/categories'
import { retailerLabel } from '@/lib/format'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'

export interface ListFilterState {
  category: ProductCategory | 'all'
  retailer: string | 'all'
  needsReview: boolean
}

interface ListFiltersProps {
  filters: ListFilterState
  retailers: string[]
  onChange: (next: ListFilterState) => void
}

export function ListFilters({ filters, retailers, onChange }: ListFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="grid gap-2">
        <Label htmlFor="filter-category">Category</Label>
        <Select
          value={filters.category}
          onValueChange={(value) =>
            onChange({ ...filters, category: value as ListFilterState['category'] })
          }
        >
          <SelectTrigger id="filter-category" className="w-[160px]">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORY_ORDER.map((category) => (
              <SelectItem key={category} value={category}>
                {categoryLabel(category)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="filter-retailer">Retailer</Label>
        <Select
          value={filters.retailer}
          onValueChange={(value) =>
            onChange({ ...filters, retailer: value as ListFilterState['retailer'] })
          }
        >
          <SelectTrigger id="filter-retailer" className="w-[200px]">
            <SelectValue placeholder="All retailers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All retailers</SelectItem>
            {retailers.map((retailer) => (
              <SelectItem key={retailer} value={retailer}>
                {retailerLabel(retailer)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={filters.needsReview}
          onChange={(event) =>
            onChange({ ...filters, needsReview: event.target.checked })
          }
          className="h-4 w-4 rounded border-border"
        />
        Has unreviewed matches
      </label>
    </div>
  )
}

export function applyListFilters<T extends {
  category: ProductCategory
  best_retailer_slug: string | null
  needs_review_count: number
}>(
  items: T[],
  filters: ListFilterState,
): T[] {
  return items.filter((item) => {
    if (filters.category !== 'all' && item.category !== filters.category) return false
    if (filters.retailer !== 'all' && item.best_retailer_slug !== filters.retailer) return false
    if (filters.needsReview && item.needs_review_count <= 0) return false
    return true
  })
}
