import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { apiClient } from '@/api/client'
import {
  TrendingUp,
  TrendingDown,
  Factory,
  Rocket,
  Gem,
  Zap,
  Filter,
  ChevronRight,
} from 'lucide-react'

interface ManufacturingOpportunity {
  product_id: number
  blueprint_id: number
  product_name: string
  category: string
  group_name: string
  difficulty: number
  material_cost: number
  sell_price: number
  profit: number
  roi: number
  volume_available: number
}

interface OpportunitiesResponse {
  results: ManufacturingOpportunity[]
}

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
 * Get difficulty badge color
 */
function getDifficultyColor(difficulty: number): string {
  switch (difficulty) {
    case 0:
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 1:
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    case 2:
      return 'bg-red-500/20 text-red-400 border-red-500/30'
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }
}

/**
 * Get difficulty label
 */
function getDifficultyLabel(difficulty: number): string {
  switch (difficulty) {
    case 0:
      return 'Easy'
    case 1:
      return 'Medium'
    case 2:
      return 'Hard'
    default:
      return 'Unknown'
  }
}

/**
 * Get category icon
 */
function getCategoryIcon(category: string) {
  switch (category.toLowerCase()) {
    case 'ship':
      return Rocket
    case 'module':
      return Zap
    case 'structure':
      return Factory
    default:
      return Gem
  }
}

/**
 * Opportunity card component
 */
function OpportunityCard({
  opportunity,
  onClick,
}: {
  opportunity: ManufacturingOpportunity
  onClick: () => void
}) {
  const isProfitable = opportunity.profit > 0
  const CategoryIcon = getCategoryIcon(opportunity.category)

  return (
    <Card
      className="cursor-pointer hover:bg-secondary/30 transition-colors"
      onClick={onClick}
    >
      <CardContent className="pt-4">
        <div className="flex items-start gap-4">
          <img
            src={getItemIconUrl(opportunity.product_id, 64)}
            alt={opportunity.product_name}
            className="w-12 h-12 rounded-lg border border-border"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium truncate">{opportunity.product_name}</h3>
              <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs">
                <CategoryIcon className="h-3 w-3 mr-1" />
                {opportunity.group_name}
              </Badge>
              <Badge
                variant="outline"
                className={cn('text-xs', getDifficultyColor(opportunity.difficulty))}
              >
                {getDifficultyLabel(opportunity.difficulty)}
              </Badge>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-4">
          <div>
            <div className="text-xs text-muted-foreground">Material Cost</div>
            <div className="text-sm font-mono">{formatISK(opportunity.material_cost)}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Sell Price</div>
            <div className="text-sm font-mono">{formatISK(opportunity.sell_price)}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Profit</div>
            <div
              className={cn(
                'text-sm font-mono font-medium',
                isProfitable ? 'text-green-400' : 'text-red-400'
              )}
            >
              {formatISK(opportunity.profit)}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
          <div className="flex items-center gap-2">
            {isProfitable ? (
              <TrendingUp className="h-4 w-4 text-green-400" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-400" />
            )}
            <span
              className={cn(
                'text-sm font-medium',
                isProfitable ? 'text-green-400' : 'text-red-400'
              )}
            >
              {opportunity.roi.toFixed(1)}% ROI
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Filter buttons
 */
const CATEGORIES = ['All', 'Ship', 'Module', 'Structure', 'Ammunition']

const SORT_OPTIONS = [
  { value: 'profit', label: 'Profit' },
  { value: 'roi', label: 'ROI %' },
  { value: 'material_cost', label: 'Investment' },
]

/**
 * Main Manufacturing Opportunities page
 */
export function ManufacturingOpportunities() {
  const navigate = useNavigate()
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [sortBy, setSortBy] = useState<'profit' | 'roi' | 'material_cost'>('profit')
  const [showOnlyEasy, setShowOnlyEasy] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['manufacturing-opportunities'],
    queryFn: async () => {
      const response = await apiClient.get<OpportunitiesResponse>('/hunter/opportunities')
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Filter and sort opportunities
  const filteredOpportunities = data?.results
    .filter((opp) => {
      if (selectedCategory !== 'All' && opp.category !== selectedCategory) {
        return false
      }
      if (showOnlyEasy && opp.difficulty > 0) {
        return false
      }
      return opp.profit > 0 // Only show profitable items
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'roi':
          return b.roi - a.roi
        case 'material_cost':
          return a.material_cost - b.material_cost // Lower investment first
        default:
          return b.profit - a.profit
      }
    })

  // Calculate summary stats
  const stats = {
    totalItems: filteredOpportunities?.length ?? 0,
    avgRoi:
      filteredOpportunities && filteredOpportunities.length > 0
        ? filteredOpportunities.reduce((sum, o) => sum + o.roi, 0) / filteredOpportunities.length
        : 0,
    totalPotentialProfit:
      filteredOpportunities?.reduce((sum, o) => sum + o.profit, 0) ?? 0,
  }

  const handleItemClick = (opportunity: ManufacturingOpportunity) => {
    // Navigate to blueprint browser with pre-selected item
    navigate(`/blueprints?typeId=${opportunity.product_id}`)
  }

  return (
    <div>
      <Header
        title="Manufacturing Opportunities"
        subtitle="Find profitable items to manufacture"
      />

      <div className="p-6 space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Factory className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{stats.totalItems}</div>
                  <div className="text-xs text-muted-foreground">Profitable Items</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/20">
                  <TrendingUp className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{stats.avgRoi.toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">Average ROI</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/20">
                  <Gem className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">
                    {formatISK(stats.totalPotentialProfit)}
                  </div>
                  <div className="text-xs text-muted-foreground">Total Potential</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-4">
              {/* Category Filter */}
              <div className="flex gap-1">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={cn(
                      'px-3 py-1.5 text-sm rounded-lg transition-colors',
                      selectedCategory === cat
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary/50 hover:bg-secondary text-foreground'
                    )}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <div className="h-6 w-px bg-border" />

              {/* Sort Options */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Sort by:</span>
                {SORT_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setSortBy(option.value as typeof sortBy)}
                    className={cn(
                      'px-3 py-1.5 text-sm rounded-lg transition-colors',
                      sortBy === option.value
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary/50 hover:bg-secondary text-foreground'
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <div className="h-6 w-px bg-border" />

              {/* Easy Only Toggle */}
              <button
                onClick={() => setShowOnlyEasy(!showOnlyEasy)}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-lg transition-colors',
                  showOnlyEasy
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                    : 'bg-secondary/50 hover:bg-secondary text-foreground'
                )}
              >
                Easy Only
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Opportunities Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Card key={i}>
                <CardContent className="pt-4">
                  <Skeleton className="h-12 w-12 rounded-lg mb-4" />
                  <Skeleton className="h-5 w-3/4 mb-2" />
                  <Skeleton className="h-4 w-1/2 mb-4" />
                  <div className="grid grid-cols-3 gap-3">
                    <Skeleton className="h-10" />
                    <Skeleton className="h-10" />
                    <Skeleton className="h-10" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : isError ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Factory className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Failed to Load Opportunities</h3>
              <p className="text-muted-foreground">
                Could not fetch manufacturing opportunities. Please try again later.
              </p>
            </CardContent>
          </Card>
        ) : filteredOpportunities && filteredOpportunities.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredOpportunities.map((opp) => (
              <OpportunityCard
                key={opp.product_id}
                opportunity={opp}
                onClick={() => handleItemClick(opp)}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Factory className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No Opportunities Found</h3>
              <p className="text-muted-foreground">
                Try adjusting your filters to see more opportunities.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
