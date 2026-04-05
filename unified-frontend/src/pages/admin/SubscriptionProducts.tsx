import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Plus,
  Pencil,
  Trash2,
  Package,
  ArrowLeft,
  Save
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { subscriptionAdminApi } from '@/api/subscriptionAdmin'
import { formatISK } from '@/lib/utils'
import type { Product, ProductCreate, ProductUpdate } from '@/types/subscription'

export default function SubscriptionProducts() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  const { data: products, isLoading } = useQuery({
    queryKey: ['subscription-products'],
    queryFn: subscriptionAdminApi.getProducts,
  })

  const createMutation = useMutation({
    mutationFn: subscriptionAdminApi.createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription-products'] })
      setIsCreateOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductUpdate }) =>
      subscriptionAdminApi.updateProduct(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription-products'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: subscriptionAdminApi.deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription-products'] })
    },
  })

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/admin/subscriptions">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Products</h1>
            <p className="text-muted-foreground">Manage subscription products and pricing</p>
          </div>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Product
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Create Product</DialogTitle>
            </DialogHeader>
            <ProductForm
              onSubmit={(data) => createMutation.mutate(data as ProductCreate)}
              isLoading={createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Products Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-6 w-32 mb-2" />
                <Skeleton className="h-4 w-full mb-4" />
                <Skeleton className="h-8 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {products?.map((product) => (
            <Card key={product.id} className={!product.is_active ? 'opacity-60' : ''}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Package className="h-5 w-5 text-blue-500" />
                    <CardTitle className="text-lg">{product.name}</CardTitle>
                  </div>
                  <Badge variant={product.is_active ? 'default' : 'secondary'}>
                    {product.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  {product.description || 'No description'}
                </p>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-green-500">
                      {formatISK(product.price_isk)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {product.duration_days} days
                    </p>
                  </div>
                </div>

                {product.features.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {product.features.map((feature) => (
                      <Badge key={feature} variant="outline" className="text-xs">
                        {feature}
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                      >
                        <Pencil className="h-4 w-4 mr-1" />
                        Edit
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-md">
                      <DialogHeader>
                        <DialogTitle>Edit Product</DialogTitle>
                      </DialogHeader>
                      <ProductForm
                        product={product}
                        onSubmit={(data) => updateMutation.mutate({ id: product.id, data: data as ProductUpdate })}
                        isLoading={updateMutation.isPending}
                      />
                    </DialogContent>
                  </Dialog>

                  <Button
                    variant="outline"
                    size="sm"
                    className="text-red-500 hover:text-red-600"
                    onClick={() => {
                      if (confirm(`Deactivate "${product.name}"?`)) {
                        deleteMutation.mutate(product.id)
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Deactivate
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {products?.length === 0 && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Package className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No products yet</p>
            <Button className="mt-4" onClick={() => setIsCreateOpen(true)}>
              Create First Product
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Product Form Component
function ProductForm({
  product,
  onSubmit,
  isLoading,
}: {
  product?: Product
  onSubmit: (data: ProductCreate | ProductUpdate) => void
  isLoading: boolean
}) {
  const [formData, setFormData] = useState({
    slug: product?.slug ?? '',
    name: product?.name ?? '',
    description: product?.description ?? '',
    price_isk: product?.price_isk ?? 50000000,
    duration_days: product?.duration_days ?? 30,
    is_active: product?.is_active ?? true,
    features: product?.features?.join(', ') ?? '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      ...formData,
      features: formData.features.split(',').map((f) => f.trim()).filter(Boolean),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-sm font-medium">Slug (URL-friendly)</label>
        <Input
          value={formData.slug}
          onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
          placeholder="alliance-intel-basic"
          required
        />
      </div>

      <div>
        <label className="text-sm font-medium">Name</label>
        <Input
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Alliance Intelligence Basic"
          required
        />
      </div>

      <div>
        <label className="text-sm font-medium">Description</label>
        <Input
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Access to alliance intelligence features"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Price (ISK)</label>
          <Input
            type="number"
            value={formData.price_isk}
            onChange={(e) => setFormData({ ...formData, price_isk: parseInt(e.target.value) })}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium">Duration (Days)</label>
          <Input
            type="number"
            value={formData.duration_days}
            onChange={(e) => setFormData({ ...formData, duration_days: parseInt(e.target.value) })}
            required
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-medium">Features (comma-separated)</label>
        <Input
          value={formData.features}
          onChange={(e) => setFormData({ ...formData, features: e.target.value })}
          placeholder="alliance-intel, battle-reports, war-economy"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active"
          checked={formData.is_active}
          onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
        />
        <label htmlFor="is_active" className="text-sm">Active</label>
      </div>

      <Button type="submit" className="w-full" disabled={isLoading}>
        <Save className="h-4 w-4 mr-2" />
        {isLoading ? 'Saving...' : 'Save Product'}
      </Button>
    </form>
  )
}
