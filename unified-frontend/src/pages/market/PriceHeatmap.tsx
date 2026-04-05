// unified-frontend/src/pages/market/PriceHeatmap.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { formatISK, cn } from '@/lib/utils'
import { Map } from 'lucide-react'

type ViewType = 'portfolio' | 'category'

// Common EVE categories for market items
const CATEGORIES = [
  { id: 4, name: 'Materials' },
  { id: 6, name: 'Ships' },
  { id: 7, name: 'Modules' },
  { id: 8, name: 'Charges' },
  { id: 18, name: 'Drones' },
  { id: 25, name: 'Implants' },
]

const TRADE_HUBS = ['Jita', 'Amarr', 'Dodixie', 'Rens', 'Hek']

export function PriceHeatmap() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id
  const [view, setView] = useState<ViewType>('portfolio')
  const [categoryId, setCategoryId] = useState<number>(4) // Materials

  // Portfolio heatmap - items from character's active orders
  const { data: portfolioData, isLoading: portfolioLoading, refetch: refetchPortfolio, isFetching: portfolioFetching } = useQuery({
    queryKey: ['heatmap-portfolio', characterId],
    queryFn: () => marketApi.getPortfolioHeatmap(characterId!, 20),
    enabled: !!characterId && view === 'portfolio',
  })

  // Category heatmap
  const { data: categoryData, isLoading: categoryLoading, refetch: refetchCategory, isFetching: categoryFetching } = useQuery({
    queryKey: ['heatmap-category', categoryId],
    queryFn: () => marketApi.getCategoryHeatmap(categoryId, 20),
    enabled: view === 'category',
  })

  const data = view === 'portfolio' ? portfolioData : categoryData
  const isLoading = view === 'portfolio' ? portfolioLoading : categoryLoading
  const isFetching = view === 'portfolio' ? portfolioFetching : categoryFetching
  const refetch = view === 'portfolio' ? refetchPortfolio : refetchCategory

  // Find min price for each item (for color coding)
  const getMinPrice = (prices: Record<string, number | null>) => {
    const values = Object.values(prices).filter((p): p is number => p !== null)
    return values.length > 0 ? Math.min(...values) : null
  }

  // Color coding based on price comparison
  const getPriceColor = (price: number | null, minPrice: number | null) => {
    if (price === null || minPrice === null) return 'text-muted-foreground'
    if (price === minPrice) return 'text-green-400 font-medium' // Best price
    const diff = ((price - minPrice) / minPrice) * 100
    if (diff <= 5) return 'text-yellow-400' // Close to best
    return 'text-red-400' // Expensive
  }

  return (
    <div className="p-6 space-y-6">
      <Header
        title="Price Heatmap"
        subtitle="Compare prices across trade hubs"
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
      />

      {/* View Toggle */}
      <div className="flex items-center gap-4">
        <div className="flex gap-2">
          <Button
            variant={view === 'portfolio' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setView('portfolio')}
            disabled={!characterId}
          >
            Portfolio Items
          </Button>
          <Button
            variant={view === 'category' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setView('category')}
          >
            By Category
          </Button>
        </div>

        {view === 'category' && (
          <div className="flex gap-2">
            {CATEGORIES.map((cat) => (
              <Button
                key={cat.id}
                variant={categoryId === cat.id ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setCategoryId(cat.id)}
              >
                {cat.name}
              </Button>
            ))}
          </div>
        )}
      </div>

      {/* Heatmap Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Map className="h-5 w-5" />
            {view === 'portfolio' ? 'Your Traded Items' : CATEGORIES.find(c => c.id === categoryId)?.name}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground">Loading prices...</div>
          ) : !data?.items.length ? (
            <div className="text-center py-12 text-muted-foreground">
              {view === 'portfolio' ? 'No active orders to compare' : 'No items found'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Item</th>
                    {TRADE_HUBS.map((hub) => (
                      <th key={hub} className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                        {hub}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => {
                    const minPrice = getMinPrice(item.prices)
                    return (
                      <tr key={item.type_id} className="border-b border-border/50 hover:bg-accent/50">
                        <td className="py-3 px-4 font-medium">{item.type_name}</td>
                        {TRADE_HUBS.map((hub) => {
                          const price = item.prices[hub]
                          return (
                            <td
                              key={hub}
                              className={cn(
                                "text-right py-3 px-4 text-sm",
                                getPriceColor(price, minPrice)
                              )}
                            >
                              {price !== null ? formatISK(price) : '—'}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex items-center gap-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-400 rounded"></div>
          Best Price
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-yellow-400 rounded"></div>
          Within 5%
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-400 rounded"></div>
          More Expensive
        </div>
      </div>
    </div>
  )
}
