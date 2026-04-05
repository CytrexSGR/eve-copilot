import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useCharacterAssets } from '@/hooks/useCharacters'
import type { Asset, AssetLocation } from '@/types/character'
import { cn } from '@/lib/utils'
import {
  Package,
  Search,
  ChevronDown,
  ChevronRight,
  X,
  MapPin,
  Filter,
} from 'lucide-react'

interface AssetsTabProps {
  characterId: number
}

/**
 * Get EVE Online item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Format large numbers with commas
 */
function formatNumber(value: number): string {
  return value.toLocaleString()
}

/**
 * Location group component with collapsible content
 */
function LocationGroup({
  location,
  defaultExpanded = false,
}: {
  location: AssetLocation
  defaultExpanded?: boolean
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <Card className="overflow-hidden">
      <button
        className="w-full text-left"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <CardHeader className="pb-3 cursor-pointer hover:bg-secondary/30 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isExpanded ? (
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              )}
              <MapPin className="h-4 w-4 text-primary" />
              <CardTitle className="text-base font-medium">
                {location.location_name}
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-xs">
                {location.assets.length} {location.assets.length === 1 ? 'type' : 'types'}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {formatNumber(location.total_items)} items
              </Badge>
            </div>
          </div>
        </CardHeader>
      </button>

      {isExpanded && (
        <CardContent className="pt-0">
          <div className="border-t border-border pt-3">
            <div className="space-y-1">
              {location.assets.map((asset) => (
                <AssetItem key={asset.item_id} asset={asset} />
              ))}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

/**
 * Single asset item display
 */
function AssetItem({ asset }: { asset: Asset }) {
  return (
    <div className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-secondary/30 transition-colors">
      {/* Item Icon */}
      <div className="flex-shrink-0">
        <img
          src={getItemIconUrl(asset.type_id, 32)}
          alt={asset.type_name}
          className="w-8 h-8 rounded"
          loading="lazy"
          onError={(e) => {
            // Fallback to a placeholder on error
            e.currentTarget.style.display = 'none'
          }}
        />
      </div>

      {/* Item Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{asset.type_name}</span>
          {asset.is_singleton && (
            <Badge variant="outline" className="text-xs py-0">
              Single
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{asset.group_name}</span>
          <span className="text-border">|</span>
          <span>{asset.category_name}</span>
        </div>
      </div>

      {/* Quantity */}
      <div className="flex-shrink-0 text-right">
        <span className="font-mono text-sm">
          x{formatNumber(asset.quantity)}
        </span>
      </div>
    </div>
  )
}

/**
 * Loading skeleton for assets
 */
function AssetsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex gap-4 mb-6">
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 w-40" />
      </div>
      {[1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-48" />
              <div className="flex gap-2">
                <Skeleton className="h-5 w-16" />
                <Skeleton className="h-5 w-20" />
              </div>
            </div>
          </CardHeader>
        </Card>
      ))}
    </div>
  )
}

/**
 * Empty state when no assets match filters
 */
function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <Card>
      <CardContent className="py-12">
        <div className="flex flex-col items-center justify-center text-center">
          <Package className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">
            {hasFilters ? 'No matching assets' : 'No assets found'}
          </h3>
          <p className="text-muted-foreground max-w-sm">
            {hasFilters
              ? 'Try adjusting your search or filter criteria.'
              : 'This character has no assets or the data is still loading.'}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Sort options for assets
 */
type SortOption = 'name' | 'quantity' | 'location'

/**
 * Main AssetsTab component
 */
