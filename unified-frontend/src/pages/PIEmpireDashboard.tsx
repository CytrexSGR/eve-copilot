import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { PIAlertsPanel } from '@/components/pi/PIAlertsPanel'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, type P4EmpireProfitability } from '@/api/pi'
import { cn } from '@/lib/utils'
import {
  ArrowLeft,
  TrendingUp,
  Coins,
  Globe2,
  Package,
  Star,
  ArrowUpDown,
  ChevronUp,
  ChevronDown,
} from 'lucide-react'

/**
 * Format ISK value with B/M/K suffixes
 */
function formatISK(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toFixed(0)
}

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 64): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Get recommendation badge color
 */
function getRecommendationStyle(recommendation: P4EmpireProfitability['recommendation']) {
  switch (recommendation) {
    case 'excellent':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    case 'good':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 'fair':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    case 'poor':
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }
}

/**
 * Get complexity stars
 */
function ComplexityStars({ complexity }: { complexity: P4EmpireProfitability['complexity'] }) {
  const starCount = complexity === 'low' ? 1 : complexity === 'medium' ? 2 : 3
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3].map((i) => (
        <Star
          key={i}
          className={cn(
            'h-3 w-3',
            i <= starCount ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'
          )}
        />
      ))}
    </div>
  )
}

/**
 * Logistics score bar
 */
function LogisticsBar({ score }: { score: number }) {
  const percentage = (score / 10) * 100
  const color =
    score >= 7 ? 'bg-green-500' : score >= 4 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-xs text-muted-foreground w-4">{score}</span>
    </div>
  )
}

/**
 * Slider component for configuration
 */
function ConfigSlider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  suffix = '',
  displayValue,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (value: number) => void
  suffix?: string
  displayValue?: string
}) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {displayValue ?? value}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-secondary rounded-full appearance-none cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:h-4
          [&::-webkit-slider-thumb]:w-4
          [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:bg-primary
          [&::-webkit-slider-thumb]:cursor-pointer
          [&::-webkit-slider-thumb]:border-2
          [&::-webkit-slider-thumb]:border-primary-foreground
          [&::-moz-range-thumb]:h-4
          [&::-moz-range-thumb]:w-4
          [&::-moz-range-thumb]:rounded-full
          [&::-moz-range-thumb]:bg-primary
          [&::-moz-range-thumb]:cursor-pointer
          [&::-moz-range-thumb]:border-2
          [&::-moz-range-thumb]:border-primary-foreground"
      />
    </div>
  )
}

type SortField = 'monthly_profit' | 'profit_per_planet' | 'logistics_score' | 'complexity' | 'recommendation'
type SortDirection = 'asc' | 'desc'

/**
 * Product row component
 */
function ProductRow({
  product,
  onClick,
}: {
  product: P4EmpireProfitability
  onClick: () => void
}) {
  return (
    <tr
      onClick={onClick}
      className="border-b border-border hover:bg-secondary/30 cursor-pointer transition-colors"
    >
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <img
            src={getItemIconUrl(product.type_id)}
            alt={product.type_name}
            className="w-10 h-10 rounded-lg border border-border"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
          <div>
            <div className="font-medium">{product.type_name}</div>
            <Badge
              variant="outline"
              className={cn('text-xs mt-1', getRecommendationStyle(product.recommendation))}
            >
              {product.recommendation.charAt(0).toUpperCase() + product.recommendation.slice(1)}
            </Badge>
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-right">
        <div className="font-mono text-green-400">{formatISK(product.monthly_profit)}</div>
        <div className="text-xs text-muted-foreground">per month</div>
      </td>
      <td className="py-3 px-4 text-right">
        <div className="font-mono">{formatISK(product.profit_per_planet)}</div>
        <div className="text-xs text-muted-foreground">per planet</div>
      </td>
      <td className="py-3 px-4">
        <ComplexityStars complexity={product.complexity} />
      </td>
      <td className="py-3 px-4">
        <LogisticsBar score={product.logistics_score} />
      </td>
    </tr>
  )
}

/**
 * Sortable table header
 */
