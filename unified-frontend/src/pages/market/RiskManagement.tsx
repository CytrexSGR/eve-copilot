// unified-frontend/src/pages/market/RiskManagement.tsx

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Shield,
  AlertTriangle,
  TrendingUp,
  Droplets,
  PieChart,
  Lightbulb,
  Building2,
} from 'lucide-react'
import type { RiskSummary, ConcentrationRisk, LiquidityRisk } from '@/types/market'

const formatISK = (value: number): string => {
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B`
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toFixed(0)
}

const getRiskBadgeVariant = (level: string) => {
  switch (level) {
    case 'critical':
      return 'destructive'
    case 'high':
      return 'destructive'
    case 'medium':
      return 'default'
    default:
      return 'secondary'
  }
}

const getRiskColor = (level: string) => {
  switch (level) {
    case 'critical':
      return 'text-red-500'
    case 'high':
      return 'text-orange-500'
    case 'medium':
      return 'text-yellow-500'
    default:
      return 'text-green-500'
  }
}

function RiskScoreGauge({ score, label, inverted = false }: { score: number; label: string; inverted?: boolean }) {
  // If inverted, high score is good (e.g., liquidity). If not inverted, low score is good (e.g., concentration).
  const displayScore = inverted ? score : 100 - score
  const color = displayScore >= 70 ? 'bg-green-500' : displayScore >= 40 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{score.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full transition-all ${color}`}
          style={{ width: `${displayScore}%` }}
        />
      </div>
    </div>
  )
}

function ConcentrationCard({ risk }: { risk: ConcentrationRisk }) {
  return (
    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
      <div className="flex-1">
        <div className="font-medium text-sm">{risk.type_name}</div>
        <div className="text-xs text-muted-foreground">
          {formatISK(risk.value)} • {risk.order_count} order{risk.order_count !== 1 ? 's' : ''}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className={`text-sm font-bold ${getRiskColor(risk.risk_level)}`}>
          {risk.percent_of_portfolio.toFixed(1)}%
        </div>
        <Badge variant={getRiskBadgeVariant(risk.risk_level)}>
          {risk.risk_level}
        </Badge>
      </div>
    </div>
  )
}

function LiquidityCard({ risk }: { risk: LiquidityRisk }) {
  return (
    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
      <div className="flex-1">
        <div className="font-medium text-sm">{risk.type_name}</div>
        <div className="text-xs text-muted-foreground">
          Your: {risk.your_volume.toLocaleString()} • Market: {risk.market_daily_volume.toFixed(0)}/day
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className={`text-sm font-bold ${getRiskColor(risk.risk_level)}`}>
          {risk.days_to_sell !== null ? `${risk.days_to_sell.toFixed(1)}d` : 'N/A'}
        </div>
        <Badge variant={getRiskBadgeVariant(risk.risk_level)}>
          {risk.risk_level}
        </Badge>
      </div>
    </div>
  )
}

export default function RiskManagement() {
  const { selectedCharacter } = useCharacterContext()
  const [includeCorp, setIncludeCorp] = useState(true)

  const characterId = selectedCharacter?.character_id

  const { data, isLoading, error } = useQuery<RiskSummary>({
    queryKey: ['risk-summary', characterId, includeCorp],
    queryFn: () => marketApi.getRiskSummary(characterId!, { includeCorp }),
    enabled: !!characterId,
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Please select a character to view risk analysis.
          </CardContent>
        </Card>
      </div>
    )
  }

  const overallRiskIcon = () => {
    switch (data?.overall_risk_level) {
      case 'critical':
        return <AlertTriangle className="h-6 w-6 text-red-500" />
      case 'high':
        return <AlertTriangle className="h-6 w-6 text-orange-500" />
      case 'medium':
        return <Shield className="h-6 w-6 text-yellow-500" />
      default:
        return <Shield className="h-6 w-6 text-green-500" />
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Risk Management</h1>
            <p className="text-muted-foreground">
              Portfolio concentration and liquidity analysis
            </p>
          </div>
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

      {isLoading ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Analyzing portfolio risks...
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="p-6 text-center text-red-500">
            Error loading risk data: {(error as Error).message}
          </CardContent>
        </Card>
      ) : data ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Overall Risk */}
            <Card className={`border-l-4 ${
              data.overall_risk_level === 'critical' ? 'border-l-red-500' :
              data.overall_risk_level === 'high' ? 'border-l-orange-500' :
              data.overall_risk_level === 'medium' ? 'border-l-yellow-500' :
              'border-l-green-500'
            }`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  {overallRiskIcon()}
                  Overall Risk
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold capitalize ${getRiskColor(data.overall_risk_level)}`}>
                  {data.overall_risk_level}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {data.total_orders} orders tracked
                </div>
              </CardContent>
            </Card>

            {/* Portfolio Value */}
            <Card className="border-l-4 border-l-blue-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Portfolio Value
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-500">
                  {formatISK(data.total_portfolio_value)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Active sell orders
                </div>
              </CardContent>
            </Card>

            {/* Concentration Score */}
            <Card className="border-l-4 border-l-purple-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <PieChart className="h-4 w-4" />
                  Diversification
                </CardTitle>
              </CardHeader>
              <CardContent>
                <RiskScoreGauge
                  score={data.concentration_score}
                  label=""
                  inverted={false}
                />
                <div className="text-xs text-muted-foreground mt-1">
                  {data.concentration_score < 30 ? 'Well diversified' :
                   data.concentration_score < 60 ? 'Moderately concentrated' :
                   'Highly concentrated'}
                </div>
              </CardContent>
            </Card>

            {/* Liquidity Score */}
            <Card className="border-l-4 border-l-cyan-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Droplets className="h-4 w-4" />
                  Liquidity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <RiskScoreGauge
                  score={data.liquidity_score}
                  label=""
                  inverted={true}
                />
                <div className="text-xs text-muted-foreground mt-1">
                  {data.liquidity_score >= 70 ? 'Highly liquid' :
                   data.liquidity_score >= 40 ? 'Moderate liquidity' :
                   'Low liquidity'}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recommendations */}
          {data.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-yellow-500" />
                  Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.recommendations.map((rec, idx) => (
                    <div key={idx} className="p-3 bg-muted/50 rounded-lg text-sm">
                      {rec}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Risk Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Concentration Risks */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <PieChart className="h-5 w-5 text-purple-500" />
                  Concentration Risks
                </CardTitle>
                <CardDescription>
                  Items with high portfolio share (&gt;10%)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.top_concentration_risks.length > 0 ? (
                  <div className="space-y-2">
                    {data.top_concentration_risks.map((risk) => (
                      <ConcentrationCard key={risk.type_id} risk={risk} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No concentration risks detected. Portfolio is well diversified.
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Liquidity Risks */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Droplets className="h-5 w-5 text-cyan-500" />
                  Liquidity Risks
                </CardTitle>
                <CardDescription>
                  Items with slow sell rates (&gt;7 days)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.top_liquidity_risks.length > 0 ? (
                  <div className="space-y-2">
                    {data.top_liquidity_risks.map((risk) => (
                      <LiquidityCard key={risk.type_id} risk={risk} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No liquidity risks detected. All positions are liquid.
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