export function AssetsTab({ characterId }: AssetsTabProps) {
  const { data, isLoading, error } = useCharacterAssets(characterId)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<SortOption>('location')

  // Get unique categories for filter dropdown
  const categories = useMemo(() => {
    if (!data?.assets) return []
    const uniqueCategories = [...new Set(data.assets.map((a) => a.category_name))]
    return uniqueCategories.filter((c) => c && c !== 'Unknown').sort()
  }, [data])

  // Group and filter assets by location
  const groupedAssets = useMemo(() => {
    if (!data?.assets) return []

    // Apply search and category filter
    const filtered = data.assets.filter((a) => {
      const matchesSearch =
        !search ||
        a.type_name.toLowerCase().includes(search.toLowerCase()) ||
        a.group_name.toLowerCase().includes(search.toLowerCase())
      const matchesCategory =
        !categoryFilter || a.category_name === categoryFilter
      return matchesSearch && matchesCategory
    })

    // Group by location
    const groups = new Map<number, AssetLocation>()
    for (const asset of filtered) {
      if (!groups.has(asset.location_id)) {
        groups.set(asset.location_id, {
          location_id: asset.location_id,
          location_name: asset.location_name || 'Unknown Location',
          location_type: asset.location_type || 'unknown',
          assets: [],
          total_items: 0,
        })
      }
      const group = groups.get(asset.location_id)!
      group.assets.push(asset)
      group.total_items += asset.quantity
    }

    // Convert to array and sort assets within each group
    const result = Array.from(groups.values())

    // Sort assets within each location group
    for (const group of result) {
      group.assets.sort((a, b) => {
        if (sortBy === 'name') {
          return a.type_name.localeCompare(b.type_name)
        } else if (sortBy === 'quantity') {
          return b.quantity - a.quantity
        }
        return 0
      })
    }

    // Sort location groups by total items (descending) or name
    result.sort((a, b) => {
      if (sortBy === 'location') {
        return a.location_name.localeCompare(b.location_name)
      }
      return b.total_items - a.total_items
    })

    return result
  }, [data, search, categoryFilter, sortBy])

  // Calculate totals
  const totalAssets = groupedAssets.reduce((sum, g) => sum + g.total_items, 0)
  const totalTypes = groupedAssets.reduce((sum, g) => sum + g.assets.length, 0)
  const hasFilters = !!search || !!categoryFilter

  // Handle errors
  if (error) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center text-center">
            <Package className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-medium mb-2">Failed to load assets</h3>
            <p className="text-muted-foreground max-w-sm">
              {error instanceof Error ? error.message : 'An error occurred while loading assets.'}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Loading state
  if (isLoading) {
    return <AssetsSkeleton />
  }

  return (
    <div className="space-y-4">
      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by item name or group..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={cn(
              'w-full pl-10 pr-4 py-2 rounded-md',
              'bg-secondary/50 border border-border',
              'text-foreground placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
              'transition-colors'
            )}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Category Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <select
            value={categoryFilter ?? ''}
            onChange={(e) => setCategoryFilter(e.target.value || null)}
            className={cn(
              'pl-10 pr-8 py-2 rounded-md appearance-none cursor-pointer min-w-[160px]',
              'bg-secondary/50 border border-border',
              'text-foreground',
              'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
              'transition-colors'
            )}
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>

        {/* Sort Options */}
        <div className="flex gap-1">
          <Button
            variant={sortBy === 'location' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSortBy('location')}
            className="text-xs"
          >
            Location
          </Button>
          <Button
            variant={sortBy === 'name' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSortBy('name')}
            className="text-xs"
          >
            Name
          </Button>
          <Button
            variant={sortBy === 'quantity' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSortBy('quantity')}
            className="text-xs"
          >
            Quantity
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <span>
          <strong className="text-foreground">{groupedAssets.length}</strong>{' '}
          {groupedAssets.length === 1 ? 'location' : 'locations'}
        </span>
        <span className="text-border">|</span>
        <span>
          <strong className="text-foreground">{formatNumber(totalTypes)}</strong>{' '}
          item types
        </span>
        <span className="text-border">|</span>
        <span>
          <strong className="text-foreground">{formatNumber(totalAssets)}</strong>{' '}
          total items
        </span>
        {hasFilters && (
          <>
            <span className="text-border">|</span>
            <button
              onClick={() => {
                setSearch('')
                setCategoryFilter(null)
              }}
              className="text-primary hover:underline"
            >
              Clear filters
            </button>
          </>
        )}
      </div>

      {/* Location Groups */}
      {groupedAssets.length === 0 ? (
        <EmptyState hasFilters={hasFilters} />
      ) : (
        <div className="space-y-3">
          {groupedAssets.map((location, index) => (
            <LocationGroup
              key={location.location_id}
              location={location}
              defaultExpanded={index === 0}
            />
          ))}
        </div>
      )}
    </div>
  )
}
