import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useCharacters } from '@/hooks/useCharacters'
import { charactersApi } from '@/api/characters'
import { cn } from '@/lib/utils'
import type { Character, ValuedAsset, LocationSummary } from '@/types/character'
import { AssetDetailModal } from '@/components/assets/AssetDetailModal'
import {
  Package,
  Search,
  ChevronDown,
  ChevronRight,
  X,
  MapPin,
  Filter,
  Users,
  LayoutGrid,
} from 'lucide-react'

/**
 * Format ISK value with appropriate suffix (K, M, B)
 */
function formatISK(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B`
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  return value.toFixed(0)
}

/**
 * Format volume in m³
 */
function formatVolume(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M m³`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K m³`
  }
  return `${value.toFixed(0)} m³`
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

// Sort types
type SortField = 'name' | 'value' | 'quantity' | 'volume'
type SortDirection = 'asc' | 'desc'

interface CharacterAssetGroup {
  character_id: number
  character_name: string
  portrait_url: string
  assets: ValuedAsset[]
  total_items: number
  total_value: number
  total_volume: number
  location_summaries: LocationSummary[]
}

/**
 * Character group component with collapsible content
 */
function CharacterGroup({
  group,
  search,
  sortField,
  sortDirection,
  defaultExpanded = false,
  onAssetSelect,
}: {
  group: CharacterAssetGroup
  search: string
  sortField: SortField
  sortDirection: SortDirection
  defaultExpanded?: boolean
  onAssetSelect?: (asset: ValuedAsset, characterName: string) => void
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  // Filter assets by search
  const filteredAssets = useMemo(() => {
    if (!search) return group.assets
    const searchLower = search.toLowerCase()
    return group.assets.filter(
      (a) =>
        a.type_name.toLowerCase().includes(searchLower) ||
        a.group_name.toLowerCase().includes(searchLower) ||
        a.location_name.toLowerCase().includes(searchLower)
    )
  }, [group.assets, search])

  // Sort filtered assets
  const sortedAssets = useMemo(() => {
    return [...filteredAssets].sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1
      switch (sortField) {
        case 'value':
          return (a.total_value - b.total_value) * dir
        case 'quantity':
          return (a.quantity - b.quantity) * dir
        case 'volume':
          return (a.total_volume - b.total_volume) * dir
        case 'name':
        default:
          return a.type_name.localeCompare(b.type_name) * dir
      }
    })
  }, [filteredAssets, sortField, sortDirection])

  if (sortedAssets.length === 0) return null

  return (
    <Card className="overflow-hidden">
      <button className="w-full text-left" onClick={() => setIsExpanded(!isExpanded)}>
        <CardHeader className="pb-3 cursor-pointer hover:bg-secondary/30 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isExpanded ? (
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              )}
              <Avatar className="h-8 w-8">
                <AvatarImage src={group.portrait_url} alt={group.character_name} />
                <AvatarFallback>{group.character_name.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <CardTitle className="text-base font-medium">{group.character_name}</CardTitle>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-sm font-semibold text-primary">
                  {formatISK(group.total_value)} ISK
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatVolume(group.total_volume)}
                </div>
              </div>
              <Badge variant="secondary" className="text-xs">
                {sortedAssets.length} types
              </Badge>
            </div>
          </div>
        </CardHeader>
      </button>

      {isExpanded && (
        <CardContent className="pt-0">
          <div className="border-t border-border pt-3">
            <div className="space-y-1">
              {sortedAssets.slice(0, 50).map((asset) => (
                <AssetItem key={asset.item_id} asset={asset} onSelect={(a) => onAssetSelect?.(a, group.character_name)} />
              ))}
              {sortedAssets.length > 50 && (
                <div className="text-sm text-muted-foreground text-center py-2">
                  +{sortedAssets.length - 50} more items...
                </div>
              )}
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
function AssetItem({ asset, onSelect }: { asset: ValuedAsset; onSelect?: (asset: ValuedAsset) => void }) {
  return (
    <button
      onClick={() => onSelect?.(asset)}
      className="w-full flex items-center gap-3 py-2 px-2 rounded-md hover:bg-secondary/30 transition-colors text-left"
    >
      <div className="flex-shrink-0">
        <img
          src={getItemIconUrl(asset.type_id, 32)}
          alt={asset.type_name}
          className="w-8 h-8 rounded"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />
      </div>

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
          <MapPin className="h-3 w-3" />
          <span className="truncate">{asset.location_name}</span>
        </div>
      </div>

      <div className="flex-shrink-0 text-right">
        <span className="font-mono text-sm">x{formatNumber(asset.quantity)}</span>
        <div className="text-xs text-primary font-medium">{formatISK(asset.total_value)} ISK</div>
      </div>
    </button>
  )
}

/**
 * Single asset item display with character name
 */
function AssetItemWithCharacter({
  asset,
  onSelect,
}: {
  asset: ValuedAsset & { character_name: string }
  onSelect?: (asset: ValuedAsset, characterName: string) => void
}) {
  return (
    <button
      onClick={() => onSelect?.(asset, asset.character_name)}
      className="w-full flex items-center gap-3 py-2 px-2 rounded-md hover:bg-secondary/30 transition-colors text-left"
    >
      <div className="flex-shrink-0">
        <img
          src={getItemIconUrl(asset.type_id, 32)}
          alt={asset.type_name}
          className="w-8 h-8 rounded"
          loading="lazy"
          onError={(e) => { e.currentTarget.style.display = 'none' }}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{asset.type_name}</span>
          {asset.is_singleton && (
            <Badge variant="outline" className="text-xs py-0">Single</Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Users className="h-3 w-3" />
          <span className="truncate">{asset.character_name}</span>
        </div>
      </div>
      <div className="flex-shrink-0 text-right">
        <span className="font-mono text-sm">x{formatNumber(asset.quantity)}</span>
        <div className="text-xs text-primary font-medium">{formatISK(asset.total_value)} ISK</div>
      </div>
    </button>
  )
}

interface LocationAssetGroup {
  location_id: number
  location_name: string
  location_type: string
  assets: Array<ValuedAsset & { character_name: string; character_id: number }>
  total_items: number
  total_value: number
  total_volume: number
}

/**
 * Location group component with collapsible content
 */
function LocationGroup({
  group,
  search,
  sortField,
  sortDirection,
  defaultExpanded = false,
  onAssetSelect,
}: {
  group: LocationAssetGroup
  search: string
  sortField: SortField
  sortDirection: SortDirection
  defaultExpanded?: boolean
  onAssetSelect?: (asset: ValuedAsset, characterName: string) => void
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  const filteredAssets = useMemo(() => {
    if (!search) return group.assets
    const searchLower = search.toLowerCase()
    return group.assets.filter(
      (a) =>
        a.type_name.toLowerCase().includes(searchLower) ||
        a.group_name.toLowerCase().includes(searchLower) ||
        a.character_name.toLowerCase().includes(searchLower)
    )
  }, [group.assets, search])

  // Sort filtered assets
  const sortedAssets = useMemo(() => {
    return [...filteredAssets].sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1
      switch (sortField) {
        case 'value':
          return (a.total_value - b.total_value) * dir
        case 'quantity':
          return (a.quantity - b.quantity) * dir
        case 'volume':
          return (a.total_volume - b.total_volume) * dir
        case 'name':
        default:
          return a.type_name.localeCompare(b.type_name) * dir
      }
    })
  }, [filteredAssets, sortField, sortDirection])

  if (sortedAssets.length === 0) return null

  const locationTypeLabel = group.location_type === 'station' ? 'Station'
    : group.location_type === 'item' ? 'Ship/Container' : 'Other'

  return (
    <Card className="overflow-hidden">
      <button className="w-full text-left" onClick={() => setIsExpanded(!isExpanded)}>
        <CardHeader className="pb-3 cursor-pointer hover:bg-secondary/30 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isExpanded ? (
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              )}
              <MapPin className="h-5 w-5 text-primary" />
              <div>
                <CardTitle className="text-base font-medium">{group.location_name}</CardTitle>
                <span className="text-xs text-muted-foreground">{locationTypeLabel}</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-sm font-semibold text-primary">
                  {formatISK(group.total_value)} ISK
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatVolume(group.total_volume)}
                </div>
              </div>
              <Badge variant="secondary" className="text-xs">
                {sortedAssets.length} types
              </Badge>
            </div>
          </div>
        </CardHeader>
      </button>

      {isExpanded && (
        <CardContent className="pt-0">
          <div className="border-t border-border pt-3">
            <div className="space-y-1">
              {sortedAssets.slice(0, 50).map((asset) => (
                <AssetItemWithCharacter key={`${asset.character_id}-${asset.item_id}`} asset={asset} onSelect={onAssetSelect} />
              ))}
              {sortedAssets.length > 50 && (
                <div className="text-sm text-muted-foreground text-center py-2">
                  +{sortedAssets.length - 50} more items...
                </div>
              )}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

/**
 * Hook to fetch valued assets for all characters using useQueries (proper hook pattern)
 */
function useAllCharacterAssets(characters: Character[]) {
  const queries = useQueries({
    queries: characters.map((char) => ({
      queryKey: ['character', char.character_id, 'assets', 'valued'],
      queryFn: () => charactersApi.getValuedAssets(char.character_id),
      staleTime: 5 * 60 * 1000, // 5 minutes
      enabled: char.character_id > 0,
    })),
  })

  const isLoading = queries.some((q) => q.isLoading)
  const isError = queries.some((q) => q.isError)

  const groups: CharacterAssetGroup[] = useMemo(() => {
    return queries
      .map((q, index) => ({
        query: q,
        character: characters[index],
      }))
      .filter((item) => item.query.data?.assets && item.query.data.assets.length > 0)
      .map((item) => ({
        character_id: item.character.character_id,
        character_name: item.character.character_name,
        portrait_url: `https://images.evetech.net/characters/${item.character.character_id}/portrait?size=64`,
        assets: item.query.data!.assets,
        total_items: item.query.data!.total_items,
        total_value: item.query.data!.total_value,
        total_volume: item.query.data!.total_volume,
        location_summaries: item.query.data!.location_summaries,
      }))
  }, [queries, characters])

  // Calculate grand totals across all characters
  const totals = useMemo(() => {
    return groups.reduce(
      (acc, group) => ({
        totalValue: acc.totalValue + group.total_value,
        totalVolume: acc.totalVolume + group.total_volume,
      }),
      { totalValue: 0, totalVolume: 0 }
    )
  }, [groups])

  return { groups, totals, isLoading, isError }
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
              <div className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-5 w-32" />
              </div>
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
              : 'No assets found across any characters.'}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Main Assets page component - shows assets from ALL characters
 */
