// unified-frontend/src/pages/market/ArbitragePlanner.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import {
  Truck,
  MapPin,
  Timer,
  TrendingUp,
  Package,
  Route,
  Ship,
  Coins,
  ChevronRight,
} from 'lucide-react'
import type { ArbitrageRoute, ArbitrageItem } from '@/types/market'

const REGIONS = [
  { id: 10000002, name: 'Jita (The Forge)' },
  { id: 10000043, name: 'Amarr (Domain)' },
  { id: 10000030, name: 'Rens (Heimatar)' },
  { id: 10000032, name: 'Dodixie (Sinq Laison)' },
  { id: 10000042, name: 'Hek (Metropolis)' },
]

const CARGO_PRESETS = [
  // User's ships first
  { value: 785000, label: '⭐ Obelisk (Artallus) - 785k m³' },
  { value: 87500, label: '⭐ Orca (Cytricia) - 87.5k m³' },
  // Standard presets
  { value: 5000, label: 'Blockade Runner (~5k m³)' },
  { value: 30000, label: 'DST (~30k m³)' },
  { value: 60000, label: 'DST Expanded (~60k m³)' },
  { value: 350000, label: 'Freighter (~350k m³)' },
  { value: 1000000, label: 'Jump Freighter (~1M m³)' },
]

/**
 * Item row in route cargo
 */
function CargoItem({ item }: { item: ArbitrageItem }) {
  const turnoverColors: Record<string, string> = {
    instant: 'text-cyan-400',
    fast: 'text-green-400',
    moderate: 'text-yellow-400',
    slow: 'text-red-400',
    unknown: 'text-muted-foreground',
  }

  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
      <div className="flex-1">
        <div className="font-medium text-sm">{item.type_name}</div>
        <div className="text-xs text-muted-foreground">
          {item.quantity.toLocaleString()} units • {item.volume.toLocaleString()} m³
        </div>
        {/* Buy/Sell prices */}
        <div className="text-xs mt-1 flex gap-3">
          <span className="text-red-400">
            Buy: {formatISK(item.buy_price_source)}
          </span>
          <span className="text-green-400">
            Sell: {formatISK(item.sell_price_dest)}
          </span>
        </div>
        {/* V2: Volume and turnover info */}
        <div className="text-xs mt-1">
          {item.avg_daily_volume ? (
            <span className={turnoverColors[item.turnover] || 'text-muted-foreground'}>
              {item.avg_daily_volume.toLocaleString()}/day • {item.days_to_sell?.toFixed(1) ?? '?'} days to sell
            </span>
          ) : (
            <span className="text-muted-foreground">No volume data</span>
          )}
        </div>
      </div>
      <div className="text-right">
        <div className="font-mono text-green-400 text-sm">
          +{formatISK(item.total_profit)}
        </div>
        <div className="text-xs text-muted-foreground">
          {formatISK(item.profit_per_unit)}/unit
        </div>
      </div>
    </div>
  )
}

/**
 * Route card component
 */
