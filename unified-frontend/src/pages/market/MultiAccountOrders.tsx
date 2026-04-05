// unified-frontend/src/pages/market/MultiAccountOrders.tsx

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import {
  Users,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  Package,
  Wallet,
} from 'lucide-react'
import type { AggregatedOrder, CharacterOrderSummary } from '@/types/market'

type FilterType = 'all' | 'sell' | 'buy' | 'outbid'

/**
 * Summary card component
 */
function SummaryCard({
  icon: Icon,
  label,
  value,
  subValue,
  color = 'text-foreground',
}: {
  icon: React.ElementType
  label: string
  value: string | number
  subValue?: string
  color?: string
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg bg-secondary', color.includes('green') && 'bg-green-500/20', color.includes('red') && 'bg-red-500/20', color.includes('yellow') && 'bg-yellow-500/20')}>
            <Icon className={cn('h-5 w-5', color)} />
          </div>
          <div>
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className={cn('text-xl font-bold', color)}>{value}</div>
            {subValue && <div className="text-xs text-muted-foreground">{subValue}</div>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Character summary row
 */
function CharacterRow({ char }: { char: CharacterOrderSummary }) {
  const slotPercent = (char.order_slots_used / char.order_slots_max) * 100

  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0">
      <div>
        <div className="font-medium">{char.character_name}</div>
        <div className="text-sm text-muted-foreground">
          {char.order_slots_used}/{char.order_slots_max} slots ({slotPercent.toFixed(0)}%)
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm">
          <span className="text-green-400">{char.sell_orders} sell</span>
          {' / '}
          <span className="text-blue-400">{char.buy_orders} buy</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {formatISK(char.isk_in_sell_orders + char.isk_in_escrow)} total
        </div>
      </div>
    </div>
  )
}

/**
 * Order row component
 */
function OrderRow({ order }: { order: AggregatedOrder }) {
  const isOutbid = order.market_status.is_outbid

  return (
    <Card className={cn(
      'transition-all',
      isOutbid && 'border-yellow-500/50 bg-yellow-500/5'
    )}>
      <CardContent className="py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              'p-1.5 rounded',
              order.is_buy_order ? 'bg-blue-500/20' : 'bg-green-500/20'
            )}>
              {order.is_buy_order ? (
                <TrendingDown className="h-4 w-4 text-blue-400" />
              ) : (
                <TrendingUp className="h-4 w-4 text-green-400" />
              )}
            </div>
            <div>
              <div className="font-medium">{order.type_name}</div>
              <div className="text-xs text-muted-foreground">
                {order.character_name} • {order.location_name}
              </div>
            </div>
          </div>

          <div className="text-right">
            <div className={cn(
              'font-mono',
              isOutbid ? 'text-yellow-400' : 'text-foreground'
            )}>
              {formatISK(order.price)}
            </div>
            <div className="text-xs text-muted-foreground">
              {order.volume_remain.toLocaleString()} / {order.volume_total.toLocaleString()}
            </div>
          </div>

          <div className="ml-4">
            {isOutbid ? (
              <Badge variant="outline" className="border-yellow-500 text-yellow-500">
                <AlertTriangle className="h-3 w-3 mr-1" />
                {order.is_buy_order ? 'Outbid' : 'Undercut'}
              </Badge>
            ) : (
              <Badge variant="outline" className="border-green-500 text-green-500">
                <CheckCircle className="h-3 w-3 mr-1" />
                Best
              </Badge>
            )}
          </div>
        </div>

        {isOutbid && (
          <div className="mt-2 pt-2 border-t border-border text-xs text-muted-foreground">
            <span className="text-yellow-400">
              {order.is_buy_order ? 'Best buy' : 'Best sell'}: {formatISK(order.is_buy_order ? order.market_status.current_best_buy : order.market_status.current_best_sell)}
            </span>
            <span className="mx-2">•</span>
            <span>Diff: {formatISK(order.market_status.outbid_by)}</span>
            <span className="mx-2">•</span>
            <span>Spread: {order.market_status.spread_percent.toFixed(1)}%</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Main Multi-Account Orders page
 */
export function MultiAccountOrders() {
  const [filter, setFilter] = useState<FilterType>('all')

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['aggregated-orders'],
    queryFn: () => marketApi.getAggregatedOrders(),
    refetchInterval: 5 * 60 * 1000,
  })

  const summary = data?.summary
  const byCharacter = data?.by_character ?? []
  const orders = data?.orders ?? []

  // Filter orders
  const filteredOrders = useMemo(() => {
    return orders.filter(o => {
      if (filter === 'sell') return !o.is_buy_order
      if (filter === 'buy') return o.is_buy_order
      if (filter === 'outbid') return o.market_status.is_outbid
      return true
    })
  }, [orders, filter])

  const outbidTotal = (summary?.outbid_count ?? 0) + (summary?.undercut_count ?? 0)

  return (
    <div className="p-6 space-y-6">
      <Header
        title="Multi-Account Orders"
        subtitle={`${summary?.total_characters ?? 0} characters • ${orders.length} total orders`}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
      />

      {/* Summary Cards */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard
            icon={Users}
            label="Characters"
            value={summary?.total_characters ?? 0}
            subValue={`${summary?.total_buy_orders ?? 0} buy / ${summary?.total_sell_orders ?? 0} sell`}
          />
          <SummaryCard
            icon={TrendingUp}
            label="Sell Orders Value"
            value={formatISK(summary?.total_isk_in_sell_orders ?? 0)}
            color="text-green-400"
          />
          <SummaryCard
            icon={Wallet}
            label="ISK in Escrow"
            value={formatISK(summary?.total_isk_in_buy_orders ?? 0)}
            color="text-blue-400"
          />
          <SummaryCard
            icon={AlertTriangle}
            label="Need Attention"
            value={outbidTotal}
            subValue={`${summary?.outbid_count ?? 0} outbid / ${summary?.undercut_count ?? 0} undercut`}
            color={outbidTotal > 0 ? 'text-yellow-400' : 'text-green-400'}
          />
        </div>
      )}

      {/* Character Breakdown */}
      {byCharacter.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="h-5 w-5" />
              By Character
            </CardTitle>
          </CardHeader>
          <CardContent>
            {byCharacter.map(char => (
              <CharacterRow key={char.character_id} char={char} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All ({orders.length})
        </Button>
        <Button
          variant={filter === 'sell' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('sell')}
        >
          <TrendingUp className="h-4 w-4 mr-1" />
          Sell ({orders.filter(o => !o.is_buy_order).length})
        </Button>
        <Button
          variant={filter === 'buy' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('buy')}
        >
          <TrendingDown className="h-4 w-4 mr-1" />
          Buy ({orders.filter(o => o.is_buy_order).length})
        </Button>
        <Button
          variant={filter === 'outbid' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('outbid')}
          className={outbidTotal > 0 ? 'border-yellow-500' : ''}
        >
          <AlertTriangle className="h-4 w-4 mr-1" />
          Needs Attention ({outbidTotal})
        </Button>
      </div>

      {/* Orders List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : filteredOrders.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No orders found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredOrders.map(order => (
            <OrderRow key={order.order_id} order={order} />
          ))}
        </div>
      )}
    </div>
  )
}

export default MultiAccountOrders
