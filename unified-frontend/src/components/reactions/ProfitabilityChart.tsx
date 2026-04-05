// unified-frontend/src/components/reactions/ProfitabilityChart.tsx

import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart3 } from 'lucide-react'
import { formatISK } from '@/lib/utils'
import type { ProfitableReaction } from '@/types/reactions'

interface Props {
  reactions: ProfitableReaction[]
  metric?: 'profit_per_hour' | 'roi_percent'
}

/**
 * Truncate reaction name if too long
 */
function truncateName(name: string, maxLength: number = 25): string {
  if (name.length <= maxLength) return name
  return name.substring(0, maxLength - 3) + '...'
}

/**
 * Format value based on metric type
 */
function formatValue(value: number, metric: 'profit_per_hour' | 'roi_percent'): string {
  if (metric === 'roi_percent') {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K%`
    }
    return `${value.toFixed(1)}%`
  }
  // Format ISK without the "ISK" suffix for chart axis
  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(1)}B`
  }
  if (value >= 1e6) {
    return `${(value / 1e6).toFixed(1)}M`
  }
  if (value >= 1e3) {
    return `${(value / 1e3).toFixed(1)}K`
  }
  return value.toFixed(0)
}

/**
 * Custom tooltip for the chart
 */
function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: ReadonlyArray<{ payload: ChartDataPoint }>
}) {
  if (!active || !payload || payload.length === 0) return null

  const data = payload[0].payload

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-3 shadow-lg">
      <div className="font-medium text-[#e6edf3] mb-2">{data.fullName}</div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-[#8b949e]">Profit/Hour:</span>
          <span className={data.profit_per_hour >= 0 ? 'text-green-400' : 'text-red-400'}>
            {formatISK(data.profit_per_hour)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-[#8b949e]">ROI:</span>
          <span className={data.roi_percent >= 0 ? 'text-green-400' : 'text-red-400'}>
            {data.roi_percent >= 1000
              ? `${(data.roi_percent / 1000).toFixed(1)}K%`
              : `${data.roi_percent.toFixed(1)}%`}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-[#8b949e]">Profit/Run:</span>
          <span className={data.profit_per_run >= 0 ? 'text-green-400' : 'text-red-400'}>
            {formatISK(data.profit_per_run)}
          </span>
        </div>
      </div>
    </div>
  )
}

interface ChartDataPoint {
  name: string
  fullName: string
  value: number
  profit_per_hour: number
  profit_per_run: number
  roi_percent: number
  isPositive: boolean
}

/**
 * Horizontal bar chart showing top 10 profitable reactions
 */
export function ProfitabilityChart({ reactions, metric = 'profit_per_hour' }: Props) {
  // Memoize chart data transformation
  const chartData = useMemo<ChartDataPoint[]>(() => {
    const top10 = reactions.slice(0, 10)
    return top10.map((reaction) => ({
      name: truncateName(reaction.reaction_name),
      fullName: reaction.reaction_name,
      value: metric === 'profit_per_hour' ? reaction.profit_per_hour : reaction.roi_percent,
      profit_per_hour: reaction.profit_per_hour,
      profit_per_run: reaction.profit_per_run,
      roi_percent: reaction.roi_percent,
      isPositive: reaction[metric] >= 0,
    }))
  }, [reactions, metric])

  // Reverse for vertical bar chart (top item at top) - memoized
  const reversedData = useMemo(() => [...chartData].reverse(), [chartData])

  const metricLabel = metric === 'profit_per_hour' ? 'Profit/Hour' : 'ROI %'

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Top 10 by {metricLabel}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={reversedData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#30363d"
                horizontal={true}
                vertical={false}
              />
              <XAxis
                type="number"
                stroke="#8b949e"
                fontSize={12}
                tickFormatter={(value) => formatValue(value, metric)}
                axisLine={{ stroke: '#30363d' }}
                tickLine={{ stroke: '#30363d' }}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#8b949e"
                fontSize={11}
                width={150}
                axisLine={{ stroke: '#30363d' }}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload }) => (
                  <CustomTooltip active={active} payload={payload} />
                )}
                cursor={{ fill: 'rgba(88, 166, 255, 0.1)' }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={30}>
                {reversedData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.isPositive ? '#3fb950' : '#f85149'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 text-xs text-muted-foreground text-center">
          Hover over bars for detailed information
        </div>
      </CardContent>
    </Card>
  )
}

export default ProfitabilityChart
