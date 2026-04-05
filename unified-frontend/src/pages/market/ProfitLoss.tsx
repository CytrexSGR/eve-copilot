// unified-frontend/src/pages/market/ProfitLoss.tsx

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import {
  TrendingUp,
  PiggyBank,
  Building2,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  Filter,
  Percent,
  Package,
  Trophy,
  Skull,
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

type SortField = 'realized_pnl' | 'margin_percent' | 'roi_percent' | 'total_sold' | 'type_name'
type SortDirection = 'asc' | 'desc'
type FilterType = 'all' | 'winners' | 'losers'

export function ProfitLoss() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id

  // State
  const [includeCorp, setIncludeCorp] = useState(true)
  const [days, setDays] = useState(30)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState<SortField>('realized_pnl')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [filterType, setFilterType] = useState<FilterType>('all')

  // Get trading P&L report
  const { data: pnlReport, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['trading-pnl', characterId, includeCorp, days],
    queryFn: () => marketApi.getTradingPnL(characterId!, { includeCorp, days }),
    enabled: !!characterId,
  })

  // Get portfolio history for chart
  const { data: portfolio } = useQuery({
    queryKey: ['portfolio', characterId, days],
    queryFn: () => marketApi.getPortfolioHistory(characterId!, days),
    enabled: !!characterId,
  })

  // Filter and sort items
  const filteredItems = useMemo(() => {
    if (!pnlReport?.items) return []

    let items = [...pnlReport.items]

    // Filter by search term
    if (searchTerm) {
      items = items.filter(item =>
        item.type_name.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    // Filter by winner/loser
    if (filterType === 'winners') {
      items = items.filter(item => item.realized_pnl > 0)
    } else if (filterType === 'losers') {
      items = items.filter(item => item.realized_pnl < 0)
    }

    // Sort
    items.sort((a, b) => {
      const aVal = a[sortField]
      const bVal = b[sortField]

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      return sortDirection === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number)
    })

    return items
  }, [pnlReport?.items, searchTerm, filterType, sortField, sortDirection])

  // P&L distribution data - must be before early return to follow Rules of Hooks
  const pnlDistribution = useMemo(() => {
    if (!pnlReport?.items) return []

    const winners = pnlReport.items.filter(i => i.realized_pnl > 0)
    const losers = pnlReport.items.filter(i => i.realized_pnl < 0)

    return [
      { name: 'Winners', count: winners.length, value: winners.reduce((sum, i) => sum + i.realized_pnl, 0) },
      { name: 'Losers', count: losers.length, value: Math.abs(losers.reduce((sum, i) => sum + i.realized_pnl, 0)) },
    ]
  }, [pnlReport?.items])

  // Handle sort click
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  // Export to CSV
  const exportCSV = () => {
    if (!filteredItems.length) return

    const headers = ['Item', 'Bought', 'Sold', 'Inventory', 'Buy Value', 'Sell Value', 'Realized P&L', 'Margin %', 'ROI %']
    const rows = filteredItems.map(item => [
      item.type_name,
      item.total_bought,
      item.total_sold,
      item.current_inventory,
      item.total_buy_value.toFixed(2),
      item.total_sell_value.toFixed(2),
      item.realized_pnl.toFixed(2),
      item.margin_percent.toFixed(2),
      item.roi_percent.toFixed(2),
    ])

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pnl-report-${days}d.csv`
    a.click()
  }

  if (!characterId) {
    return (
      <div className="p-6">
        <Header title="P&L Analysis" subtitle="Select a character to view profit/loss analysis" />
      </div>
    )
  }

  // Chart data
  const chartData = portfolio?.snapshots.map(s => ({
    date: new Date(s.snapshot_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: s.total_liquid / 1_000_000_000,
  })) ?? []

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 opacity-50" />
    return sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Header
          title="P&L Analysis"
          subtitle="Detailed profit/loss breakdown by item"
          onRefresh={() => refetch()}
          isRefreshing={isFetching}
        />
        <div className="flex items-center gap-4">
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
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <PiggyBank className="h-4 w-4" />
              Total P&L
            </div>
            <div className={cn(
              "text-2xl font-bold",
              (pnlReport?.total_pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
            )}>
              {pnlReport ? formatISK(pnlReport.total_pnl) : '—'}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <TrendingUp className="h-4 w-4" />
              Realized
            </div>
            <div className="text-2xl font-bold text-green-500">
              {pnlReport ? formatISK(pnlReport.total_realized_pnl) : '—'}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Package className="h-4 w-4" />
              Unrealized
            </div>
            <div className="text-2xl font-bold text-amber-500">
              {pnlReport ? formatISK(pnlReport.total_unrealized_pnl) : '—'}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-emerald-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Trophy className="h-4 w-4" />
              Winners
            </div>
            <div className="text-2xl font-bold">
              {pnlReport?.top_winners.length ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Skull className="h-4 w-4" />
              Losers
            </div>
            <div className="text-2xl font-bold">
              {pnlReport?.top_losers.length ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Portfolio Trend</CardTitle>
            <CardDescription>{days}-day value history</CardDescription>
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
                No portfolio data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* P&L Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">P&L Distribution</CardTitle>
            <CardDescription>Winners vs Losers</CardDescription>
          </CardHeader>
          <CardContent>
            {pnlDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={pnlDistribution}>
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                  <YAxis stroke="#6b7280" fontSize={12} tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                    formatter={(value, name) => [formatISK(Number(value)), name === 'value' ? 'P&L' : 'Count']}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {pnlDistribution.map((_, index) => (
                      <Cell key={index} fill={index === 0 ? '#22c55e' : '#ef4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Filters and Actions */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Period Selection */}
        <div className="flex gap-1">
          {[7, 30, 90, 365].map((d) => (
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

        {/* Filter Type */}
        <div className="flex gap-1">
          <Button
            variant={filterType === 'all' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('all')}
          >
            <Filter className="h-3 w-3 mr-1" />
            All
          </Button>
          <Button
            variant={filterType === 'winners' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('winners')}
            className="text-green-500"
          >
            Winners
          </Button>
          <Button
            variant={filterType === 'losers' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('losers')}
            className="text-red-500"
          >
            Losers
          </Button>
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search items..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Export */}
        <Button variant="outline" size="sm" onClick={exportCSV}>
          <Download className="h-4 w-4 mr-1" />
          Export CSV
        </Button>
      </div>

      {/* Items Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Item P&L Breakdown</CardTitle>
          <CardDescription>
            {filteredItems.length} items | Click headers to sort
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground">Loading...</div>
          ) : filteredItems.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {searchTerm ? 'No items match your search' : 'No trading data available'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th
                      className="text-left py-3 px-2 text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                      onClick={() => handleSort('type_name')}
                    >
                      <div className="flex items-center gap-1">
                        Item <SortIcon field="type_name" />
                      </div>
                    </th>
                    <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                      Bought / Sold
                    </th>
                    <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                      Inventory
                    </th>
                    <th
                      className="text-right py-3 px-2 text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                      onClick={() => handleSort('realized_pnl')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        Realized P&L <SortIcon field="realized_pnl" />
                      </div>
                    </th>
                    <th
                      className="text-right py-3 px-2 text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                      onClick={() => handleSort('margin_percent')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        Margin <SortIcon field="margin_percent" />
                      </div>
                    </th>
                    <th
                      className="text-right py-3 px-2 text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                      onClick={() => handleSort('roi_percent')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        ROI <SortIcon field="roi_percent" />
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((item, idx) => (
                    <tr
                      key={item.type_id}
                      className={cn(
                        "border-b border-border/50 hover:bg-muted/50 transition-colors",
                        idx % 2 === 0 ? 'bg-transparent' : 'bg-muted/20'
                      )}
                    >
                      <td className="py-3 px-2">
                        <div className="flex items-center gap-2">
                          <div className={cn(
                            "w-2 h-2 rounded-full",
                            item.realized_pnl > 0 ? "bg-green-500" : item.realized_pnl < 0 ? "bg-red-500" : "bg-gray-500"
                          )} />
                          <span className="font-medium">{item.type_name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-2 text-right text-sm text-muted-foreground">
                        {item.total_bought.toLocaleString()} / {item.total_sold.toLocaleString()}
                      </td>
                      <td className="py-3 px-2 text-right text-sm">
                        {item.current_inventory > 0 ? (
                          <Badge variant="outline" className="text-amber-500 border-amber-500">
                            {item.current_inventory.toLocaleString()}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">0</span>
                        )}
                      </td>
                      <td className={cn(
                        "py-3 px-2 text-right font-medium",
                        item.realized_pnl > 0 ? "text-green-500" : item.realized_pnl < 0 ? "text-red-500" : "text-muted-foreground"
                      )}>
                        {item.realized_pnl > 0 ? '+' : ''}{formatISK(item.realized_pnl)}
                      </td>
                      <td className="py-3 px-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Percent className="h-3 w-3 text-muted-foreground" />
                          <span className={cn(
                            item.margin_percent > 0 ? "text-green-500" : item.margin_percent < 0 ? "text-red-500" : "text-muted-foreground"
                          )}>
                            {item.margin_percent.toFixed(1)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-2 text-right">
                        <span className={cn(
                          item.roi_percent > 0 ? "text-green-500" : item.roi_percent < 0 ? "text-red-500" : "text-muted-foreground"
                        )}>
                          {item.roi_percent > 0 ? '+' : ''}{item.roi_percent.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
