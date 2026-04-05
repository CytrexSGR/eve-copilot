import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { piApi, type MakeOrBuyResult, type PIOpportunity, type PISchematic, type PISchematicInput } from '@/api/pi'
import { cn } from '@/lib/utils'
import {
  Search,
  TrendingUp,
  TrendingDown,
  Package,
  ArrowLeft,
  ArrowRight,
  ShoppingCart,
  Factory,
  Calculator,
  Loader2,
} from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Tier colors and labels
 */
const TIER_CONFIG: Record<number, { label: string; color: string; bg: string }> = {
  0: { label: 'P0', color: 'text-gray-400', bg: 'bg-gray-500/20' },
  1: { label: 'P1', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  2: { label: 'P2', color: 'text-green-400', bg: 'bg-green-500/20' },
  3: { label: 'P3', color: 'text-purple-400', bg: 'bg-purple-500/20' },
  4: { label: 'P4', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
}

/**
 * Format ISK value
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
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Search result item
 */
function SearchResultItem({
  schematic,
  onSelect,
}: {
  schematic: PISchematic
  onSelect: (typeId: number) => void
}) {
  const tierConfig = TIER_CONFIG[schematic.tier] || TIER_CONFIG[1]

  return (
    <button
      onClick={() => onSelect(schematic.output_type_id)}
      className="w-full flex items-center gap-3 p-2 hover:bg-secondary/50 rounded-lg transition-colors text-left"
    >
      <img
        src={getItemIconUrl(schematic.output_type_id, 32)}
        alt={schematic.output_name}
        className="w-8 h-8 rounded border border-border"
        onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
          e.currentTarget.style.display = 'none'
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{schematic.output_name}</div>
      </div>
      <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
        {tierConfig.label}
      </Badge>
    </button>
  )
}

/**
 * Analysis Result Card
 */
function AnalysisResultCard({
  result,
  showP0Cost,
  onToggleP0,
  isLoadingP0,
}: {
  result: MakeOrBuyResult
  showP0Cost: boolean
  onToggleP0: () => void
  isLoadingP0: boolean
}) {
  const tierConfig = TIER_CONFIG[result.tier] || TIER_CONFIG[1]
  const isMake = result.recommendation === 'MAKE'

  return (
    <Card className={cn('border-2', isMake ? 'border-green-500/30' : 'border-orange-500/30')}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <img
              src={getItemIconUrl(result.type_id, 64)}
              alt={result.type_name}
              className="w-12 h-12 rounded-lg border border-border"
              onError={(e) => {
                e.currentTarget.style.display = 'none'
              }}
            />
            <div>
              <CardTitle className="flex items-center gap-2">
                {result.type_name}
                <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
                  {tierConfig.label}
                </Badge>
              </CardTitle>
              <div className="text-sm text-muted-foreground">
                Quantity: {result.quantity}
              </div>
            </div>
          </div>

          <Badge
            className={cn(
              'text-lg px-4 py-2',
              isMake
                ? 'bg-green-500/20 text-green-400 border-green-500/30'
                : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
            )}
          >
            {isMake ? <Factory className="h-5 w-5 mr-2" /> : <ShoppingCart className="h-5 w-5 mr-2" />}
            {result.recommendation}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Price Comparison */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <ShoppingCart className="h-3 w-3" />
              Market Price
            </div>
            <div className="text-lg font-mono font-medium">{formatISK(result.market_price)}</div>
          </div>

          <div className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <Factory className="h-3 w-3" />
              Production Cost
            </div>
            <div className="text-lg font-mono font-medium">{formatISK(result.make_cost)}</div>
          </div>

          <div className={cn('p-3 rounded-lg', isMake ? 'bg-green-500/10' : 'bg-orange-500/10')}>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              {isMake ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              You Save
            </div>
            <div
              className={cn(
                'text-lg font-mono font-medium',
                isMake ? 'text-green-400' : 'text-orange-400'
              )}
            >
              {formatISK(result.savings_isk)} ({result.savings_percent.toFixed(1)}%)
            </div>
          </div>
        </div>

        {/* Inputs Table */}
        <div>
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <Package className="h-4 w-4" />
            Required Inputs
          </div>
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-secondary/30">
                <tr>
                  <th className="text-left p-2 font-medium">Material</th>
                  <th className="text-right p-2 font-medium">Qty</th>
                  <th className="text-right p-2 font-medium">Unit Price</th>
                  <th className="text-right p-2 font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                {result.inputs.map((input: PISchematicInput) => {
                  const avgUnitPrice = result.make_cost / result.inputs.reduce((sum: number, i: PISchematicInput) => sum + i.quantity, 0)
                  const inputTotal = avgUnitPrice * input.quantity
                  return (
                    <tr key={input.type_id} className="border-t border-border">
                      <td className="p-2 flex items-center gap-2">
                        <img
                          src={getItemIconUrl(input.type_id, 32)}
                          alt={input.type_name}
                          className="w-6 h-6 rounded"
                          onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                            e.currentTarget.style.display = 'none'
                          }}
                        />
                        {input.type_name}
                      </td>
                      <td className="p-2 text-right font-mono">{input.quantity}</td>
                      <td className="p-2 text-right font-mono text-muted-foreground">
                        ~{formatISK(avgUnitPrice)}
                      </td>
                      <td className="p-2 text-right font-mono">
                        {formatISK(inputTotal)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* P0 Cost Toggle */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/20 border border-border">
          <div className="flex items-center gap-3">
            <Checkbox
              id="p0-cost"
              checked={showP0Cost}
              onCheckedChange={onToggleP0}
              disabled={isLoadingP0}
            />
            <label htmlFor="p0-cost" className="text-sm cursor-pointer">
              Show P0 Raw Material Cost (Vertical Integration)
            </label>
          </div>
          {isLoadingP0 ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : result.p0_cost !== null ? (
            <div className="text-sm font-mono">
              P0 Total: <span className="text-blue-400">{formatISK(result.p0_cost)}</span>
            </div>
          ) : null}
        </div>

        {/* Action Links */}
        <div className="flex justify-end">
          <Link to={`/pi/chain/${result.type_id}`}>
            <Button variant="outline" className="gap-2">
              View Production Chain
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Opportunity row for top MAKE products
 */
function OpportunityRow({
  opportunity,
  onAnalyze,
}: {
  opportunity: PIOpportunity
  onAnalyze: (typeId: number) => void
}) {
  const tierConfig = TIER_CONFIG[opportunity.tier] || TIER_CONFIG[1]

  return (
    <div className="flex items-center gap-4 p-3 hover:bg-secondary/30 rounded-lg transition-colors">
      <img
        src={getItemIconUrl(opportunity.type_id, 32)}
        alt={opportunity.type_name}
        className="w-8 h-8 rounded border border-border"
        onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
          e.currentTarget.style.display = 'none'
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{opportunity.type_name}</div>
      </div>
      <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
        {tierConfig.label}
      </Badge>
      <div className="text-sm font-mono text-green-400 w-20 text-right">
        {opportunity.roi_percent.toFixed(1)}%
      </div>
      <Button size="sm" variant="secondary" onClick={() => onAnalyze(opportunity.type_id)}>
        Analyze
      </Button>
    </div>
  )
}

/**
 * Main Make or Buy page
 */
export function PIMakeOrBuy() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypeId, setSelectedTypeId] = useState<number | null>(
    searchParams.get('product') ? parseInt(searchParams.get('product')!) : null
  )
  const [quantity, setQuantity] = useState(10)
  const [showP0Cost, setShowP0Cost] = useState(false)
  const [showSearchResults, setShowSearchResults] = useState(false)

  // Search schematics
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['pi', 'search', searchQuery],
    queryFn: () => piApi.searchSchematics(searchQuery),
    enabled: searchQuery.length >= 2,
    staleTime: 5 * 60 * 1000,
  })

  // Analyze selected product
  const {
    data: analysisResult,
    isLoading: isAnalyzing,
    refetch: refetchAnalysis,
  } = useQuery({
    queryKey: ['pi', 'make-or-buy', selectedTypeId, quantity, showP0Cost],
    queryFn: () =>
      piApi.analyzeMakeOrBuy(selectedTypeId!, quantity, 10000002, showP0Cost),
    enabled: selectedTypeId !== null,
    staleTime: 5 * 60 * 1000,
  })

  // Load top opportunities
  const { data: opportunities, isLoading: isLoadingOpportunities } = useQuery({
    queryKey: ['pi', 'opportunities', 'all'],
    queryFn: () => piApi.getOpportunities(undefined, 50),
    staleTime: 10 * 60 * 1000,
  })

  // Filter to MAKE-worthy opportunities (high ROI)
  const topMakeOpportunities = useMemo(() => {
    if (!opportunities) return []
    return opportunities
      .filter((o) => o.roi_percent > 20)
      .sort((a, b) => b.roi_percent - a.roi_percent)
      .slice(0, 10)
  }, [opportunities])

  // Handle product selection
  const handleSelectProduct = (typeId: number) => {
    setSelectedTypeId(typeId)
    setSearchQuery('')
    setShowSearchResults(false)
    setSearchParams({ product: typeId.toString() })
  }

  // Handle quantity change with debounce
  useEffect(() => {
    if (selectedTypeId) {
      const timer = setTimeout(() => {
        refetchAnalysis()
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [quantity])

  return (
    <div>
      <Header title="Make or Buy Analysis" subtitle="Decide whether to buy or produce PI products" />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/pi"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to PI Overview
        </Link>

        {/* Search Section */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Calculator className="h-4 w-4" />
              Analyze PI Product
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              {/* Search Input */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search PI product..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setShowSearchResults(true)
                  }}
                  onFocus={() => setShowSearchResults(true)}
                  className="pl-10"
                />

                {/* Search Results Dropdown */}
                {showSearchResults && searchQuery.length >= 2 && (
                  <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-background border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto">
                    {isSearching ? (
                      <div className="p-4 text-center text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin mx-auto mb-2" />
                        Searching...
                      </div>
                    ) : searchResults && searchResults.length > 0 ? (
                      <div className="p-1">
                        {searchResults.map((schematic) => (
                          <SearchResultItem
                            key={schematic.schematic_id}
                            schematic={schematic}
                            onSelect={handleSelectProduct}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="p-4 text-center text-muted-foreground">
                        No PI products found
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Quantity Input */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground whitespace-nowrap">Quantity:</span>
                <Input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-24"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Analysis Result */}
        {isAnalyzing ? (
          <Card>
            <CardContent className="py-12">
              <div className="flex flex-col items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
                <div className="text-muted-foreground">Analyzing...</div>
              </div>
            </CardContent>
          </Card>
        ) : analysisResult ? (
          <AnalysisResultCard
            result={analysisResult}
            showP0Cost={showP0Cost}
            onToggleP0={() => setShowP0Cost(!showP0Cost)}
            isLoadingP0={isAnalyzing && showP0Cost}
          />
        ) : selectedTypeId ? (
          <Card>
            <CardContent className="py-12 text-center">
              <div className="text-muted-foreground">
                Unable to analyze this product. It may not be a valid PI product.
              </div>
            </CardContent>
          </Card>
        ) : null}

        {/* Top MAKE Opportunities */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-400" />
              Top MAKE Opportunities
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingOpportunities ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : topMakeOpportunities.length > 0 ? (
              <div className="space-y-1">
                {topMakeOpportunities.map((opp) => (
                  <OpportunityRow
                    key={opp.type_id}
                    opportunity={opp}
                    onAnalyze={handleSelectProduct}
                  />
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-muted-foreground">
                No high-ROI products found
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Click outside to close search */}
      {showSearchResults && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowSearchResults(false)}
        />
      )}
    </div>
  )
}
