// unified-frontend/src/pages/market/Transactions.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import { ArrowDownLeft, ArrowUpRight, Calendar } from 'lucide-react'

type FilterType = 'all' | 'buys' | 'sells'

export function Transactions() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id
  const [filter, setFilter] = useState<FilterType>('all')

  const { data: transactions, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['transactions', characterId],
    queryFn: () => marketApi.getWalletTransactions(characterId!),
    enabled: !!characterId,
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Header title="Transactions" subtitle="Select a character to view transactions" />
      </div>
    )
  }

  const allTxns = transactions?.transactions ?? []
  const filteredTxns = allTxns.filter(txn => {
    if (filter === 'buys') return txn.is_buy
    if (filter === 'sells') return !txn.is_buy
    return true
  })

  // Group transactions by date
  const groupedByDate = filteredTxns.reduce((acc, txn) => {
    const date = new Date(txn.date).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    })
    if (!acc[date]) acc[date] = []
    acc[date].push(txn)
    return acc
  }, {} as Record<string, typeof filteredTxns>)

  const buyCount = allTxns.filter(t => t.is_buy).length
  const sellCount = allTxns.filter(t => !t.is_buy).length

  // Calculate totals
  const totalBought = allTxns
    .filter(t => t.is_buy)
    .reduce((sum, t) => sum + Math.abs(t.quantity * t.unit_price), 0)
  const totalSold = allTxns
    .filter(t => !t.is_buy)
    .reduce((sum, t) => sum + Math.abs(t.quantity * t.unit_price), 0)

  return (
    <div className="p-6 space-y-6">
      <Header
        title="Transactions"
        subtitle={`${allTxns.length} recent transactions`}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ArrowDownLeft className="h-5 w-5 text-red-400" />
                <span className="text-sm text-muted-foreground">Total Bought</span>
              </div>
              <div className="text-lg font-semibold text-red-400">
                -{formatISK(totalBought)}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ArrowUpRight className="h-5 w-5 text-green-400" />
                <span className="text-sm text-muted-foreground">Total Sold</span>
              </div>
              <div className="text-lg font-semibold text-green-400">
                +{formatISK(totalSold)}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All ({allTxns.length})
        </Button>
        <Button
          variant={filter === 'buys' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('buys')}
        >
          Buys ({buyCount})
        </Button>
        <Button
          variant={filter === 'sells' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('sells')}
        >
          Sells ({sellCount})
        </Button>
      </div>

      {/* Transactions List */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading transactions...</div>
      ) : Object.keys(groupedByDate).length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">No transactions found</div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedByDate).map(([date, txns]) => (
            <div key={date} className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                {date}
              </div>
              <div className="space-y-2">
                {txns.map((txn) => (
                  <Card key={txn.transaction_id}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {txn.is_buy ? (
                            <ArrowDownLeft className="h-5 w-5 text-red-400" />
                          ) : (
                            <ArrowUpRight className="h-5 w-5 text-green-400" />
                          )}
                          <div>
                            <div className="font-medium">{txn.type_name}</div>
                            <div className="text-sm text-muted-foreground">
                              {Math.abs(txn.quantity).toLocaleString()} @ {formatISK(txn.unit_price)}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={cn(
                            "font-medium",
                            txn.is_buy ? "text-red-400" : "text-green-400"
                          )}>
                            {txn.is_buy ? '-' : '+'}{formatISK(Math.abs(txn.quantity * txn.unit_price))}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {txn.location_name}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
