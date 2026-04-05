// unified-frontend/src/pages/market/CompetitionTracker.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import {
  Trophy,
  AlertTriangle,
  TrendingDown,
  Building2,
  ShoppingCart,
  Tag,
  ArrowUp,
  CheckCircle2,
  XCircle,
  Percent,
} from 'lucide-react'
import type { CompetitorInfo } from '@/types/market'

function StatusBadge({ status }: { status: string }) {
  const config = {
    ok: { label: 'Competitive', className: 'bg-green-500/20 text-green-400 border-green-500/50', icon: CheckCircle2 },
    undercut: { label: 'Undercut', className: 'bg-red-500/20 text-red-400 border-red-500/50', icon: TrendingDown },
    outbid: { label: 'Outbid', className: 'bg-amber-500/20 text-amber-400 border-amber-500/50', icon: ArrowUp },
  }[status] ?? { label: 'Unknown', className: 'bg-gray-500/20 text-gray-400', icon: XCircle }

  const Icon = config.icon

  return (
    <Badge variant="outline" className={cn('flex items-center gap-1', config.className)}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  )
}

function OrderTable({ orders, title, icon: Icon, type }: {
  orders: CompetitorInfo[]
  title: string
  icon: React.ElementType
  type: 'sell' | 'buy'
}) {
  if (orders.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Icon className="h-5 w-5" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">No {type} orders</p>
        </CardContent>
      </Card>
    )
  }

  const problemOrders = orders.filter(o => o.status !== 'ok')

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Icon className={cn("h-5 w-5", type === 'sell' ? 'text-red-400' : 'text-green-400')} />
          {title}
        </CardTitle>
        <CardDescription>
          {orders.length} orders | {problemOrders.length} need attention
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2 text-sm font-medium text-muted-foreground">Item</th>
                <th className="text-left py-2 px-2 text-sm font-medium text-muted-foreground">Location</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">Your Price</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">Market Price</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">Gap</th>
                <th className="text-right py-2 px-2 text-sm font-medium text-muted-foreground">Volume</th>
                <th className="text-center py-2 px-2 text-sm font-medium text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order, idx) => (
                <tr
                  key={`${order.type_id}-${idx}`}
                  className={cn(
                    "border-b border-border/50 hover:bg-muted/50 transition-colors",
                    order.status !== 'ok' ? 'bg-red-500/5' : (idx % 2 === 0 ? 'bg-transparent' : 'bg-muted/20')
                  )}
                >
                  <td className="py-2 px-2">
                    <span className="font-medium">{order.type_name}</span>
                  </td>
                  <td className="py-2 px-2 text-sm text-muted-foreground">
                    {order.location_name}
                  </td>
                  <td className="py-2 px-2 text-right text-sm font-medium">
                    {formatISK(order.our_price)}
                  </td>
                  <td className="py-2 px-2 text-right text-sm">
                    {formatISK(order.best_price)}
                  </td>
                  <td className="py-2 px-2 text-right text-sm">
                    {order.price_gap_percent > 0 && (
                      <span className={cn(
                        "flex items-center justify-end gap-1",
                        order.status !== 'ok' ? 'text-red-500' : 'text-muted-foreground'
                      )}>
                        <Percent className="h-3 w-3" />
                        {order.price_gap_percent.toFixed(1)}
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-2 text-right text-sm">
                    {order.volume_remain.toLocaleString()}
                  </td>
                  <td className="py-2 px-2 text-center">
                    <StatusBadge status={order.status} />
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

export function CompetitionTracker() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id
  const [includeCorp, setIncludeCorp] = useState(true)

  const { data: competition, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['competition', characterId, includeCorp],
    queryFn: () => marketApi.getCompetitionReport(characterId!, includeCorp),
    enabled: !!characterId,
    refetchInterval: 2 * 60 * 1000, // 2 minutes - more frequent for competition
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Header title="Competition Tracker" subtitle="Select a character to view competitive position" />
      </div>
    )
  }

  // Calculate stats
  const totalOrders = competition?.total_orders ?? 0
  const competitive = competition?.competitive_orders ?? 0
  const undercut = competition?.undercut_orders ?? 0
  const outbid = competition?.outbid_orders ?? 0
  const competitiveRate = totalOrders > 0 ? (competitive / totalOrders * 100) : 0

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Header
          title="Competition Tracker"
          subtitle="Monitor your competitive position in the market"
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <ShoppingCart className="h-4 w-4" />
              Total Orders
            </div>
            <div className="text-2xl font-bold">
              {isLoading ? '...' : totalOrders}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Trophy className="h-4 w-4 text-green-500" />
              Competitive
            </div>
            <div className="text-2xl font-bold text-green-500">
              {isLoading ? '...' : competitive}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {competitiveRate.toFixed(0)}% of orders
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <TrendingDown className="h-4 w-4 text-red-500" />
              Undercut (Sell)
            </div>
            <div className="text-2xl font-bold text-red-500">
              {isLoading ? '...' : undercut}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Need price reduction
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <ArrowUp className="h-4 w-4 text-amber-500" />
              Outbid (Buy)
            </div>
            <div className="text-2xl font-bold text-amber-500">
              {isLoading ? '...' : outbid}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Need price increase
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Banner */}
      {(undercut > 0 || outbid > 0) && (
        <Card className="border-amber-500/50 bg-amber-500/5">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-foreground">Orders Need Attention</p>
                <p className="text-muted-foreground mt-1">
                  {undercut > 0 && <span className="text-red-500">{undercut} sell orders have been undercut.</span>}
                  {undercut > 0 && outbid > 0 && ' '}
                  {outbid > 0 && <span className="text-amber-500">{outbid} buy orders have been outbid.</span>}
                  {' '}Consider adjusting prices to remain competitive.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading competition data...</div>
      ) : (
        <div className="space-y-6">
          {/* Sell Orders */}
          <OrderTable
            orders={competition?.sell_orders ?? []}
            title="Sell Orders"
            icon={Tag}
            type="sell"
          />

          {/* Buy Orders */}
          <OrderTable
            orders={competition?.buy_orders ?? []}
            title="Buy Orders"
            icon={ShoppingCart}
            type="buy"
          />
        </div>
      )}

      {/* Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Understanding Competition</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <p className="font-medium">Competitive</p>
                <p className="text-muted-foreground">Your order has the best price</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <TrendingDown className="h-4 w-4 text-red-500 mt-0.5" />
              <div>
                <p className="font-medium">Undercut (Sell)</p>
                <p className="text-muted-foreground">Someone is selling cheaper than you</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <ArrowUp className="h-4 w-4 text-amber-500 mt-0.5" />
              <div>
                <p className="font-medium">Outbid (Buy)</p>
                <p className="text-muted-foreground">Someone is buying at a higher price</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
