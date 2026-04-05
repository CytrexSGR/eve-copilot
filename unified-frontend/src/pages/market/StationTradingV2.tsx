// unified-frontend/src/pages/market/StationTradingV2.tsx

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Coins,
  Search,
  Sparkles,
  Clock,
  ChevronDown,
  LayoutGrid,
  Table,
  PieChart,
  Shield,
} from 'lucide-react'
import type { TradingOpportunityV2 } from '@/types/market'
import { CapitalAllocator } from '@/components/market/CapitalAllocator'

const REGIONS = [
  { id: 10000002, name: 'The Forge (Jita)' },
  { id: 10000043, name: 'Domain (Amarr)' },
  { id: 10000030, name: 'Heimatar (Rens)' },
  { id: 10000032, name: 'Sinq Laison (Dodixie)' },
  { id: 10000042, name: 'Metropolis (Hek)' },
]

const CAPITAL_RANGES = [
  { label: 'Any', min: 0, max: undefined },
  { label: '< 100M', min: 0, max: 100000000 },
  { label: '100M - 500M', min: 100000000, max: 500000000 },
  { label: '500M - 1B', min: 500000000, max: 1000000000 },
  { label: '1B - 5B', min: 1000000000, max: 5000000000 },
  { label: '> 5B', min: 5000000000, max: undefined },
]

type ViewMode = 'cards' | 'table' | 'dashboard'

function getRiskColor(score: number) {
  if (score <= 20) return 'text-green-400'
  if (score <= 40) return 'text-blue-400'
  if (score <= 60) return 'text-yellow-400'
  return 'text-red-400'
}

function getRiskLabel(score: number) {
  if (score <= 20) return 'Low Risk'
  if (score <= 40) return 'Moderate'
  if (score <= 60) return 'Elevated'
  return 'High Risk'
}

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

