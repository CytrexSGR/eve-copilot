import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, type PIOpportunity } from '@/api/pi'
import { cn } from '@/lib/utils'
import {
  TrendingUp,
  Filter,
  ChevronRight,
  Coins,
  Clock,
  Percent,
  ArrowLeft,
} from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Tier colors and labels
 */
const TIER_CONFIG: Record<number, { label: string; color: string; bg: string }> = {
  0: { label: 'P0 (Raw)', color: 'text-gray-400', bg: 'bg-gray-500/20' },
  1: { label: 'P1 (Basic)', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  2: { label: 'P2 (Refined)', color: 'text-green-400', bg: 'bg-green-500/20' },
  3: { label: 'P3 (Specialized)', color: 'text-purple-400', bg: 'bg-purple-500/20' },
  4: { label: 'P4 (Advanced)', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
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
 * Opportunity card
 */
function OpportunityCard({
  opportunity,
  onClick,
}: {
  opportunity: PIOpportunity
  onClick: () => void
}) {
  const tierConfig = TIER_CONFIG[opportunity.tier] || TIER_CONFIG[1]
  const isProfitable = opportunity.profit_per_hour > 0

  return (
    <Card
      className="cursor-pointer hover:bg-secondary/30 transition-colors"
      onClick={onClick}
    >
      <CardContent className="pt-4">
        <div className="flex items-start gap-3">
          <img
            src={getItemIconUrl(opportunity.type_id, 64)}
            alt={opportunity.type_name}
            className="w-12 h-12 rounded-lg border border-border"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">{opportunity.type_name}</span>
              <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </div>
            <Badge className={cn('text-xs mt-1', tierConfig.bg, tierConfig.color)}>
              {tierConfig.label}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-4">
          <div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Coins className="h-3 w-3" />
              Input Cost
            </div>
            <div className="text-sm font-mono">{formatISK(opportunity.input_cost)}</div>
          </div>

          <div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3" />
              Output Value
            </div>
            <div className="text-sm font-mono">{formatISK(opportunity.output_value)}</div>
          </div>

          <div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              Profit/h
            </div>
            <div
              className={cn(
                'text-sm font-mono font-medium',
                isProfitable ? 'text-green-400' : 'text-red-400'
              )}
            >
              {formatISK(opportunity.profit_per_hour)}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
          <div className="flex items-center gap-2">
            <Percent className="h-4 w-4 text-muted-foreground" />
            <span
              className={cn(
                'text-sm font-medium',
                isProfitable ? 'text-green-400' : 'text-red-400'
              )}
            >
              {opportunity.roi_percent.toFixed(1)}% ROI
            </span>
          </div>
          <div className="text-xs text-muted-foreground">
            Cycle: {opportunity.cycle_time / 60}min
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Main PI Profitability page
 */
export function PIProfitability() {
  const navigate = useNavigate()
  const [selectedTier, setSelectedTier] = useState<number | null>(null)
  const [sortBy, setSortBy] = useState<'profit' | 'roi'>('profit')

  // Fetch all opportunities
  const { data: allOpportunities, isLoading } = useQuery({
    queryKey: ['pi', 'opportunities', 'all'],
    queryFn: () => piApi.getOpportunities(undefined, 100),
    staleTime: 10 * 60 * 1000,
  })

  // Filter and sort
  const filteredOpportunities = useMemo(() => {
    if (!allOpportunities) return []

    let filtered = allOpportunities.filter((o) => o.profit_per_hour > 0)

    if (selectedTier !== null) {
      filtered = filtered.filter((o) => o.tier === selectedTier)
    }

    return filtered.sort((a, b) => {
      if (sortBy === 'roi') return b.roi_percent - a.roi_percent
      return b.profit_per_hour - a.profit_per_hour
    })
  }, [allOpportunities, selectedTier, sortBy])

  // Calculate stats
  const stats = useMemo(() => {
    if (!filteredOpportunities.length) return { count: 0, avgRoi: 0, topProfit: 0 }
    return {
      count: filteredOpportunities.length,
      avgRoi:
        filteredOpportunities.reduce((sum, o) => sum + o.roi_percent, 0) /
        filteredOpportunities.length,
      topProfit: Math.max(...filteredOpportunities.map((o) => o.profit_per_hour)),
    }
  }, [filteredOpportunities])

  // Count by tier
  const tierCounts = useMemo(() => {
    if (!allOpportunities) return {}
    const counts: Record<number, number> = {}
    allOpportunities
      .filter((o) => o.profit_per_hour > 0)
      .forEach((o) => {
        counts[o.tier] = (counts[o.tier] || 0) + 1
      })
    return counts
  }, [allOpportunities])

  const handleItemClick = (opportunity: PIOpportunity) => {
    navigate(`/pi/chain/${opportunity.type_id}`)
  }

  return (
    <div>
      <Header title="PI Profitability" subtitle="Find profitable planetary products" />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/pi"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to PI Overview
        </Link>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/20">
                  <TrendingUp className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{stats.count}</div>
                  <div className="text-xs text-muted-foreground">Profitable Products</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Percent className="h-5 w-5 text-blue-400" />
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
                <div className="p-2 rounded-lg bg-yellow-500/20">
                  <Coins className="h-5 w-5 text-yellow-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{formatISK(stats.topProfit)}</div>
                  <div className="text-xs text-muted-foreground">Top Profit/h</div>
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
              {/* Tier Filter */}
              <div className="flex gap-1">
                <button
                  onClick={() => setSelectedTier(null)}
                  className={cn(
                    'px-3 py-1.5 text-sm rounded-lg transition-colors',
                    selectedTier === null
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary/50 hover:bg-secondary text-foreground'
                  )}
                >
                  All ({Object.values(tierCounts).reduce((a, b) => a + b, 0)})
                </button>
                {[1, 2, 3, 4].map((tier) => {
                  const count = tierCounts[tier] || 0
                  return (
                    <button
                      key={tier}
                      onClick={() => setSelectedTier(tier)}
                      disabled={count === 0}
                      className={cn(
                        'px-3 py-1.5 text-sm rounded-lg transition-colors',
                        selectedTier === tier
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary/50 hover:bg-secondary text-foreground',
                        count === 0 && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      P{tier} ({count})
                    </button>
                  )
                })}
              </div>

              <div className="h-6 w-px bg-border" />

              {/* Sort Options */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Sort by:</span>
                <button
                  onClick={() => setSortBy('profit')}
                  className={cn(
                    'px-3 py-1.5 text-sm rounded-lg transition-colors',
                    sortBy === 'profit'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary/50 hover:bg-secondary text-foreground'
                  )}
                >
                  Profit/h
                </button>
                <button
                  onClick={() => setSortBy('roi')}
                  className={cn(
                    'px-3 py-1.5 text-sm rounded-lg transition-colors',
                    sortBy === 'roi'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary/50 hover:bg-secondary text-foreground'
                  )}
                >
                  ROI %
                </button>
              </div>
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
        ) : filteredOpportunities.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredOpportunities.map((opp) => (
              <OpportunityCard
                key={opp.type_id}
                opportunity={opp}
                onClick={() => handleItemClick(opp)}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No Profitable Products</h3>
              <p className="text-muted-foreground">
                No profitable PI products found for the selected filters.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
