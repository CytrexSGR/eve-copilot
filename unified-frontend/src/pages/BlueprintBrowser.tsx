import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { productionApi, type ItemSearchResult, type ProductionCostResponse } from '@/api/production'
import {
  Search,
  Package,
  Coins,
  TrendingUp,
  TrendingDown,
  Loader2,
  ChevronRight,
  Factory,
  Info,
} from 'lucide-react'

/**
 * Get EVE Online item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Format ISK value
 */
function formatISK(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B`
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  return value.toFixed(0)
}

/**
 * Format number with commas
 */
function formatNumber(value: number): string {
  return value.toLocaleString()
}

/**
 * Debounce hook
 */
function useDebounce<T extends (...args: string[]) => void>(
  callback: T,
  delay: number
): T {
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null)

  return useCallback(
    ((...args: Parameters<T>) => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      const id = setTimeout(() => {
        callback(...args)
      }, delay)
      setTimeoutId(id)
    }) as T,
    [callback, delay, timeoutId]
  )
}

/**
 * Search result item
 */
function SearchResultItem({
  item,
  isSelected,
  onSelect,
}: {
  item: ItemSearchResult
  isSelected: boolean
  onSelect: (item: ItemSearchResult) => void
}) {
  return (
    <button
      onClick={() => onSelect(item)}
      className={cn(
        'w-full flex items-center gap-3 p-3 rounded-lg transition-colors text-left',
        isSelected
          ? 'bg-primary/20 border border-primary/50'
          : 'hover:bg-secondary/50 border border-transparent'
      )}
    >
      <img
        src={getItemIconUrl(item.typeID, 32)}
        alt={item.typeName}
        className="w-8 h-8 rounded"
        loading="lazy"
        onError={(e) => {
          e.currentTarget.style.display = 'none'
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{item.typeName}</div>
        <div className="text-xs text-muted-foreground">
          Type ID: {item.typeID}
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </button>
  )
}

/**
 * Material row in production cost view
 */
function MaterialRow({ material }: { material: ProductionCostResponse['materials'][0] }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-border last:border-0">
      <img
        src={getItemIconUrl(material.type_id, 32)}
        alt={material.name}
        className="w-8 h-8 rounded"
        loading="lazy"
        onError={(e) => {
          e.currentTarget.style.display = 'none'
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{material.name}</div>
        <div className="text-xs text-muted-foreground">
          {formatNumber(material.adjusted_quantity)} units @ {formatISK(material.unit_price)} ISK
        </div>
      </div>
      <div className="text-right">
        <div className="font-mono text-sm">{formatISK(material.total_cost)}</div>
        <div className="text-xs text-muted-foreground">ISK</div>
      </div>
    </div>
  )
}

/**
 * Production cost detail panel
 */
function ProductionCostPanel({
  typeId,
  meLevel,
  onMEChange,
}: {
  typeId: number
  meLevel: number
  onMEChange: (me: number) => void
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['production-cost', typeId, meLevel],
    queryFn: () => productionApi.getProductionCost(typeId, meLevel),
    enabled: typeId > 0,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Info className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-muted-foreground">
            No blueprint found for this item
          </p>
        </CardContent>
      </Card>
    )
  }

  const profitAnalysis = data.profit_analysis
  const isProfitable = profitAnalysis?.profitable ?? false

  return (
    <div className="space-y-4">
      {/* Item Header */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-start gap-4">
            <img
              src={getItemIconUrl(data.item.type_id, 64)}
              alt={data.item.name}
              className="w-16 h-16 rounded-lg border border-border"
            />
            <div className="flex-1">
              <h2 className="text-xl font-bold">{data.item.name}</h2>
              <p className="text-sm text-muted-foreground">{data.blueprint.name}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="secondary">Output: {data.item.output_quantity}</Badge>
                <Badge variant="outline">Type ID: {data.item.type_id}</Badge>
                {data.summary.build_time_formatted && (
                  <Badge variant="outline">Build: {data.summary.build_time_formatted}</Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ME Level Selector */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Material Efficiency</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-1">
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((me) => (
              <button
                key={me}
                onClick={() => onMEChange(me)}
                className={cn(
                  'flex-1 py-2 text-sm rounded transition-colors',
                  meLevel === me
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary/50 hover:bg-secondary'
                )}
              >
                {me}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Profit Summary */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Coins className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Material Cost</span>
            </div>
            <div className="text-xl font-bold mt-1">
              {formatISK(data.summary.total_material_cost)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Package className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Sell Price</span>
            </div>
            <div className="text-xl font-bold mt-1">
              {profitAnalysis ? formatISK(profitAnalysis.current_sell_price) : 'N/A'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              {isProfitable ? (
                <TrendingUp className="h-4 w-4 text-green-400" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-400" />
              )}
              <span className="text-xs text-muted-foreground">Profit</span>
            </div>
            <div className={cn('text-xl font-bold mt-1', isProfitable ? 'text-green-400' : 'text-red-400')}>
              {profitAnalysis ? formatISK(profitAnalysis.profit) : 'N/A'}
            </div>
            {profitAnalysis && (
              <div className="text-xs text-muted-foreground">
                {profitAnalysis.profit_margin_percent.toFixed(1)}% margin
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Materials List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Factory className="h-4 w-4" />
            Required Materials ({data.materials.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            {data.materials.map((mat) => (
              <MaterialRow key={mat.type_id} material={mat} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Main Blueprint Browser page
 */
export function BlueprintBrowser() {
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedItem, setSelectedItem] = useState<ItemSearchResult | null>(null)
  const [meLevel, setMELevel] = useState(10)

  const debouncedSetQuery = useDebounce((query: string) => {
    setDebouncedQuery(query)
  }, 300)

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchQuery(value)
    debouncedSetQuery(value)
  }

  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['items-search', debouncedQuery],
    queryFn: () => productionApi.searchItems(debouncedQuery, 20),
    enabled: debouncedQuery.length >= 2,
    staleTime: 60 * 1000,
  })

  const handleSelectItem = (item: ItemSearchResult) => {
    setSelectedItem(item)
  }

  return (
    <div>
      <Header title="Blueprint Browser" subtitle="Search items & calculate production costs" />

      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Search Panel */}
          <div className="lg:col-span-1 space-y-4">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search items (e.g., Badger, Raven)..."
                value={searchQuery}
                onChange={handleSearchChange}
                className={cn(
                  'w-full pl-10 pr-4 py-3 rounded-lg',
                  'bg-secondary/50 border border-border',
                  'text-foreground placeholder:text-muted-foreground',
                  'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                  'transition-colors'
                )}
              />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground animate-spin" />
              )}
            </div>

            {/* Search Results */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">
                  {searchResults?.results.length
                    ? `${searchResults.results.length} results`
                    : 'Search Results'}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-2">
                {!debouncedQuery && (
                  <div className="py-8 text-center text-muted-foreground text-sm">
                    Enter at least 2 characters to search
                  </div>
                )}

                {debouncedQuery && !searchResults?.results.length && !isSearching && (
                  <div className="py-8 text-center text-muted-foreground text-sm">
                    No items found for "{debouncedQuery}"
                  </div>
                )}

                {searchResults?.results && (
                  <div className="space-y-1 max-h-[60vh] overflow-y-auto">
                    {searchResults.results
                      .filter((item) => !item.typeName.includes('Blueprint'))
                      .map((item) => (
                        <SearchResultItem
                          key={item.typeID}
                          item={item}
                          isSelected={selectedItem?.typeID === item.typeID}
                          onSelect={handleSelectItem}
                        />
                      ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-2">
            {!selectedItem ? (
              <Card>
                <CardContent className="py-16 text-center">
                  <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">Select an Item</h3>
                  <p className="text-muted-foreground max-w-sm mx-auto">
                    Search for an item and select it to view production costs and required materials.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <ProductionCostPanel
                typeId={selectedItem.typeID}
                meLevel={meLevel}
                onMEChange={setMELevel}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
