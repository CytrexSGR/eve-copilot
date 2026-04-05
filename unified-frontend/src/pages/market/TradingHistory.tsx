// unified-frontend/src/pages/market/TradingHistory.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  History,
  TrendingUp,
  TrendingDown,
  Calendar,
  Clock,
  BarChart3,
  Lightbulb,
  Building2,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { TradingHistory, TradeEntry, ItemPerformance } from '@/types/market'

const formatISK = (value: number): string => {
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B`
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toFixed(0)
}

const formatTimeAgo = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function TradeRow({ trade }: { trade: TradeEntry }) {
  return (
    <div className="flex items-center justify-between p-3 hover:bg-muted/50 rounded-lg transition-colors">
      <div className="flex items-center gap-3">
        {trade.is_buy ? (
          <ArrowDownRight className="h-4 w-4 text-red-500" />
        ) : (
          <ArrowUpRight className="h-4 w-4 text-green-500" />
        )}
        <div>
          <div className="font-medium text-sm">{trade.type_name}</div>
          <div className="text-xs text-muted-foreground">
            {trade.quantity.toLocaleString()} x {formatISK(trade.unit_price)}
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className={`font-medium text-sm ${trade.is_buy ? 'text-red-500' : 'text-green-500'}`}>
          {trade.is_buy ? '-' : '+'}{formatISK(trade.total_value)}
        </div>
        <div className="text-xs text-muted-foreground">{formatTimeAgo(trade.date)}</div>
      </div>
    </div>
  )
}

function ItemPerformanceRow({ item, rank }: { item: ItemPerformance; rank: number }) {
  const isProfit = item.total_profit >= 0

  return (
    <div className="flex items-center justify-between p-3 hover:bg-muted/50 rounded-lg transition-colors">
      <div className="flex items-center gap-3">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
          isProfit ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
        }`}>
          {rank}
        </div>
        <div>
          <div className="font-medium text-sm">{item.type_name}</div>
          <div className="text-xs text-muted-foreground">
            Bought: {item.total_bought} | Sold: {item.total_sold}
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className={`font-medium text-sm ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
          {isProfit ? '+' : ''}{formatISK(item.total_profit)}
        </div>
        <div className="text-xs text-muted-foreground">
          {item.margin_percent.toFixed(1)}% margin
        </div>
      </div>
    </div>
  )
}

export default function TradingHistoryPage() {
  const { selectedCharacter } = useCharacterContext()
  const [includeCorp, setIncludeCorp] = useState(true)
  const [days, setDays] = useState(30)

  const characterId = selectedCharacter?.character_id

  const { data, isLoading, error } = useQuery<TradingHistory>({
    queryKey: ['trading-history', characterId, days, includeCorp],
    queryFn: () => marketApi.getTradingHistory(characterId!, { days, includeCorp }),
    enabled: !!characterId,
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Please select a character to view trading history.
          </CardContent>
        </Card>
      </div>
    )
  }

  // Prepare hourly chart data
  const hourlyChartData = data?.hourly_patterns.map(p => ({
    hour: `${p.hour.toString().padStart(2, '0')}:00`,
    trades: p.trade_count,
  })) ?? []

  // Prepare day of week chart data
  const dowChartData = data?.day_of_week_patterns.map(p => ({
    day: p.day_name.slice(0, 3),
    profit: p.profit_estimate / 1_000_000,
    trades: p.trade_count,
  })) ?? []

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Trading History</h1>
            <p className="text-muted-foreground">
              Trade journal and pattern analysis
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            {[7, 14, 30, 60, 90].map((d) => (
              <Button
                key={d}
                variant={days === d ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDays(d)}
              >
                {d}d
              </Button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="include-corp"
              checked={includeCorp}
              onCheckedChange={(checked: boolean) => setIncludeCorp(checked)}
            />
            <label
              htmlFor="include-corp"
              className="text-sm text-muted-foreground flex items-center gap-1 cursor-pointer"
            >
              <Building2 className="h-4 w-4" />
              Include Corp
            </label>
          </div>
        </div>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Loading trading history...
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="p-6 text-center text-red-500">
            Error loading history: {(error as Error).message}
          </CardContent>
        </Card>
      ) : data ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-l-4 border-l-blue-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Total Trades
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.total_trades}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Last {days} days
                </div>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-red-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <TrendingDown className="h-4 w-4" />
                  Total Bought
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-500">
                  {formatISK(data.total_buy_value)}
                </div>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-green-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Total Sold
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">
                  {formatISK(data.total_sell_value)}
                </div>
              </CardContent>
            </Card>

            <Card className={`border-l-4 ${data.estimated_profit >= 0 ? 'border-l-green-500' : 'border-l-red-500'}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Estimated Profit
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${data.estimated_profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {data.estimated_profit >= 0 ? '+' : ''}{formatISK(data.estimated_profit)}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Insights */}
          {data.insights.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-yellow-500" />
                  Insights
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {data.insights.map((insight, idx) => (
                    <div key={idx} className="p-3 bg-muted/50 rounded-lg text-sm">
                      {insight}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Hourly Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="h-5 w-5 text-blue-500" />
                  Hourly Activity
                </CardTitle>
                <CardDescription>Trade count by hour (UTC)</CardDescription>
              </CardHeader>
              <CardContent>
                {hourlyChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={hourlyChartData}>
                      <XAxis dataKey="hour" stroke="#6b7280" fontSize={10} tickLine={false} interval={3} />
                      <YAxis stroke="#6b7280" fontSize={12} tickLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                        formatter={(value) => [value, 'Trades']}
                      />
                      <Bar dataKey="trades" fill="#3b82f6" radius={[2, 2, 0, 0]}>
                        {hourlyChartData.map((_, index) => {
                          const isBest = data.best_trading_hours.includes(index)
                          return <Cell key={index} fill={isBest ? '#22c55e' : '#3b82f6'} />
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                    No activity data
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Day of Week Profit */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-purple-500" />
                  Weekly Patterns
                </CardTitle>
                <CardDescription>Estimated profit by day (millions ISK)</CardDescription>
              </CardHeader>
              <CardContent>
                {dowChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={dowChartData}>
                      <XAxis dataKey="day" stroke="#6b7280" fontSize={12} tickLine={false} />
                      <YAxis stroke="#6b7280" fontSize={12} tickLine={false} tickFormatter={(v) => `${v}M`} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                        formatter={(value) => [`${Number(value).toFixed(1)}M ISK`, 'Profit']}
                      />
                      <Bar dataKey="profit" radius={[4, 4, 0, 0]}>
                        {dowChartData.map((entry, index) => (
                          <Cell key={index} fill={entry.profit >= 0 ? '#22c55e' : '#ef4444'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                    No weekly data
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Recent Trades & Top Items */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Trades */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <History className="h-5 w-5 text-blue-500" />
                  Recent Trades
                </CardTitle>
                <CardDescription>Last 20 transactions</CardDescription>
              </CardHeader>
              <CardContent className="max-h-[400px] overflow-y-auto">
                {data.recent_trades.length > 0 ? (
                  <div className="space-y-1">
                    {data.recent_trades.slice(0, 20).map((trade) => (
                      <TradeRow key={trade.transaction_id} trade={trade} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No recent trades
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top Items */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-500" />
                  Top Performing Items
                </CardTitle>
                <CardDescription>By total profit</CardDescription>
              </CardHeader>
              <CardContent className="max-h-[400px] overflow-y-auto">
                {data.top_items.length > 0 ? (
                  <div className="space-y-1">
                    {data.top_items.map((item, idx) => (
                      <ItemPerformanceRow key={item.type_id} item={item} rank={idx + 1} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No item data
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
