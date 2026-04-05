import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { apiClient } from '@/api/client'
import { piApi } from '@/api/pi'
import { cn } from '@/lib/utils'
import {
  ArrowLeft,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Factory,
  Package,
  Search,
  ShoppingCart,
} from 'lucide-react'

/**
 * Chain node from API
 */
interface ChainNode {
  type_id: number
  type_name: string
  tier: number
  quantity_needed: number
  schematic_id: number | null
  children: ChainNode[]
}

/**
 * Tier colors
 */
const TIER_CONFIG: Record<number, { label: string; color: string; bg: string; border: string }> = {
  0: { label: 'P0', color: 'text-gray-400', bg: 'bg-gray-500/20', border: 'border-gray-500/50' },
  1: { label: 'P1', color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/50' },
  2: { label: 'P2', color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/50' },
  3: { label: 'P3', color: 'text-purple-400', bg: 'bg-purple-500/20', border: 'border-purple-500/50' },
  4: { label: 'P4', color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/50' },
}

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Format number
 */
function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toLocaleString()
}

/**
 * Chain node component (recursive)
 */
function ChainNodeComponent({
  node,
  depth = 0,
}: {
  node: ChainNode
  depth?: number
}) {
  const [isExpanded, setIsExpanded] = useState(depth < 2) // Auto-expand first 2 levels
  const hasChildren = node.children && node.children.length > 0
  const tierConfig = TIER_CONFIG[node.tier] || TIER_CONFIG[0]

  return (
    <div className={cn('relative', depth > 0 && 'ml-6')}>
      {/* Connector line */}
      {depth > 0 && (
        <div className="absolute left-[-20px] top-0 bottom-0 w-px bg-border" />
      )}
      {depth > 0 && (
        <div className="absolute left-[-20px] top-5 w-5 h-px bg-border" />
      )}

      {/* Node */}
      <div
        className={cn(
          'flex items-center gap-3 p-3 rounded-lg border transition-colors mb-2',
          tierConfig.border,
          tierConfig.bg
        )}
      >
        {/* Expand/Collapse button */}
        {hasChildren ? (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 rounded hover:bg-black/20 transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        ) : (
          <div className="w-6" />
        )}

        {/* Icon */}
        <img
          src={getItemIconUrl(node.type_id, 32)}
          alt={node.type_name}
          className="w-8 h-8 rounded border border-border"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{node.type_name}</span>
            <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
              {tierConfig.label}
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground">
            Quantity: {formatNumber(node.quantity_needed)}
          </div>
        </div>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="relative">
          {node.children.map((child) => (
            <ChainNodeComponent
              key={child.type_id}
              node={child}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Flatten chain to get all P0 materials
 */
function getP0Materials(node: ChainNode): Array<{ type_id: number; type_name: string; quantity: number }> {
  if (node.tier === 0) {
    return [{ type_id: node.type_id, type_name: node.type_name, quantity: node.quantity_needed }]
  }

  const materials: Array<{ type_id: number; type_name: string; quantity: number }> = []
  for (const child of node.children || []) {
    const childMats = getP0Materials(child)
    for (const mat of childMats) {
      const existing = materials.find((m) => m.type_id === mat.type_id)
      if (existing) {
        existing.quantity += mat.quantity
      } else {
        materials.push({ ...mat })
      }
    }
  }
  return materials
}

/**
 * Search and select component
 */
function ProductSearch({ onSelect }: { onSelect: (typeId: number) => void }) {
  const [query, setQuery] = useState('')

  const { data: results } = useQuery({
    queryKey: ['pi', 'search', query],
    queryFn: async () => {
      const response = await apiClient.get('/pi/formulas/search', {
        params: { q: query },
      })
      return response.data as Array<{ schematic_id: number; schematic_name: string; output_type_id: number; tier: number }>
    },
    enabled: query.length >= 2,
    staleTime: 60 * 1000,
  })

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search PI products..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className={cn(
            'w-full pl-10 pr-4 py-2 rounded-lg',
            'bg-secondary/50 border border-border',
            'text-foreground placeholder:text-muted-foreground',
            'focus:outline-none focus:ring-2 focus:ring-primary'
          )}
        />
      </div>

      {results && results.length > 0 && query.length >= 2 && (
        <div className="absolute z-10 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {results.map((item) => {
            const tierConfig = TIER_CONFIG[item.tier] || TIER_CONFIG[1]
            return (
              <button
                key={item.schematic_id}
                onClick={() => {
                  onSelect(item.output_type_id)
                  setQuery('')
                }}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-secondary/50 transition-colors text-left"
              >
                <img
                  src={getItemIconUrl(item.output_type_id, 32)}
                  alt={item.schematic_name}
                  className="w-6 h-6 rounded"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                  }}
                />
                <span className="flex-1 truncate">{item.schematic_name}</span>
                <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
                  P{item.tier}
                </Badge>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

/**
 * Make or Buy Summary Card
 */
function MakeOrBuySummary({
  typeId,
}: {
  typeId: number
}) {
  const { data: result, isLoading } = useQuery({
    queryKey: ['pi', 'make-or-buy', typeId],
    queryFn: () => piApi.analyzeMakeOrBuy(typeId, 1),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <Card className="border-border">
        <CardContent className="py-4">
          <Skeleton className="h-8 w-48" />
        </CardContent>
      </Card>
    )
  }

  if (!result) return null

  const isMake = result.recommendation === 'MAKE'

  return (
    <Card className={cn('border-2', isMake ? 'border-green-500/30 bg-green-500/5' : 'border-orange-500/30 bg-orange-500/5')}>
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Badge
              className={cn(
                'text-sm px-3 py-1',
                isMake
                  ? 'bg-green-500/20 text-green-400 border-green-500/30'
                  : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
              )}
            >
              {isMake ? <Factory className="h-4 w-4 mr-1" /> : <ShoppingCart className="h-4 w-4 mr-1" />}
              {result.recommendation}
            </Badge>
            <span className="text-sm">
              {isMake ? (
                <>You save <span className="text-green-400 font-medium">{result.savings_percent.toFixed(1)}%</span> by producing</>
              ) : (
                <>You save <span className="text-orange-400 font-medium">{result.savings_percent.toFixed(1)}%</span> by buying</>
              )}
            </span>
          </div>
          <Link
            to={`/pi/make-or-buy?product=${typeId}`}
            className="flex items-center gap-1 text-sm text-primary hover:underline"
          >
            Full Analysis
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Main PI Production Chain page
 */
export function PIProductionChain() {
  const { typeId } = useParams<{ typeId: string }>()
  const navigate = useNavigate()

  const { data: chainData, isLoading, isError } = useQuery({
    queryKey: ['pi', 'chain', typeId],
    queryFn: async () => {
      const response = await apiClient.get(`/pi/chain/${typeId}`)
      return response.data as ChainNode
    },
    enabled: !!typeId,
    staleTime: 10 * 60 * 1000,
  })

  // Calculate P0 materials
  const p0Materials = chainData ? getP0Materials(chainData) : []

  const handleProductSelect = (newTypeId: number) => {
    navigate(`/pi/chain/${newTypeId}`)
  }

  return (
    <div>
      <Header
        title="Production Chain"
        subtitle={chainData?.type_name || 'Select a product'}
      />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/pi/profitability"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Profitability
        </Link>

        {/* Search */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Search Product</CardTitle>
          </CardHeader>
          <CardContent>
            <ProductSearch onSelect={handleProductSelect} />
          </CardContent>
        </Card>

        {!typeId ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Factory className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Select a Product</h3>
              <p className="text-muted-foreground">
                Search for a PI product to view its production chain.
              </p>
            </CardContent>
          </Card>
        ) : isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : isError || !chainData ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Chain Not Found</h3>
              <p className="text-muted-foreground">
                Could not load the production chain for this item.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Make or Buy Summary */}
            <MakeOrBuySummary typeId={parseInt(typeId!)} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Production Chain Tree */}
              <div className="lg:col-span-2">
                <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Factory className="h-5 w-5" />
                    Production Chain
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ChainNodeComponent node={chainData} />
                </CardContent>
              </Card>
            </div>

            {/* P0 Materials Summary */}
            <div>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Package className="h-5 w-5 text-gray-400" />
                    Raw Materials (P0)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {p0Materials.map((mat) => (
                      <div
                        key={mat.type_id}
                        className="flex items-center gap-3 p-2 rounded-lg bg-gray-500/10 border border-gray-500/30"
                      >
                        <img
                          src={getItemIconUrl(mat.type_id, 32)}
                          alt={mat.type_name}
                          className="w-8 h-8 rounded"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none'
                          }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm truncate">{mat.type_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {formatNumber(mat.quantity)} units
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {p0Materials.length === 0 && (
                    <div className="py-4 text-center text-muted-foreground text-sm">
                      No raw materials
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