function RouteCard({ route, startRegion }: { route: ArbitrageRoute; startRegion: string }) {
  return (
    <Card className="hover:border-primary/50 transition-all">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" />
            {startRegion}
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
            {route.destination_hub}
          </CardTitle>
          <Badge variant="outline" className={cn(
            route.safety === 'safe' ? 'border-green-500 text-green-500' :
            route.safety === 'caution' ? 'border-yellow-500 text-yellow-500' :
            'border-red-500 text-red-500'
          )}>
            {route.jumps} jumps
          </Badge>
          {route.avg_days_to_sell !== null && route.avg_days_to_sell !== undefined && (
            <Badge variant="outline" className={cn(
              route.route_risk === 'low' ? 'border-green-500 text-green-500' :
              route.route_risk === 'medium' ? 'border-yellow-500 text-yellow-500' :
              'border-red-500 text-red-500'
            )}>
              ~{route.avg_days_to_sell.toFixed(1)}d
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3" />
              Profit
            </div>
            <div className="font-bold text-green-400 text-lg">
              {formatISK(route.summary.total_profit)}
            </div>
          </div>
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Timer className="h-3 w-3" />
              Per Hour
            </div>
            <div className="font-bold text-lg">
              {formatISK(route.logistics.profit_per_hour)}
            </div>
          </div>
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Coins className="h-3 w-3" />
              ROI
            </div>
            <div className={cn(
              'font-bold text-lg',
              route.summary.roi_percent >= 10 ? 'text-green-400' :
              route.summary.roi_percent >= 5 ? 'text-blue-400' : 'text-foreground'
            )}>
              {route.summary.roi_percent.toFixed(1)}%
            </div>
          </div>
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Ship className="h-3 w-3" />
              Ship
            </div>
            <div className="font-medium text-sm">
              {route.logistics.recommended_ship}
            </div>
          </div>
        </div>

        {/* Logistics Info */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
          <span>
            <Package className="h-4 w-4 inline mr-1" />
            {route.summary.total_items} items
          </span>
          <span>
            <Truck className="h-4 w-4 inline mr-1" />
            {route.summary.total_volume.toLocaleString()} m³
          </span>
          <span>
            <Timer className="h-4 w-4 inline mr-1" />
            {route.logistics.round_trip_time}
          </span>
          <span>
            Capital: {formatISK(route.summary.total_buy_cost)}
          </span>
        </div>

        {/* Cargo Items */}
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-2 py-2 text-sm hover:text-primary transition-colors">
            <ChevronRight className="h-4 w-4 transition-transform [[data-state=open]_&]:rotate-90" />
            View Cargo ({route.items.length} items)
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="max-h-64 overflow-y-auto">
              {route.items.map((item, idx) => (
                <CargoItem key={idx} item={item} />
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  )
}

/**
 * Main Arbitrage Planner page
 */
export function ArbitragePlanner() {
  const [startRegion, setStartRegion] = useState(10000002)
  const [maxJumps, setMaxJumps] = useState(15)
  const [minProfit, setMinProfit] = useState(10000000)
  const [cargoCapacity, setCargoCapacity] = useState(60000)
  const [turnover, setTurnover] = useState<string>('')
  const [maxCompetition, setMaxCompetition] = useState<string>('')
  const [maxDaysToSell, setMaxDaysToSell] = useState<number | undefined>()
  const [minVolume, setMinVolume] = useState<number | undefined>()

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['arbitrage-routes', startRegion, maxJumps, minProfit, cargoCapacity, turnover, maxCompetition, maxDaysToSell, minVolume],
    queryFn: () => marketApi.getArbitrageRoutes(startRegion, {
      maxJumps,
      minProfitPerTrip: minProfit,
      cargoCapacity,
      turnover: turnover || undefined,
      maxCompetition: maxCompetition || undefined,
      maxDaysToSell,
      minVolume,
    }),
    refetchInterval: 10 * 60 * 1000,
  })

  const routes = data?.routes ?? []
  const startHub = REGIONS.find(r => r.id === startRegion)?.name.split(' ')[0] ?? 'Unknown'

  // Stats
  const totalPotential = routes.reduce((sum, r) => sum + r.summary.total_profit, 0)
  const bestRoute = routes[0]

  return (
    <div className="p-6 space-y-6">
      <Header
        title="Arbitrage Planner"
        subtitle={`Routes from ${startHub}`}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
      />

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            {/* Start Region dropdown */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Start Region</div>
              <Select value={String(startRegion)} onValueChange={v => setStartRegion(Number(v))}>
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

            {/* Cargo Capacity dropdown */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Cargo Capacity</div>
              <Select value={String(cargoCapacity)} onValueChange={v => setCargoCapacity(Number(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CARGO_PRESETS.map(p => (
                    <SelectItem key={p.value} value={String(p.value)}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Max Jumps input */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Max Jumps</div>
              <Input
                type="number"
                value={maxJumps}
                onChange={e => setMaxJumps(Number(e.target.value))}
                min={1}
                max={50}
              />
            </div>

            {/* Min Profit input */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Min Profit/Trip</div>
              <Input
                type="number"
                value={minProfit}
                onChange={e => setMinProfit(Number(e.target.value))}
                min={0}
              />
            </div>

            {/* Turnover filter */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Turnover</div>
              <Select value={turnover || '__any__'} onValueChange={v => setTurnover(v === '__any__' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Any" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__any__">Any</SelectItem>
                  <SelectItem value="instant">Instant (&lt;1 day)</SelectItem>
                  <SelectItem value="fast">Fast (1-3 days)</SelectItem>
                  <SelectItem value="moderate">Moderate (3-7 days)</SelectItem>
                  <SelectItem value="slow">Slow (7+ days)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Max Competition filter */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Max Competition</div>
              <Select value={maxCompetition || '__any__'} onValueChange={v => setMaxCompetition(v === '__any__' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Any" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__any__">Any</SelectItem>
                  <SelectItem value="low">Low (5 sellers)</SelectItem>
                  <SelectItem value="medium">Medium (15)</SelectItem>
                  <SelectItem value="high">High (30)</SelectItem>
                  <SelectItem value="extreme">Extreme (30+)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Max Days to Sell */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Max Days</div>
              <Input
                type="number"
                value={maxDaysToSell ?? ''}
                onChange={e => setMaxDaysToSell(e.target.value ? Number(e.target.value) : undefined)}
                placeholder="Any"
                min={1}
                max={30}
              />
            </div>

            {/* Min Volume */}
            <div>
              <div className="text-xs text-muted-foreground mb-1">Min Volume/Day</div>
              <Input
                type="number"
                value={minVolume ?? ''}
                onChange={e => setMinVolume(e.target.value ? Number(e.target.value) : undefined)}
                placeholder="Any"
                min={0}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <Route className="h-5 w-5 text-primary" />
              <div>
                <div className="text-xs text-muted-foreground">Routes Found</div>
                <div className="text-xl font-bold">{routes.length}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-400" />
              <div>
                <div className="text-xs text-muted-foreground">Total Potential</div>
                <div className="text-lg font-bold text-green-400">{formatISK(totalPotential)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <Timer className="h-5 w-5 text-blue-400" />
              <div>
                <div className="text-xs text-muted-foreground">Best ISK/Hour</div>
                <div className="text-lg font-bold text-blue-400">
                  {bestRoute ? formatISK(bestRoute.logistics.profit_per_hour) : '-'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2">
              <Truck className="h-5 w-5 text-purple-400" />
              <div>
                <div className="text-xs text-muted-foreground">Cargo</div>
                <div className="text-lg font-bold">{cargoCapacity.toLocaleString()} m³</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Routes List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-48" />)}
        </div>
      ) : routes.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Route className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No profitable routes found</p>
            <p className="text-sm mt-2">Try adjusting filters or selecting a different starting region</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {routes.map((route, idx) => (
            <RouteCard key={idx} route={route} startRegion={startHub} />
          ))}
        </div>
      )}
    </div>
  )
}

export default ArbitragePlanner