export function Assets() {
  const { data: charactersData, isLoading: isLoadingChars } = useCharacters()
  const characters = charactersData?.characters ?? []
  const { groups, totals, isLoading: isLoadingAssets } = useAllCharacterAssets(characters)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [locationTypeFilter, setLocationTypeFilter] = useState<string | null>(null)
  type ViewMode = 'character' | 'location'
  const [viewMode, setViewMode] = useState<ViewMode>('character')
  const [selectedAsset, setSelectedAsset] = useState<ValuedAsset | null>(null)
  const [selectedCharacterName, setSelectedCharacterName] = useState<string | undefined>()

  // Sort state
  const [sortField, setSortField] = useState<SortField>('value')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const isLoading = isLoadingChars || isLoadingAssets

  // Get all unique categories across all characters
  const categories = useMemo(() => {
    const allCategories = new Set<string>()
    for (const group of groups) {
      for (const asset of group.assets) {
        if (asset.category_name && asset.category_name !== 'Unknown') {
          allCategories.add(asset.category_name)
        }
      }
    }
    return Array.from(allCategories).sort()
  }, [groups])

  // Get all unique location types across all characters
  const locationTypes = useMemo(() => {
    const types = new Map<string, string>([
      ['station', 'Stations'],
      ['item', 'Ships & Containers'],
      ['other', 'Other'],
    ])
    const found = new Set<string>()
    for (const group of groups) {
      for (const asset of group.assets) {
        if (asset.location_type) {
          found.add(asset.location_type)
        }
      }
    }
    return Array.from(found).map(t => ({ value: t, label: types.get(t) || t }))
  }, [groups])

  // Filter groups by category and location type
  const filteredGroups = useMemo(() => {
    let result = groups

    // Category filter
    if (categoryFilter) {
      result = result
        .map((g) => {
          const filteredAssets = g.assets.filter((a) => a.category_name === categoryFilter)
          return {
            ...g,
            assets: filteredAssets,
            total_items: filteredAssets.reduce((sum, a) => sum + a.quantity, 0),
            total_value: filteredAssets.reduce((sum, a) => sum + a.total_value, 0),
            total_volume: filteredAssets.reduce((sum, a) => sum + a.total_volume, 0),
          }
        })
        .filter((g) => g.assets.length > 0)
    }

    // Location type filter
    if (locationTypeFilter) {
      result = result
        .map((g) => {
          const filteredAssets = g.assets.filter((a) => a.location_type === locationTypeFilter)
          return {
            ...g,
            assets: filteredAssets,
            total_items: filteredAssets.reduce((sum, a) => sum + a.quantity, 0),
            total_value: filteredAssets.reduce((sum, a) => sum + a.total_value, 0),
            total_volume: filteredAssets.reduce((sum, a) => sum + a.total_volume, 0),
          }
        })
        .filter((g) => g.assets.length > 0)
    }

    // Sort assets within each group based on sortField and sortDirection
    result = result.map((g) => ({
      ...g,
      assets: [...g.assets].sort((a, b) => {
        let comparison = 0
        switch (sortField) {
          case 'name':
            comparison = a.type_name.localeCompare(b.type_name)
            break
          case 'value':
            comparison = a.total_value - b.total_value
            break
          case 'quantity':
            comparison = a.quantity - b.quantity
            break
          case 'volume':
            comparison = a.total_volume - b.total_volume
            break
        }
        return sortDirection === 'asc' ? comparison : -comparison
      }),
    }))

    return result
  }, [groups, categoryFilter, locationTypeFilter, sortField, sortDirection])

  // Group assets by location (for location view mode)
  const locationGroups = useMemo((): LocationAssetGroup[] => {
    const locationMap = new Map<number, LocationAssetGroup>()

    for (const charGroup of filteredGroups) {
      for (const asset of charGroup.assets) {
        const existing = locationMap.get(asset.location_id)
        const enrichedAsset = {
          ...asset,
          character_name: charGroup.character_name,
          character_id: charGroup.character_id,
        }

        if (existing) {
          existing.assets.push(enrichedAsset)
          existing.total_items += asset.quantity
          existing.total_value += asset.total_value
          existing.total_volume += asset.total_volume
        } else {
          locationMap.set(asset.location_id, {
            location_id: asset.location_id,
            location_name: asset.location_name,
            location_type: asset.location_type || 'other',
            assets: [enrichedAsset],
            total_items: asset.quantity,
            total_value: asset.total_value,
            total_volume: asset.total_volume,
          })
        }
      }
    }

    return Array.from(locationMap.values()).sort((a, b) =>
      a.location_name.localeCompare(b.location_name)
    )
  }, [filteredGroups])

  // Calculate totals
  const totalCharacters = filteredGroups.length
  const totalTypes = filteredGroups.reduce((sum, g) => sum + g.assets.length, 0)
  const totalItems = filteredGroups.reduce((sum, g) => sum + g.total_items, 0)
  const hasFilters = !!search || !!categoryFilter || !!locationTypeFilter

  if (isLoading) {
    return (
      <div>
        <Header title="Assets" subtitle="All Characters" />
        <div className="p-6">
          <AssetsSkeleton />
        </div>
      </div>
    )
  }

  return (
    <div>
      <Header title="Assets" subtitle="All Characters" />

      <div className="p-6 space-y-4">
        {/* Search and Filter Bar */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by item name, group, or location..."
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

          {/* Location Type Filter */}
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <select
              value={locationTypeFilter ?? ''}
              onChange={(e) => setLocationTypeFilter(e.target.value || null)}
              className={cn(
                'pl-10 pr-8 py-2 rounded-md appearance-none cursor-pointer min-w-[180px]',
                'bg-secondary/50 border border-border',
                'text-foreground',
                'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'transition-colors'
              )}
            >
              <option value="">All Locations</option>
              {locationTypes.map((lt) => (
                <option key={lt.value} value={lt.value}>
                  {lt.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>

          {/* View Mode Toggle */}
          <div className="flex rounded-md border border-border overflow-hidden">
            <button
              onClick={() => setViewMode('character')}
              className={cn(
                'px-3 py-2 text-sm flex items-center gap-2 transition-colors',
                viewMode === 'character'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary/50 text-muted-foreground hover:text-foreground'
              )}
            >
              <Users className="h-4 w-4" />
              By Character
            </button>
            <button
              onClick={() => setViewMode('location')}
              className={cn(
                'px-3 py-2 text-sm flex items-center gap-2 transition-colors',
                viewMode === 'location'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary/50 text-muted-foreground hover:text-foreground'
              )}
            >
              <LayoutGrid className="h-4 w-4" />
              By Location
            </button>
          </div>

          {/* Sort Dropdown */}
          <div className="relative">
            <select
              value={`${sortField}-${sortDirection}`}
              onChange={(e) => {
                const [field, dir] = e.target.value.split('-') as [SortField, SortDirection]
                setSortField(field)
                setSortDirection(dir)
              }}
              className={cn(
                'pl-3 pr-8 py-2 rounded-md appearance-none cursor-pointer min-w-[160px]',
                'bg-secondary/50 border border-border',
                'text-foreground',
                'focus:outline-none focus:ring-2 focus:ring-primary'
              )}
            >
              <option value="value-desc">Highest Value</option>
              <option value="value-asc">Lowest Value</option>
              <option value="quantity-desc">Most Items</option>
              <option value="quantity-asc">Fewest Items</option>
              <option value="name-asc">Name A-Z</option>
              <option value="name-desc">Name Z-A</option>
              <option value="volume-desc">Largest Volume</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>
        </div>

        {/* Grand Total Banner */}
        <div className="bg-gradient-to-r from-primary/20 to-primary/5 border border-primary/30 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-muted-foreground">Total Asset Value</div>
              <div className="text-3xl font-bold text-primary">
                {formatISK(totals.totalValue)} ISK
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-muted-foreground">Total Volume</div>
              <div className="text-xl font-semibold">{formatVolume(totals.totalVolume)}</div>
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          {viewMode === 'character' ? (
            <span>
              <Users className="inline h-4 w-4 mr-1" />
              <strong className="text-foreground">{totalCharacters}</strong>{' '}
              {totalCharacters === 1 ? 'character' : 'characters'}
            </span>
          ) : (
            <span>
              <MapPin className="inline h-4 w-4 mr-1" />
              <strong className="text-foreground">{locationGroups.length}</strong>{' '}
              {locationGroups.length === 1 ? 'location' : 'locations'}
            </span>
          )}
          <span className="text-border">|</span>
          <span>
            <strong className="text-foreground">{formatNumber(totalTypes)}</strong> item types
          </span>
          <span className="text-border">|</span>
          <span>
            <strong className="text-foreground">{formatNumber(totalItems)}</strong> total items
          </span>
          {hasFilters && (
            <>
              <span className="text-border">|</span>
              <button
                onClick={() => {
                  setSearch('')
                  setCategoryFilter(null)
                  setLocationTypeFilter(null)
                }}
                className="text-primary hover:underline"
              >
                Clear filters
              </button>
            </>
          )}
        </div>

        {/* Asset Groups */}
        {viewMode === 'character' ? (
          filteredGroups.length === 0 ? (
            <EmptyState hasFilters={hasFilters} />
          ) : (
            <div className="space-y-3">
              {filteredGroups.map((group, index) => (
                <CharacterGroup
                  key={group.character_id}
                  group={group}
                  search={search}
                  sortField={sortField}
                  sortDirection={sortDirection}
                  defaultExpanded={index === 0}
                  onAssetSelect={(asset, charName) => {
                    setSelectedAsset(asset)
                    setSelectedCharacterName(charName)
                  }}
                />
              ))}
            </div>
          )
        ) : (
          locationGroups.length === 0 ? (
            <EmptyState hasFilters={hasFilters} />
          ) : (
            <div className="space-y-3">
              {locationGroups.map((group, index) => (
                <LocationGroup
                  key={group.location_id}
                  group={group}
                  search={search}
                  sortField={sortField}
                  sortDirection={sortDirection}
                  defaultExpanded={index === 0}
                  onAssetSelect={(asset, charName) => {
                    setSelectedAsset(asset)
                    setSelectedCharacterName(charName)
                  }}
                />
              ))}
            </div>
          )
        )}

        <AssetDetailModal
          asset={selectedAsset}
          characterName={selectedCharacterName}
          open={!!selectedAsset}
          onOpenChange={(open) => {
            if (!open) {
              setSelectedAsset(null)
              setSelectedCharacterName(undefined)
            }
          }}
        />
      </div>
    </div>
  )
}
