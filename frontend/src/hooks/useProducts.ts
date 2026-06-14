import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { ApiError } from '@/lib/api'
import {
  createProduct,
  deleteProduct,
  getProduct,
  listProducts,
  productQueryKey,
  productsQueryKey,
  refreshProduct,
  selectVariant,
  updateProduct,
  type CreateProductInput,
  type ProductDetail,
  type ProductFilters,
  type ProductSummary,
  type UpdateProductInput,
} from '@/lib/products'

function rollbackListCaches(
  queryClient: ReturnType<typeof useQueryClient>,
  snapshots: [readonly unknown[], ProductSummary[] | undefined][],
) {
  for (const [key, data] of snapshots) {
    queryClient.setQueryData(key, data)
  }
}

function snapshotListCaches(queryClient: ReturnType<typeof useQueryClient>) {
  return queryClient.getQueriesData<ProductSummary[]>({ queryKey: ['products'] })
}

function updateListCache(
  queryClient: ReturnType<typeof useQueryClient>,
  updater: (items: ProductSummary[]) => ProductSummary[],
) {
  queryClient.setQueriesData<ProductSummary[]>(
    { queryKey: ['products'], exact: false },
    (current: ProductSummary[] | undefined) => (current ? updater(current) : current),
  )
}

const ACTIVE_FILTERS: ProductFilters = { status: 'active' }

export function useProducts(filters: ProductFilters = ACTIVE_FILTERS) {
  return useQuery<ProductSummary[]>({
    queryKey: productsQueryKey(filters),
    queryFn: () => listProducts(filters),
  })
}

export function useProduct(id: string | undefined) {
  return useQuery<ProductDetail>({
    queryKey: productQueryKey(id ?? ''),
    queryFn: () => {
      if (!id) throw new Error('Product id is required')
      return getProduct(id)
    },
    enabled: Boolean(id),
  })
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (input: CreateProductInput) => createProduct(input),
    onSuccess: (product) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      if (product.status === 'needs_input') {
        navigate(`/products/${product.id}/variants`)
      } else {
        navigate(`/products/${product.id}`)
      }
    },
    onError: (error) => {
      const message = error instanceof ApiError ? error.message : 'Could not add product'
      toast.error(message)
    },
  })
}

export function useUpdateProduct(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (patch: UpdateProductInput) => updateProduct(id, patch),
    onMutate: async (patch) => {
      await queryClient.cancelQueries({ queryKey: productQueryKey(id) })
      const previousDetail = queryClient.getQueryData<ProductDetail>(productQueryKey(id))
      const previousLists = snapshotListCaches(queryClient)

      if (previousDetail) {
        const optimistic: ProductDetail = {
          ...previousDetail,
          ...patch,
          category_source: patch.category ? 'manual' : previousDetail.category_source,
        }
        queryClient.setQueryData(productQueryKey(id), optimistic)
        updateListCache(queryClient, (items) =>
          items.map((item) =>
            item.id === id
              ? {
                  ...item,
                  ...patch,
                  category_source: patch.category ? 'manual' : item.category_source,
                }
              : item,
          ),
        )
      }

      return { previousDetail, previousLists }
    },
    onError: (_error, _patch, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(productQueryKey(id), context.previousDetail)
      }
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error('Could not save changes')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: productQueryKey(id) })
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useDeleteProduct({ redirectTo = '/' }: { redirectTo?: string | null } = {}) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: deleteProduct,
    onSuccess: (_result, deletedId) => {
      queryClient.removeQueries({ queryKey: productQueryKey(deletedId) })
      updateListCache(queryClient, (items) => items.filter((item) => item.id !== deletedId))
      if (redirectTo !== null) {
        navigate(redirectTo)
      }
      toast('Product deleted')
    },
    onError: () => {
      toast.error('Could not delete product')
    },
  })
}

export function useRefreshProduct(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => refreshProduct(id),
    onSuccess: (product) => {
      queryClient.setQueryData(productQueryKey(id), product)
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 429) {
        toast('Refresh is on cooldown. Try again in about an hour.')
        return
      }
      toast.error('Could not refresh product')
    },
  })
}

export function useSelectVariant(id: string) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (variantAttributes: Record<string, string>) =>
      selectVariant(id, variantAttributes),
    onSuccess: (product) => {
      queryClient.setQueryData(productQueryKey(id), product)
      queryClient.invalidateQueries({ queryKey: ['products'] })
      navigate(`/products/${id}`)
    },
    onError: () => {
      toast.error('Could not select variant')
    },
  })
}

export function useArchiveProduct(id: string) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: () => updateProduct(id, { status: 'archived' }),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['products'] })
      const previousLists = snapshotListCaches(queryClient)
      updateListCache(queryClient, (items) => items.filter((item) => item.id !== id))
      return { previousLists }
    },
    onSuccess: () => {
      toast('Product archived')
      navigate('/history')
    },
    onError: (_error, _vars, context) => {
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error('Could not archive product')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: productQueryKey(id) })
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useRestoreProduct(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => updateProduct(id, { status: 'active' }),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['products'] })
      const previousLists = snapshotListCaches(queryClient)
      updateListCache(queryClient, (items) => items.filter((item) => item.id !== id))
      return { previousLists }
    },
    onSuccess: (product) => {
      queryClient.setQueryData(productQueryKey(id), product)
      toast('Product restored to your list')
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (_error, _vars, context) => {
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error('Could not restore product')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: productQueryKey(id) })
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}