function OpportunityCardV2({ opp }: { opp: TradingOpportunityV2 }) {
  const [isOpen, setIsOpen] = useState(false)
  const [simInvestment, setSimInvestment] = useState('')

  const { data: simulation, isFetching: simulating } = useQuery({
    queryKey: ['simulate', opp.type_id, simInvestment],
    queryFn: () => marketApi.simulateInvestment(opp.type_id, parseInt(simInvestment)),
    enabled: !!simInvestment && parseInt(simInvestment) >= 1000000,
  })

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card className="hover:border-primary/50 transition-all">
        <CardContent className="py-4">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="font-medium text-lg">{opp.type_name}</div>
              <div className="text-xs text-muted-foreground flex items-center gap-2">
                {opp.sub_index && <span>{opp.sub_index}</span>}
                {opp.primary_index && <span>- {opp.primary_index}</span>}
              </div>
            </div>
            <Badge variant="outline" className={cn('text-xs', getRecommendationStyle(opp.recommendation))}>
              {opp.recommendation.toUpperCase()}
            </Badge>
          </div>

          {/* Main Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground text-xs">Margin</div>
              <div className={cn('font-bold', opp.margin_percent >= 15 ? 'text-green-400' : opp.margin_percent >= 10 ? 'text-blue-400' : 'text-yellow-400')}>
                {opp.margin_percent.toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Profit/Unit</div>
              <div className="font-mono text-green-400">{formatISK(opp.profit_per_unit)}</div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Daily Volume</div>
              <div className="font-mono">{opp.avg_daily_volume?.toLocaleString() ?? 'N/A'}/day</div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Capital</div>
              <div className="font-mono">{formatISK(opp.capital_required)}</div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Turnover</div>
              <div className={cn('font-mono flex items-center gap-1',
                  opp.strategy.turnover === 'instant' ? 'text-green-400' :
                  opp.strategy.turnover === 'fast' ? 'text-blue-400' :
                  opp.strategy.turnover === 'moderate' ? 'text-yellow-400' : 'text-red-400')}>
                {opp.strategy.turnover === 'instant' && '⚡'}
                {opp.strategy.turnover === 'fast' && '🟢'}
                {opp.strategy.turnover === 'moderate' && '🟡'}
                {opp.strategy.turnover === 'slow' && '🔴'}
                {opp.strategy.turnover.charAt(0).toUpperCase() + opp.strategy.turnover.slice(1)}
              </div>
            </div>
          </div>

          {/* Secondary Info */}
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
              <span className={cn('flex items-center gap-1', getRiskColor(opp.risk_score))}>
                <Shield className="h-3 w-3" />
                {getRiskLabel(opp.risk_score)}
              </span>
              <span className={cn('flex items-center gap-1', opp.trend_7d >= 0 ? 'text-green-400' : 'text-red-400')}>
                {opp.trend_7d >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {opp.trend_7d >= 0 ? '+' : ''}{opp.trend_7d.toFixed(1)}%
              </span>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 px-2">
                  <ChevronDown className={cn('h-4 w-4 transition-transform', isOpen && 'rotate-180')} />
                  Details
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>

          {/* Expanded Details */}
          <CollapsibleContent>
            <div className="mt-4 pt-4 border-t border-border grid md:grid-cols-3 gap-4">
              {/* Trading Strategy */}
              <div>
                <div className="text-sm font-medium mb-2 flex items-center gap-2">
                  📊 Trading Strategy
                  <Badge variant="outline" className={cn('text-xs',
                    opp.strategy.style === 'active' ? 'border-red-500 text-red-400' :
                    opp.strategy.style === 'semi-active' ? 'border-yellow-500 text-yellow-400' :
                    'border-green-500 text-green-400'
                  )}>
                    {opp.strategy.style}
                  </Badge>
                </div>
                <div className="text-xs space-y-2 p-2 bg-muted/50 rounded">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Update prices:</span>
                    <span className="font-medium">{opp.strategy.update_frequency}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Order duration:</span>
                    <span className="font-medium">{opp.strategy.order_duration}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Competition:</span>
                    <span className={cn('font-medium',
                      opp.strategy.competition === 'extreme' ? 'text-red-400' :
                      opp.strategy.competition === 'high' ? 'text-orange-400' :
                      opp.strategy.competition === 'medium' ? 'text-yellow-400' : 'text-green-400'
                    )}>
                      {opp.strategy.competition} ({opp.competition.buy_orders + opp.competition.sell_orders} orders)
                    </span>
                  </div>
                </div>
                <div className="mt-2 space-y-1">
                  {opp.strategy.tips.map((tip, i) => (
                    <div key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                      <span className="text-blue-400">💡</span> {tip}
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk Factors */}
              <div>
                <div className="text-sm font-medium mb-2">🛡️ Risk Assessment</div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn('h-full', opp.risk_score <= 30 ? 'bg-green-500' : opp.risk_score <= 60 ? 'bg-yellow-500' : 'bg-red-500')}
                      style={{ width: `${100 - opp.risk_score}%` }}
                    />
                  </div>
                  <span className="text-sm font-mono">{100 - opp.risk_score}% Safe</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {opp.risk_factors.map((factor, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {factor}
                    </Badge>
                  ))}
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  Volatility: {opp.price_volatility.toFixed(1)}% |
                  Trend: {opp.trend_7d >= 0 ? '+' : ''}{opp.trend_7d.toFixed(1)}%
                </div>
              </div>

              {/* Portfolio Simulator */}
              <div>
                <div className="text-sm font-medium mb-2">💰 Portfolio Simulator</div>
                <div className="flex gap-2 mb-2">
                  <Input
                    type="number"
                    placeholder="Investment (ISK)"
                    value={simInvestment}
                    onChange={(e) => setSimInvestment(e.target.value)}
                    className="h-8"
                  />
                </div>
                {simulation && !simulating && (
                  <div className="text-xs space-y-1 p-2 bg-muted/50 rounded">
                    <div className="flex justify-between">
                      <span>Units:</span>
                      <span className="font-mono">{simulation.units.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Expected Profit:</span>
                      <span className="font-mono text-green-400">{formatISK(simulation.expected_profit)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Days to Sell:</span>
                      <span className="font-mono">{simulation.days_to_sell?.toFixed(1) ?? '?'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>ROI:</span>
                      <span className="font-mono text-green-400">{simulation.roi_percent.toFixed(1)}%</span>
                    </div>
                  </div>
                )}
                {simulating && <Skeleton className="h-20" />}
              </div>
            </div>
          </CollapsibleContent>
        </CardContent>
      </Card>
    </Collapsible>
  )
}

export function StationTradingV2() {
  const [regionId, setRegionId] = useState(10000002)
  const [primaryIndex, setPrimaryIndex] = useState<string>('')
  const [capitalRange, setCapitalRange] = useState(0)
  const [minMargin, setMinMargin] = useState(5)
  const [minVolume, setMinVolume] = useState(10) // Default: require at least 10/day
  const [maxDays, setMaxDays] = useState<number | undefined>(undefined)
  const [turnover, setTurnover] = useState<string>('')
  const [maxCompetition, setMaxCompetition] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'daily_potential' | 'margin' | 'profit_per_unit' | 'days_to_sell' | 'risk_score' | 'volume'>('daily_potential')
  const [viewMode, setViewMode] = useState<ViewMode>('cards')

  const range = CAPITAL_RANGES[capitalRange]

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['trading-v2', regionId, primaryIndex, range, minMargin, minVolume, maxDays, turnover, maxCompetition, sortBy],
    queryFn: () => marketApi.getTradingOpportunitiesV2(regionId, {
      primaryIndex: primaryIndex || undefined,
      minCapital: range.min,
      maxCapital: range.max,
      minMargin,
      minVolume,
      maxDaysToSell: maxDays,
      turnover: turnover || undefined,
      maxCompetition: maxCompetition || undefined,
      sortBy,
      limit: 200,
    }),
    refetchInterval: 10 * 60 * 1000,
  })

  const opportunities = data?.opportunities ?? []
  const categories = data?.available_categories ?? {}

  const filteredOpps = useMemo(() => {
    if (!searchQuery) return opportunities
    return opportunities.filter(o =>
      o.type_name.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [opportunities, searchQuery])

  // Stats
  const excellentCount = opportunities.filter(o => o.recommendation === 'excellent').length
  const goodCount = opportunities.filter(o => o.recommendation === 'good').length
  const totalDailyPotential = opportunities.reduce((sum, o) => sum + o.daily_potential, 0)
  const avgRisk = opportunities.length > 0
    ? opportunities.reduce((sum, o) => sum + o.risk_score, 0) / opportunities.length
    : 0

  return (
    <div className="p-6 space-y-6">
      <Header
        title="Station Trading V2"
        subtitle={data?.region_name ?? 'Loading...'}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
      />

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-9 gap-4">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Region</div>
              <Select value={String(regionId)} onValueChange={v => setRegionId(Number(v))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {REGIONS.map(r => (
                    <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Category</div>
              <Select value={primaryIndex || '__all__'} onValueChange={v => setPrimaryIndex(v === '__all__' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All Categories</SelectItem>
                  {Object.keys(categories).map(cat => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Capital</div>
              <Select value={String(capitalRange)} onValueChange={v => setCapitalRange(Number(v))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CAPITAL_RANGES.map((r, i) => (
                    <SelectItem key={i} value={String(i)}>{r.label}</SelectItem>
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
                placeholder="10"
              />
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Max Days to Sell</div>
              <Input
                type="number"
                value={maxDays ?? ''}
                onChange={e => setMaxDays(e.target.value ? Number(e.target.value) : undefined)}
                placeholder="Any"
                min={0}
              />
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Turnover</div>
              <Select value={turnover || '__any__'} onValueChange={v => setTurnover(v === '__any__' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="Any" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__any__">Any</SelectItem>
                  <SelectItem value="instant">⚡ Instant (&lt;1 day)</SelectItem>
                  <SelectItem value="fast">🟢 Fast (1-3 days)</SelectItem>
                  <SelectItem value="moderate">🟡 Moderate (3-7 days)</SelectItem>
                  <SelectItem value="slow">🔴 Slow (7+ days)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Competition</div>
              <Select value={maxCompetition || '__any__'} onValueChange={v => setMaxCompetition(v === '__any__' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="Any" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__any__">Any</SelectItem>
                  <SelectItem value="low">🟢 Low (set &amp; forget)</SelectItem>
                  <SelectItem value="medium">🟡 Medium (2-3x daily)</SelectItem>
                  <SelectItem value="high">🟠 High (frequent updates)</SelectItem>
                  <SelectItem value="extreme">🔴 Extreme (constant)</SelectItem>
                </SelectContent>
              </Select>
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

          {/* Sort & View Toggle */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Sort by:</span>
              <Select value={sortBy} onValueChange={(v: typeof sortBy) => setSortBy(v)}>
                <SelectTrigger className="w-40 h-8"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily_potential">Daily Potential</SelectItem>
                  <SelectItem value="margin">Margin %</SelectItem>
                  <SelectItem value="profit_per_unit">Profit/Unit</SelectItem>
                  <SelectItem value="volume">Volume</SelectItem>
                  <SelectItem value="days_to_sell">Days to Sell</SelectItem>
                  <SelectItem value="risk_score">Risk (Low First)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant={viewMode === 'cards' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('cards')}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'table' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('table')}
              >
                <Table className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'dashboard' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('dashboard')}
              >
                <PieChart className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
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
              <Shield className="h-5 w-5 text-purple-400" />
              <div>
                <div className="text-xs text-muted-foreground">Avg Risk</div>
                <div className={cn('text-xl font-bold', getRiskColor(avgRisk))}>{avgRisk.toFixed(0)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-cyan-400" />
              <div>
                <div className="text-xs text-muted-foreground">Opportunities</div>
                <div className="text-xl font-bold">{filteredOpps.length}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Content */}
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
      ) : viewMode === 'cards' ? (
        <div className="space-y-3">
          {filteredOpps.map(opp => (
            <OpportunityCardV2 key={opp.type_id} opp={opp} />
          ))}
        </div>
      ) : viewMode === 'table' ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3">Item</th>
                    <th className="text-right p-3">Margin</th>
                    <th className="text-right p-3">Profit/Unit</th>
                    <th className="text-right p-3">Volume/Day</th>
                    <th className="text-right p-3">Capital</th>
                    <th className="text-right p-3">Days to Sell</th>
                    <th className="text-right p-3">Risk</th>
                    <th className="text-center p-3">Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOpps.map(opp => (
                    <tr key={opp.type_id} className="border-t border-border hover:bg-muted/30">
                      <td className="p-3">
                        <div className="font-medium">{opp.type_name}</div>
                        <div className="text-xs text-muted-foreground">{opp.sub_index}</div>
                      </td>
                      <td className={cn('text-right p-3 font-mono', opp.margin_percent >= 15 ? 'text-green-400' : 'text-yellow-400')}>
                        {opp.margin_percent.toFixed(1)}%
                      </td>
                      <td className="text-right p-3 font-mono text-green-400">{formatISK(opp.profit_per_unit)}</td>
                      <td className="text-right p-3 font-mono">{opp.avg_daily_volume?.toLocaleString() ?? 'N/A'}</td>
                      <td className="text-right p-3 font-mono">{formatISK(opp.capital_required)}</td>
                      <td className={cn('text-right p-3 font-mono',
                        opp.days_to_sell_100 === null ? 'text-muted-foreground' :
                        opp.days_to_sell_100 <= 3 ? 'text-green-400' : 'text-yellow-400')}>
                        {opp.days_to_sell_100 !== null ? opp.days_to_sell_100.toFixed(1) : 'N/A'}
                      </td>
                      <td className={cn('text-right p-3', getRiskColor(opp.risk_score))}>
                        {opp.risk_score}
                      </td>
                      <td className="text-center p-3">
                        <Badge variant="outline" className={cn('text-xs', getRecommendationStyle(opp.recommendation))}>
                          {opp.recommendation.toUpperCase()}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <CapitalAllocator primaryIndex={primaryIndex || undefined} />
      )}
    </div>
  )
}

export default StationTradingV2