function SortableHeader({
  label,
  field,
  currentField,
  direction,
  onSort,
  align = 'left',
}: {
  label: string
  field: SortField
  currentField: SortField
  direction: SortDirection
  onSort: (field: SortField) => void
  align?: 'left' | 'right'
}) {
  const isActive = currentField === field
  return (
    <th
      onClick={() => onSort(field)}
      className={cn(
        'py-3 px-4 font-medium text-muted-foreground cursor-pointer hover:text-foreground transition-colors',
        align === 'right' && 'text-right'
      )}
    >
      <div className={cn('flex items-center gap-1', align === 'right' && 'justify-end')}>
        {label}
        {isActive ? (
          direction === 'desc' ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          )
        ) : (
          <ArrowUpDown className="h-4 w-4 opacity-30" />
        )}
      </div>
    </th>
  )
}

/**
 * Loading skeleton
 */
function EmpireSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="pt-4">
              <Skeleton className="h-5 w-24 mb-2" />
              <Skeleton className="h-8 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="pt-4">
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <Skeleton className="h-5 flex-1" />
                <Skeleton className="h-5 w-20" />
                <Skeleton className="h-5 w-20" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Main PI Empire Dashboard page
 */
function PIEmpireDashboard() {
  const navigate = useNavigate()

  // Configuration state
  const [totalPlanets, setTotalPlanets] = useState(18)
  const [extractionPlanets, setExtractionPlanets] = useState(12)
  const [pocoTax, setPocoTax] = useState(10)

  // Sorting state
  const [sortField, setSortField] = useState<SortField>('monthly_profit')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  // Calculate factory planets from total and extraction
  const factoryPlanets = totalPlanets - extractionPlanets

  // Fetch empire profitability data
  const { data, isLoading, error } = useQuery({
    queryKey: ['empire-profitability', totalPlanets, extractionPlanets, pocoTax],
    queryFn: () =>
      piApi.getEmpireProfitability({
        total_planets: totalPlanets,
        extraction_planets: extractionPlanets,
        factory_planets: factoryPlanets,
        poco_tax: pocoTax / 100, // Convert percentage to decimal
      }),
    staleTime: 5 * 60 * 1000,
  })

  // Sort products
  const sortedProducts = useMemo(() => {
    if (!data?.products) return []

    const complexityOrder = { low: 1, medium: 2, high: 3 }
    const recommendationOrder = { excellent: 4, good: 3, fair: 2, poor: 1 }

    return [...data.products].sort((a, b) => {
      let comparison = 0

      switch (sortField) {
        case 'monthly_profit':
          comparison = a.monthly_profit - b.monthly_profit
          break
        case 'profit_per_planet':
          comparison = a.profit_per_planet - b.profit_per_planet
          break
        case 'logistics_score':
          comparison = a.logistics_score - b.logistics_score
          break
        case 'complexity':
          comparison = complexityOrder[a.complexity] - complexityOrder[b.complexity]
          break
        case 'recommendation':
          comparison = recommendationOrder[a.recommendation] - recommendationOrder[b.recommendation]
          break
      }

      return sortDirection === 'desc' ? -comparison : comparison
    })
  }, [data?.products, sortField, sortDirection])

  // Handle sort
  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  // Handle extraction slider - ensure factory planets stay non-negative
  const handleExtractionChange = (value: number) => {
    // Ensure extraction doesn't exceed total planets
    const newExtraction = Math.min(value, totalPlanets)
    setExtractionPlanets(newExtraction)
  }

  // Handle total planets change - adjust extraction if needed
  const handleTotalPlanetsChange = (value: number) => {
    setTotalPlanets(value)
    // Adjust extraction if it exceeds new total
    if (extractionPlanets > value) {
      setExtractionPlanets(value)
    }
  }

  // Get comparison data
  const comparison = data?.comparison || {}

  return (
    <div>
      <Header title="PI Empire Dashboard" subtitle="P4 production analysis across multiple characters" />

      <div className="p-6 space-y-6">
        {/* Navigation */}
        <div className="flex items-center justify-between">
          <Link
            to="/pi"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to PI Overview
          </Link>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/pi/empire/overview')}
              className="flex items-center gap-2 px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg transition-colors"
            >
              Multi-Character Overview
            </button>
            <button
              onClick={() => navigate('/pi/planets/finder')}
              className="flex items-center gap-2 px-4 py-2 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded-lg transition-colors"
            >
              Find Planets
            </button>
            <button
              onClick={() => navigate('/pi/empire/plans')}
              className="flex items-center gap-2 px-4 py-2 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded-lg transition-colors"
            >
              View Empire Plans
            </button>
          </div>
        </div>

        {/* Configuration Panel */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Empire Configuration</CardTitle>
            <CardDescription>
              Configure your PI empire parameters to see profitability analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ConfigSlider
                label="Total Planets"
                value={totalPlanets}
                min={6}
                max={36}
                step={6}
                onChange={handleTotalPlanetsChange}
                displayValue={`${totalPlanets} (${Math.ceil(totalPlanets / 6)} chars)`}
              />
              <ConfigSlider
                label="Extraction / Factory Split"
                value={extractionPlanets}
                min={0}
                max={totalPlanets}
                step={1}
                onChange={handleExtractionChange}
                displayValue={`${extractionPlanets} / ${factoryPlanets}`}
              />
              <ConfigSlider
                label="POCO Tax Rate"
                value={pocoTax}
                min={0}
                max={50}
                step={1}
                onChange={setPocoTax}
                suffix="%"
              />
            </div>
          </CardContent>
        </Card>

        {isLoading ? (
          <EmpireSkeleton />
        ) : error ? (
          <Card>
            <CardContent className="py-12 text-center">
              <div className="text-red-400 mb-2">Failed to load empire data</div>
              <div className="text-sm text-muted-foreground">
                {error instanceof Error ? error.message : 'Unknown error'}
              </div>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Comparison Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-green-500/20">
                      <Coins className="h-5 w-5 text-green-400" />
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Best Profit</div>
                      <div className="text-lg font-bold">
                        {comparison.best_profit?.name || 'N/A'}
                      </div>
                      {comparison.best_profit && (
                        <div className="text-sm text-green-400">
                          {formatISK(comparison.best_profit.monthly)}/mo
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-500/20">
                      <Package className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Best Passive</div>
                      <div className="text-lg font-bold">
                        {comparison.best_passive?.name || 'N/A'}
                      </div>
                      {comparison.best_passive && (
                        <div className="text-sm text-blue-400">
                          Logistics: {comparison.best_passive.logistics_score}/10
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-purple-500/20">
                      <TrendingUp className="h-5 w-5 text-purple-400" />
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Best Balanced</div>
                      <div className="text-lg font-bold">
                        {comparison.best_balanced?.name || 'N/A'}
                      </div>
                      {comparison.best_balanced && (
                        <div className="text-sm text-purple-400">
                          Score: {comparison.best_balanced.score}/10
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Alerts Panel */}
            <PIAlertsPanel limit={10} />

            {/* Products Table */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">P4 Products</CardTitle>
                    <CardDescription>
                      {sortedProducts.length} products analyzed for your empire configuration
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Globe2 className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      {totalPlanets} planets total
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {sortedProducts.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="py-3 px-4 text-left font-medium text-muted-foreground">
                            Product
                          </th>
                          <SortableHeader
                            label="Monthly Profit"
                            field="monthly_profit"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                            align="right"
                          />
                          <SortableHeader
                            label="Per Planet"
                            field="profit_per_planet"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                            align="right"
                          />
                          <SortableHeader
                            label="Complexity"
                            field="complexity"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                          />
                          <SortableHeader
                            label="Logistics"
                            field="logistics_score"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                          />
                        </tr>
                      </thead>
                      <tbody>
                        {sortedProducts.map((product) => (
                          <ProductRow
                            key={product.type_id}
                            product={product}
                            onClick={() => {
                              // Navigate to chain view
                              navigate(`/pi/chain/${product.type_id}`)
                            }}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="py-12 text-center">
                    <Globe2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-medium mb-2">No Products Found</h3>
                    <p className="text-muted-foreground">
                      No P4 products available for analysis.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}

export default PIEmpireDashboard
export { PIEmpireDashboard }
