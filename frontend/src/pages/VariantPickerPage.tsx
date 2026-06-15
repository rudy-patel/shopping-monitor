import { useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ProductListRowSkeleton } from '@/components/products/ProductListRowSkeleton'
import { useProduct, useSelectVariant } from '@/hooks/useProducts'
import { normalizeVariants, primaryListing } from '@/lib/products'

export function VariantPickerPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: product, isLoading, isError } = useProduct(id)
  const selectVariant = useSelectVariant(id ?? '')

  useEffect(() => {
    if (product && product.status !== 'needs_input') {
      navigate(`/products/${product.id}`, { replace: true })
    }
  }, [product, navigate])

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <ProductListRowSkeleton />
      </div>
    )
  }

  if (isError || !product) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <p className="text-muted-foreground">Product not found.</p>
        <Link to="/" className="mt-4 inline-block text-sm underline-offset-4 hover:underline">
          Back to dashboard
        </Link>
      </div>
    )
  }

  const listing = primaryListing(product)
  const options = normalizeVariants(listing?.available_variants)

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <Link to="/" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
        Back to dashboard
      </Link>

      <div className="mt-6 space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{product.title}</h1>
          <p className="mt-2 text-muted-foreground">Pick the version you want to track.</p>
        </div>

        {options.length === 0 ? (
          <p className="text-sm text-muted-foreground">No variants available for this product.</p>
        ) : (
          <div className="space-y-3">
            {options.map((option) => (
              <Button
                key={option.label}
                variant="outline"
                className="h-11 w-full justify-start whitespace-normal px-4 py-3 text-left"
                disabled={selectVariant.isPending}
                onClick={() => selectVariant.mutate(option.attributes)}
              >
                {option.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
