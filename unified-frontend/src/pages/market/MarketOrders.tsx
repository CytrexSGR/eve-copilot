// unified-frontend/src/pages/market/MarketOrders.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import { AlertTriangle, CheckCircle } from 'lucide-react'

type FilterType = 'all' | 'sell' | 'buy'

export function MarketOrders() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id
  const [filter, setFilter] = useState<FilterType>('all')

  const { data: report, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['undercuts', characterId],
    queryFn: () => marketApi.getOrderUndercuts(characterId!),
    enabled: !!characterId,
    refetchInterval: 5 * 60 * 1000,
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Header title="Market Orders" subtitle="Select a character to view orders" />
      </div>
    )
  }

  const orders = report?.orders ?? []
  const filteredOrders = orders.filter(o => {
    if (filter === 'sell') return !o.is_buy_order
    if (filter === 'buy') return o.is_buy_order
    return true
  })

  const sellCount = orders.filter(o => !o.is_buy_order).length
  const buyCount = orders.filter(o => o.is_buy_order).length

  return (
    <div className="p-6 space-y-6">
      <Header
        title="Market Orders"
        subtitle={`${report?.total_orders ?? 0} active orders`}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
      />

      {/* Summary */}
      <div className="flex items-center gap-4">
        <Badge variant={report?.undercut_count ? "destructive" : "outline"}>
          {report?.undercut_count ?? 0} Undercut
        </Badge>
        <Badge variant={report?.outbid_count ? "outline" : "outline"}
               className={report?.outbid_count ? "border-yellow-500 text-yellow-500" : ""}>
          {report?.outbid_count ?? 0} Outbid
        </Badge>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
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
          Sell ({sellCount})
        </Button>
        <Button
          variant={filter === 'buy' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('buy')}
        >
          Buy ({buyCount})
        </Button>
      </div>

      {/* Orders List */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading orders...</div>
      ) : filteredOrders.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">No orders found</div>
      ) : (
        <div className="space-y-3">
          {filteredOrders.map((order) => (
            <Card key={order.order_id} className={cn(
              order.is_undercut && "border-red-500/50"
            )}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{order.type_name}</span>
                      <Badge variant="outline" className="text-xs">
                        {order.is_buy_order ? 'BUY' : 'SELL'}
                      </Badge>
                      {order.is_undercut ? (
                        <Badge variant="destructive" className="flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          {order.is_buy_order ? 'Outbid' : 'Undercut'} {Math.abs(order.undercut_percent).toFixed(1)}%
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="flex items-center gap-1 border-green-500 text-green-500">
                          <CheckCircle className="h-3 w-3" />
                          OK
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {order.volume_remain.toLocaleString()} units @ {order.location_name}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">{formatISK(order.your_price)}</div>
                    {order.is_undercut && (
                      <div className="text-sm text-muted-foreground">
                        Market: {formatISK(order.market_price)}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
