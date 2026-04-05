// unified-frontend/src/components/market/CapitalAllocator.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import { Calculator } from 'lucide-react'
import type { AllocationRequest, ItemAllocation } from '@/types/market'

interface CapitalAllocatorProps {
  primaryIndex?: string
  subIndices?: string[]
}

function getRiskColor(score: number) {
  if (score <= 20) return 'text-green-400'
  if (score <= 40) return 'text-blue-400'
  if (score <= 60) return 'text-yellow-400'
  return 'text-red-400'
}

export function CapitalAllocator({ primaryIndex, subIndices }: CapitalAllocatorProps) {
  const [budget, setBudget] = useState('')
  const [strategy, setStrategy] = useState<'max_profit' | 'balanced' | 'min_risk'>('balanced')
  const [maxPerItem, setMaxPerItem] = useState('')
  const [maxDays, setMaxDays] = useState('')
  const [shouldFetch, setShouldFetch] = useState(false)

  const request: AllocationRequest = {
    budget: parseInt(budget) || 0,
    strategy,
    max_per_item: maxPerItem ? parseInt(maxPerItem) : undefined,
    max_days_to_sell: maxDays ? parseFloat(maxDays) : undefined,
    primary_index: primaryIndex,
    sub_indices: subIndices,
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['allocate', request],
    queryFn: () => marketApi.allocateCapital(request),
    enabled: shouldFetch && request.budget >= 10000000,
  })

  const handleCalculate = () => {
    if (parseInt(budget) >= 10000000) {
      setShouldFetch(true)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calculator className="h-5 w-5" />
          Capital Allocator
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Inputs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-muted-foreground mb-1">Available Capital (ISK)</div>
            <Input
              type="number"
              placeholder="1,000,000,000"
              value={budget}
              onChange={e => { setBudget(e.target.value); setShouldFetch(false) }}
            />
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Strategy</div>
            <Select value={strategy} onValueChange={(v: 'max_profit' | 'balanced' | 'min_risk') => { setStrategy(v); setShouldFetch(false) }}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="max_profit">Max Profit</SelectItem>
                <SelectItem value="balanced">Balanced</SelectItem>
                <SelectItem value="min_risk">Min Risk</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Max per Item</div>
            <Input
              type="number"
              placeholder="Auto"
              value={maxPerItem}
              onChange={e => { setMaxPerItem(e.target.value); setShouldFetch(false) }}
            />
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Max Days to Sell</div>
            <Input
              type="number"
              placeholder="Any"
              value={maxDays}
              onChange={e => { setMaxDays(e.target.value); setShouldFetch(false) }}
            />
          </div>
        </div>

        <Button onClick={handleCalculate} disabled={!budget || parseInt(budget) < 10000000 || isFetching}>
          {isFetching ? 'Calculating...' : 'Calculate Optimal Allocation'}
        </Button>

        {/* Results */}
        {isLoading && shouldFetch && (
          <div className="space-y-2">
            <Skeleton className="h-20" />
            <Skeleton className="h-40" />
          </div>
        )}

        {data && (
          <>
            {/* Summary */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 p-4 bg-muted/50 rounded-lg">
              <div>
                <div className="text-xs text-muted-foreground">Invested</div>
                <div className="font-mono font-bold">{formatISK(data.total_invested)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Expected/Day</div>
                <div className="font-mono font-bold text-green-400">{formatISK(data.expected_daily_profit)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Avg Days to Sell</div>
                <div className="font-mono font-bold">{data.average_days_to_sell.toFixed(1)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Avg Risk</div>
                <div className={cn('font-mono font-bold', getRiskColor(data.average_risk_score))}>
                  {data.average_risk_score.toFixed(0)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Reserve</div>
                <div className="font-mono">{formatISK(data.reserve)}</div>
              </div>
            </div>

            {/* Allocations Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-2">Item</th>
                    <th className="text-right p-2">Investment</th>
                    <th className="text-right p-2">Units</th>
                    <th className="text-right p-2">Profit/Day</th>
                    <th className="text-right p-2">Days</th>
                    <th className="text-right p-2">Risk</th>
                    <th className="text-right p-2">Alloc %</th>
                  </tr>
                </thead>
                <tbody>
                  {data.allocations.map((alloc: ItemAllocation) => (
                    <tr key={alloc.type_id} className="border-t border-border">
                      <td className="p-2 font-medium">{alloc.type_name}</td>
                      <td className="text-right p-2 font-mono">{formatISK(alloc.investment)}</td>
                      <td className="text-right p-2 font-mono">{alloc.units.toLocaleString()}</td>
                      <td className="text-right p-2 font-mono text-green-400">{formatISK(alloc.expected_profit_per_day)}</td>
                      <td className="text-right p-2 font-mono">{alloc.days_to_sell?.toFixed(1) ?? '-'}</td>
                      <td className={cn('text-right p-2', getRiskColor(alloc.risk_score))}>{alloc.risk_score}</td>
                      <td className="text-right p-2">
                        <div className="flex items-center justify-end gap-1">
                          <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-primary" style={{ width: `${alloc.allocation_percent}%` }} />
                          </div>
                          <span className="text-xs w-10">{alloc.allocation_percent}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default CapitalAllocator
