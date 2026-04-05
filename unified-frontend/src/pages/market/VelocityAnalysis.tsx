// unified-frontend/src/pages/market/VelocityAnalysis.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { cn } from '@/lib/utils'
import {
  Zap,
  Turtle,
  Skull,
  Building2,
  TrendingUp,
  Clock,
  Package,
  BarChart3,
} from 'lucide-react'
import type { ItemVelocity } from '@/types/market'

function VelocityBadge({ velocity }: { velocity: string }) {
  const config = {
    fast: { label: 'Fast', className: 'bg-green-500/20 text-green-400 border-green-500/50' },
    medium: { label: 'Medium', className: 'bg-blue-500/20 text-blue-400 border-blue-500/50' },
    slow: { label: 'Slow', className: 'bg-amber-500/20 text-amber-400 border-amber-500/50' },
    dead: { label: 'Dead', className: 'bg-red-500/20 text-red-400 border-red-500/50' },
    sold_out: { label: 'Sold Out', className: 'bg-gray-500/20 text-gray-400 border-gray-500/50' },
  }[velocity] ?? { label: 'Unknown', className: 'bg-gray-500/20 text-gray-400' }

  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  )
}

function VelocityTable({ items, title, icon: Icon, emptyMessage }: {
  items: ItemVelocity[]
  title: string
  icon: React.ElementType
  emptyMessage: string
}) {
  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Icon className="h-5 w-5" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">{emptyMessage}</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription>{items.length} items</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2 text-sm font-medium text-muted-foreground">Item</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">7d Volume</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">30d Volume</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">Avg/Day</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">Days to Sell</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">Turnover</th>
                <th className="text-center py-2 px-2 text-sm font-medium text-muted-foreground">Class</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr
                  key={item.type_id}
                  className={cn(
                    "border-b border-border/50 hover:bg-muted/50 transition-colors",
                    idx % 2 === 0 ? 'bg-transparent' : 'bg-muted/20'
                  )}
                >
                  <td className="py-2 px-2">
                    <span className="font-medium">{item.type_name}</span>
                  </td>
                  <td className="py-2 px-2 text-right text-sm">
                    <span className="text-green-500">+{item.volume_bought_7d.toLocaleString()}</span>
                    {' / '}
                    <span className="text-red-500">-{item.volume_sold_7d.toLocaleString()}</span>
                  </td>
                  <td className="py-2 px-2 text-right text-sm">
                    <span className="text-green-500">+{item.volume_bought_30d.toLocaleString()}</span>
                    {' / '}
                    <span className="text-red-500">-{item.volume_sold_30d.toLocaleString()}</span>
                  </td>
                  <td className="py-2 px-2 text-right text-sm font-medium">
                    {item.avg_daily_volume.toFixed(1)}
                  </td>
                  <td className="py-2 px-2 text-right text-sm">
                    {item.days_to_sell !== null ? (
                      <span className={cn(
                        item.days_to_sell < 7 ? 'text-green-500' :
                        item.days_to_sell < 30 ? 'text-amber-500' : 'text-red-500'
                      )}>
                        {item.days_to_sell.toFixed(0)}d
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="py-2 px-2 text-right text-sm">
                    {item.turnover_rate.toFixed(1)}x
                  </td>
                  <td className="py-2 px-2 text-center">
                    <VelocityBadge velocity={item.velocity_class} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export function VelocityAnalysis() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id
  const [includeCorp, setIncludeCorp] = useState(true)

  const { data: velocity, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['velocity', characterId, includeCorp],
    queryFn: () => marketApi.getVelocityReport(characterId!, includeCorp),
    enabled: !!characterId,
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Header title="Velocity Analysis" subtitle="Select a character to view item velocity metrics" />
      </div>
    )
  }

  // Summary stats
  const totalFast = velocity?.fast_movers.length ?? 0
  const totalSlow = velocity?.slow_movers.length ?? 0
  const totalDead = velocity?.dead_stock.length ?? 0

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Header
          title="Velocity Analysis"
          subtitle="Identify fast movers, slow movers, and dead stock"
          onRefresh={() => refetch()}
          isRefreshing={isFetching}
        />
        <div className="flex items-center gap-2">
          <Checkbox
            id="include-corp"
            checked={includeCorp}
            onCheckedChange={(checked) => setIncludeCorp(checked === true)}
          />
          <label htmlFor="include-corp" className="text-sm text-muted-foreground flex items-center gap-1 cursor-pointer">
            <Building2 className="h-4 w-4" />
            Include Corp
          </label>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-green-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Zap className="h-4 w-4 text-green-500" />
              Fast Movers
            </div>
            <div className="text-2xl font-bold text-green-500">
              {isLoading ? '...' : totalFast}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              10+ sales/day
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Turtle className="h-4 w-4 text-amber-500" />
              Slow Movers
            </div>
            <div className="text-2xl font-bold text-amber-500">
              {isLoading ? '...' : totalSlow}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              &lt;10 sales/day
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Skull className="h-4 w-4 text-red-500" />
              Dead Stock
            </div>
            <div className="text-2xl font-bold text-red-500">
              {isLoading ? '...' : totalDead}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              No sales in 30d
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Info Banner */}
      <Card className="bg-muted/50">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <BarChart3 className="h-5 w-5 text-blue-400 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-foreground">Understanding Velocity</p>
              <p className="text-muted-foreground mt-1">
                <span className="text-green-500">Fast movers</span> sell quickly (&ge;10/day) - consider restocking.
                {' '}
                <span className="text-amber-500">Slow movers</span> take longer to sell - monitor margins.
                {' '}
                <span className="text-red-500">Dead stock</span> has no recent sales - consider repricing or liquidating.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading velocity data...</div>
      ) : (
        <div className="space-y-6">
          {/* Fast Movers */}
          <VelocityTable
            items={velocity?.fast_movers ?? []}
            title="Fast Movers"
            icon={Zap}
            emptyMessage="No fast-moving items found"
          />

          {/* Slow Movers */}
          <VelocityTable
            items={velocity?.slow_movers ?? []}
            title="Slow Movers"
            icon={Turtle}
            emptyMessage="No slow-moving items found"
          />

          {/* Dead Stock */}
          <VelocityTable
            items={velocity?.dead_stock ?? []}
            title="Dead Stock"
            icon={Skull}
            emptyMessage="No dead stock - all items are selling!"
          />
        </div>
      )}

      {/* Metrics Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Velocity Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-start gap-2">
              <TrendingUp className="h-4 w-4 text-blue-400 mt-0.5" />
              <div>
                <p className="font-medium">Avg/Day</p>
                <p className="text-muted-foreground">Average daily sales volume over 30 days</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Clock className="h-4 w-4 text-amber-400 mt-0.5" />
              <div>
                <p className="font-medium">Days to Sell</p>
                <p className="text-muted-foreground">Estimated days to sell current inventory</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Package className="h-4 w-4 text-green-400 mt-0.5" />
              <div>
                <p className="font-medium">Turnover Rate</p>
                <p className="text-muted-foreground">Annualized inventory turnover (higher = faster)</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
