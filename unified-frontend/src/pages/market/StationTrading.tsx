// unified-frontend/src/pages/market/StationTrading.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import {
  TrendingUp,
  BarChart3,
  Coins,
  Users,
  Search,
  Sparkles,
} from 'lucide-react'
import type { TradingOpportunity } from '@/types/market'

const REGIONS = [
  { id: 10000002, name: 'The Forge (Jita)' },
  { id: 10000043, name: 'Domain (Amarr)' },
  { id: 10000030, name: 'Heimatar (Rens)' },
  { id: 10000032, name: 'Sinq Laison (Dodixie)' },
  { id: 10000042, name: 'Metropolis (Hek)' },
]

/**
 * Get recommendation badge style
 */
function getRecommendationStyle(rec: string) {
  switch (rec) {
    case 'excellent':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 'good':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    case 'moderate':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    case 'risky':
      return 'bg-red-500/20 text-red-400 border-red-500/30'
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }
}

/**
 * Opportunity card component
 */
function OpportunityCard({ opp }: { opp: TradingOpportunity }) {
  return (
    <Card className="hover:border-primary/50 transition-all">
      <CardContent className="py-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="font-medium text-lg">{opp.type_name}</div>
            <div className="text-sm text-muted-foreground">{opp.reason}</div>
          </div>
          <Badge variant="outline" className={cn('text-xs', getRecommendationStyle(opp.recommendation))}>
            {opp.recommendation.toUpperCase()}
          </Badge>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-muted-foreground text-xs">Margin</div>
            <div className={cn(
              'font-bold',
              opp.margin_percent >= 15 ? 'text-green-400' :
              opp.margin_percent >= 10 ? 'text-blue-400' : 'text-yellow-400'
            )}>
              {opp.margin_percent.toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-muted-foreground text-xs">Profit/Unit</div>
            <div className="font-mono text-green-400">{formatISK(opp.profit_per_unit)}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-xs">Daily Potential</div>
            <div className="font-mono">{formatISK(opp.daily_potential)}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-xs">Capital</div>
            <div className="font-mono">{formatISK(opp.capital_required)}</div>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground">
              Buy: <span className="text-foreground font-mono">{formatISK(opp.best_buy)}</span>
            </span>
            <span className="text-muted-foreground">
              Sell: <span className="text-foreground font-mono">{formatISK(opp.best_sell)}</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className={cn(
              opp.competition.update_frequency === 'high' ? 'text-red-400' :
              opp.competition.update_frequency === 'medium' ? 'text-yellow-400' : 'text-green-400'
            )}>
              <Users className="h-3 w-3 inline mr-1" />
              {opp.competition.buy_orders + opp.competition.sell_orders} orders
            </span>
            <span className="text-muted-foreground">
              <BarChart3 className="h-3 w-3 inline mr-1" />
              ~{opp.daily_volume}/day
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Main Station Trading page
 */
export function StationTrading() {
  const [regionId, setRegionId] = useState(10000002)
  const [minMargin, setMinMargin] = useState(5)
  const [minVolume, setMinVolume] = useState(100)
  const [minProfit, setMinProfit] = useState(1000000)
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['trading-opportunities', regionId, minMargin, minVolume, minProfit],
    queryFn: () => marketApi.getTradingOpportunities(regionId, {
      minMarginPercent: minMargin,
      minDailyVolume: minVolume,
      minProfitPerTrade: minProfit,
      limit: 100,
    }),
    refetchInterval: 10 * 60 * 1000,
  })

  const opportunities = data?.opportunities ?? []

  // Filter by search
  const filteredOpps = opportunities.filter(o =>
    o.type_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Stats
  const excellentCount = opportunities.filter(o => o.recommendation === 'excellent').length
  const goodCount = opportunities.filter(o => o.recommendation === 'good').length
  const totalDailyPotential = opportunities.reduce((sum, o) => sum + o.daily_potential, 0)

  return (
    <div className="p-6 space-y-6">
      <Header
        title="Station Trading"
        subtitle={data?.region_name ?? 'Loading...'}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
      />

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Region</div>
              <Select value={String(regionId)} onValueChange={v => setRegionId(Number(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REGIONS.map(r => (
                    <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Min Margin %</div>
              <Input
                type="number"
                value={minMargin}
                onChange={e => setMinMargin(Number(e.target.value))}
                min={0}
                max={100}
              />
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Min Volume/Day</div>
              <Input
                type="number"
                value={minVolume}
                onChange={e => setMinVolume(Number(e.target.value))}
                min={0}
              />
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Min Profit/Unit</div>
              <Input
                type="number"
                value={minProfit}
                onChange={e => setMinProfit(Number(e.target.value))}
                min={0}
              />
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Search</div>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Filter items..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-green-400" />
              <div>
                <div className="text-xs text-muted-foreground">Excellent</div>
                <div className="text-xl font-bold text-green-400">{excellentCount}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-400" />
              <div>
                <div className="text-xs text-muted-foreground">Good</div>
                <div className="text-xl font-bold text-blue-400">{goodCount}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <Coins className="h-5 w-5 text-yellow-400" />
              <div>
                <div className="text-xs text-muted-foreground">Daily Potential</div>
                <div className="text-lg font-bold">{formatISK(totalDailyPotential)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-purple-400" />
              <div>
                <div className="text-xs text-muted-foreground">Opportunities</div>
                <div className="text-xl font-bold">{filteredOpps.length}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Opportunities List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-32" />)}
        </div>
      ) : filteredOpps.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No opportunities found matching your criteria</p>
            <p className="text-sm mt-2">Try adjusting filters or selecting a different region</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredOpps.map(opp => (
            <OpportunityCard key={opp.type_id} opp={opp} />
          ))}
        </div>
      )}
    </div>
  )
}

export default StationTrading
