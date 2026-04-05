// unified-frontend/src/pages/market/MarketDashboard.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { charactersApi } from '@/api/characters'
import { formatISK } from '@/lib/utils'
import type { ItemPnL } from '@/types/market'
import {
  ArrowRight,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  ShoppingCart,
  Wallet,
  Trophy,
  Skull,
  Building2,
  BarChart3,
  Percent,
  Package,
  Bell,
  Target,
  Shield,
  History,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts'

export function MarketDashboard() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id
  const [includeCorp, setIncludeCorp] = useState(true)

  // Get wallet balance
  const { data: wallet } = useQuery({
    queryKey: ['wallet', characterId],
    queryFn: () => charactersApi.getWallet(characterId!),
    enabled: !!characterId,
  })

  // Get order undercuts
  const { data: undercuts } = useQuery({
    queryKey: ['undercuts', characterId],
    queryFn: () => marketApi.getOrderUndercuts(characterId!),
    enabled: !!characterId,
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  })

  // Get portfolio history
  const { data: portfolio } = useQuery({
    queryKey: ['portfolio', characterId],
    queryFn: () => marketApi.getPortfolioHistory(characterId!, 30),
    enabled: !!characterId,
  })

  // Get trading summary (new analytics)
  const { data: tradingSummary } = useQuery({
    queryKey: ['trading-summary', characterId, includeCorp],
    queryFn: () => marketApi.getTradingSummary(characterId!, includeCorp),
    enabled: !!characterId,
    refetchInterval: 5 * 60 * 1000,
  })

  // Get P&L report for top performers
  const { data: pnlReport } = useQuery({
    queryKey: ['trading-pnl', characterId, includeCorp],
    queryFn: () => marketApi.getTradingPnL(characterId!, { includeCorp, days: 30 }),
    enabled: !!characterId,
  })

  // Get margin alerts
  const { data: marginAlerts } = useQuery({
    queryKey: ['margin-alerts', characterId],
    queryFn: () => marketApi.getMarginAlerts(characterId!, 10),
    enabled: !!characterId,
    refetchInterval: 5 * 60 * 1000,
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Header title="Trading Intelligence" subtitle="Select a character to view market data" />
      </div>
    )
  }

  const chartData = portfolio?.snapshots.map(s => ({
    date: new Date(s.snapshot_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: s.total_liquid / 1_000_000_000,
  })) ?? []

  // P&L breakdown for bar chart
  const pnlChartData = pnlReport?.top_winners.slice(0, 5).map(item => ({
    name: item.type_name.length > 15 ? item.type_name.slice(0, 15) + '...' : item.type_name,
    pnl: item.realized_pnl / 1_000_000,
  })) ?? []

  const criticalAlerts = marginAlerts?.filter(a => a.severity === 'critical') ?? []
  const warningAlerts = marginAlerts?.filter(a => a.severity === 'warning') ?? []

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Header title="Trading Intelligence" subtitle="Comprehensive P&L analysis and market insights" />
        <div className="flex items-center gap-2">
          <Checkbox
            id="include-corp"
            checked={includeCorp}
            onCheckedChange={(checked) => setIncludeCorp(checked === true)}
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

      {/* P&L Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total P&L */}
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Total P&L (30d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(tradingSummary?.total_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {tradingSummary ? formatISK(tradingSummary.total_pnl) : '—'}
            </div>
            {tradingSummary && (
              <div className="text-xs text-muted-foreground mt-1">
                Realized: {formatISK(tradingSummary.total_realized_pnl)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Wallet Balance */}
        <Card className="border-l-4 border-l-purple-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              Wallet Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {wallet ? formatISK(wallet.balance) : '—'}
            </div>
            {portfolio && (
              <div className={`text-xs flex items-center gap-1 mt-1 ${portfolio.growth_percent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {portfolio.growth_percent >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {portfolio.growth_percent >= 0 ? '+' : ''}{portfolio.growth_percent.toFixed(1)}% this month
              </div>
            )}
          </CardContent>
        </Card>

        {/* Items Traded */}
        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Package className="h-4 w-4" />
              Items Traded
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {tradingSummary?.items_traded ?? 0}
            </div>
            <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
              <span className="text-green-500">{tradingSummary?.profitable_items ?? 0} profitable</span>
              <span className="text-red-500">{tradingSummary?.losing_items ?? 0} losing</span>
            </div>
          </CardContent>
        </Card>

        {/* Active Orders */}
        <Card className="border-l-4 border-l-cyan-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <ShoppingCart className="h-4 w-4" />
              Active Orders
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="text-2xl font-bold">
                {undercuts?.total_orders ?? 0}
              </div>
              {(undercuts?.undercut_count ?? 0) > 0 && (
                <Badge variant="destructive" className="text-xs">
                  {undercuts?.undercut_count} undercut
                </Badge>
              )}
            </div>
            <Link
              to="/market/orders"
              className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1 mt-1"
            >
              Manage orders <ArrowRight className="h-3 w-3" />
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Section */}
      {(criticalAlerts.length > 0 || warningAlerts.length > 0) && (
        <Card className="border-red-500/50 bg-red-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2 text-red-400">
              <AlertTriangle className="h-5 w-5" />
              Margin Alerts
            </CardTitle>
            <CardDescription>Items requiring immediate attention</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {criticalAlerts.slice(0, 6).map((alert) => (
                <div key={alert.type_id} className="flex items-center justify-between p-3 bg-red-500/10 rounded-lg border border-red-500/30">
                  <div>
                    <div className="font-medium text-sm">{alert.type_name}</div>
                    <div className="text-xs text-muted-foreground">
                      Your: {formatISK(alert.your_price)} | Market: {formatISK(alert.market_price)}
                    </div>
                  </div>
                  <Badge variant="destructive" className="ml-2">
                    {alert.margin_percent.toFixed(1)}%
                  </Badge>
                </div>
              ))}
              {warningAlerts.slice(0, 3).map((alert) => (
                <div key={alert.type_id} className="flex items-center justify-between p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
                  <div>
                    <div className="font-medium text-sm">{alert.type_name}</div>
                    <div className="text-xs text-muted-foreground">
                      Your: {formatISK(alert.your_price)} | Market: {formatISK(alert.market_price)}
                    </div>
                  </div>
                  <Badge variant="outline" className="ml-2 border-yellow-500 text-yellow-500">
                    {alert.margin_percent.toFixed(1)}%
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Portfolio Value</CardTitle>
            <CardDescription>30-day portfolio trend</CardDescription>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <XAxis dataKey="date" stroke="#6b7280" fontSize={12} tickLine={false} />
                  <YAxis stroke="#6b7280" fontSize={12} tickLine={false} tickFormatter={(v) => `${v.toFixed(1)}B`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                    formatter={(value) => [`${Number(value).toFixed(2)}B ISK`, 'Value']}
                  />
                  <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                No portfolio data yet. Snapshots are created daily.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Performers Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Top Performing Items</CardTitle>
            <CardDescription>Highest realized P&L (millions ISK)</CardDescription>
          </CardHeader>
          <CardContent>
            {pnlChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={pnlChartData} layout="vertical">
                  <XAxis type="number" stroke="#6b7280" fontSize={12} tickFormatter={(v) => `${v}M`} />
                  <YAxis type="category" dataKey="name" stroke="#6b7280" fontSize={11} width={100} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                    formatter={(value) => [`${Number(value).toFixed(1)}M ISK`, 'P&L']}
                  />
                  <Bar dataKey="pnl" radius={[0, 4, 4, 0]}>
                    {pnlChartData.map((_, index) => (
                      <Cell key={index} fill={index === 0 ? '#22c55e' : index === 1 ? '#3b82f6' : '#6b7280'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                No trading data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Tools */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Link to="/market/pnl" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                <div>
                  <div className="font-medium text-sm">P&L Analysis</div>
                  <div className="text-xs text-muted-foreground">Detailed breakdown</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/velocity" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <TrendingUp className="h-5 w-5 text-green-500" />
                <div>
                  <div className="font-medium text-sm">Velocity</div>
                  <div className="text-xs text-muted-foreground">Fast/slow movers</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/competition" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Trophy className="h-5 w-5 text-cyan-500" />
                <div>
                  <div className="font-medium text-sm">Competition</div>
                  <div className="text-xs text-muted-foreground">Market position</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/alerts" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Bell className="h-5 w-5 text-red-500" />
                <div>
                  <div className="font-medium text-sm">Alerts</div>
                  <div className="text-xs text-muted-foreground">Discord notifications</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/goals" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Target className="h-5 w-5 text-emerald-500" />
                <div>
                  <div className="font-medium text-sm">Goals</div>
                  <div className="text-xs text-muted-foreground">Trading targets</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/risk" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-indigo-500" />
                <div>
                  <div className="font-medium text-sm">Risk</div>
                  <div className="text-xs text-muted-foreground">Portfolio analysis</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/history" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <History className="h-5 w-5 text-orange-500" />
                <div>
                  <div className="font-medium text-sm">History</div>
                  <div className="text-xs text-muted-foreground">Trade journal</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/orders" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <ShoppingCart className="h-5 w-5 text-amber-500" />
                <div>
                  <div className="font-medium text-sm">Orders</div>
                  <div className="text-xs text-muted-foreground">Manage orders</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/transactions" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Wallet className="h-5 w-5 text-purple-500" />
                <div>
                  <div className="font-medium text-sm">Transactions</div>
                  <div className="text-xs text-muted-foreground">Trade history</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/prices" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Package className="h-5 w-5 text-rose-500" />
                <div>
                  <div className="font-medium text-sm">Price Map</div>
                  <div className="text-xs text-muted-foreground">Regional prices</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/multi-account" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Building2 className="h-5 w-5 text-cyan-500" />
                <div>
                  <div className="font-medium text-sm">Multi-Account</div>
                  <div className="text-xs text-muted-foreground">All characters</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/station-trading-v2" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <BarChart3 className="h-5 w-5 text-emerald-500" />
                <div>
                  <div className="font-medium text-sm">Station Trading</div>
                  <div className="text-xs text-muted-foreground">Find opportunities</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/market/arbitrage" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Percent className="h-5 w-5 text-yellow-500" />
                <div>
                  <div className="font-medium text-sm">Arbitrage</div>
                  <div className="text-xs text-muted-foreground">Hauling routes</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Top Winners/Losers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Winners */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Trophy className="h-5 w-5 text-green-500" />
                Top Winners
              </CardTitle>
              <CardDescription>Highest profit items</CardDescription>
            </div>
            <Link to="/market/pnl" className="text-sm text-muted-foreground hover:text-primary flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent>
            {pnlReport?.top_winners && pnlReport.top_winners.length > 0 ? (
              <div className="space-y-3">
                {pnlReport.top_winners.slice(0, 5).map((item, idx) => (
                  <ItemPnLRow key={item.type_id} item={item} rank={idx + 1} variant="winner" />
                ))}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                No profitable trades yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Losers */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Skull className="h-5 w-5 text-red-500" />
                Top Losers
              </CardTitle>
              <CardDescription>Items to watch</CardDescription>
            </div>
            <Link to="/market/pnl" className="text-sm text-muted-foreground hover:text-primary flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent>
            {pnlReport?.top_losers && pnlReport.top_losers.length > 0 ? (
              <div className="space-y-3">
                {pnlReport.top_losers.slice(0, 5).map((item, idx) => (
                  <ItemPnLRow key={item.type_id} item={item} rank={idx + 1} variant="loser" />
                ))}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                No losing trades - great performance!
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Helper component for P&L rows
function ItemPnLRow({ item, rank, variant }: { item: ItemPnL; rank: number; variant: 'winner' | 'loser' }) {
  const isWinner = variant === 'winner'

  return (
    <div className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
          isWinner ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
        }`}>
          {rank}
        </div>
        <div>
          <div className="font-medium text-sm">{item.type_name}</div>
          <div className="text-xs text-muted-foreground flex items-center gap-2">
            <span>Qty: {item.total_sold.toLocaleString()}</span>
            {item.margin_percent !== 0 && (
              <span className="flex items-center gap-1">
                <Percent className="h-3 w-3" />
                {item.margin_percent.toFixed(1)}%
              </span>
            )}
          </div>
        </div>
      </div>
      <div className={`text-sm font-bold ${isWinner ? 'text-green-500' : 'text-red-500'}`}>
        {isWinner ? '+' : ''}{formatISK(item.realized_pnl)}
      </div>
    </div>
  )
}
