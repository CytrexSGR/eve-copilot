import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn, formatISK, formatDuration } from '@/lib/utils'
import { getReactionById, getReactionProfitability } from '@/api/reactions'
import {
  FlaskConical,
  ArrowLeft,
  Clock,
  Coins,
  TrendingUp,
  Package,
  ArrowRight,
  Percent,
  Timer,
  MapPin,
} from 'lucide-react'
import { VerticalIntegrationCalculator } from '@/components/reactions/VerticalIntegrationCalculator'
import { ReactionChainDiagram } from '@/components/reactions/ReactionChainDiagram'

/**
 * Available regions for dropdown
 */
const REGIONS = [
  { id: 10000002, name: 'The Forge (Jita)' },
  { id: 10000043, name: 'Domain (Amarr)' },
  { id: 10000030, name: 'Heimatar (Rens)' },
  { id: 10000032, name: 'Sinq Laison (Dodixie)' },
]

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Get category badge style
 */
function getCategoryStyle(category: string | undefined) {
  switch (category?.toLowerCase()) {
    case 'simple':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    case 'complex':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    case 'composite':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30'
    case 'biochemical':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }
}

/**
 * Loading skeleton
 */
function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-32" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-48" />
      <Skeleton className="h-32" />
    </div>
  )
}

/**
 * Input material row
 */
function InputRow({
  inputTypeId,
  inputName,
  quantity,
}: {
  inputTypeId: number
  inputName: string
  quantity: number
}) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-border last:border-0">
      <img
        src={getItemIconUrl(inputTypeId)}
        alt={inputName}
        className="w-8 h-8 rounded-lg border border-border"
        loading="lazy"
        onError={(e) => {
          e.currentTarget.style.display = 'none'
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{inputName}</div>
      </div>
      <div className="text-right">
        <div className="font-mono text-sm">{quantity.toLocaleString()}</div>
        <div className="text-xs text-muted-foreground">units</div>
      </div>
    </div>
  )
}

/**
 * Profitability card component
 */
function ProfitCard({
  icon: Icon,
  label,
  value,
  subValue,
  color = 'text-foreground',
  iconBg = 'bg-secondary',
}: {
  icon: React.ElementType
  label: string
  value: string
  subValue?: string
  color?: string
  iconBg?: string
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg', iconBg)}>
            <Icon className={cn('h-5 w-5', color)} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className={cn('text-lg font-bold', color)}>{value}</div>
            {subValue && (
              <div className="text-xs text-muted-foreground">{subValue}</div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Main Reaction Detail page
 */
export function ReactionDetail() {
  const { reactionTypeId } = useParams<{ reactionTypeId: string }>()
  const [regionId, setRegionId] = useState<number>(10000002) // Default: Jita

  const reactionId = Number(reactionTypeId)

  // Fetch reaction formula details
  const {
    data: formula,
    isLoading: isLoadingFormula,
    isError: isErrorFormula,
  } = useQuery({
    queryKey: ['reaction', reactionId],
    queryFn: () => getReactionById(reactionId),
    enabled: reactionId > 0,
    staleTime: 5 * 60 * 1000,
  })

  // Fetch profitability data
  const {
    data: profitability,
    isLoading: isLoadingProfit,
    isError: isErrorProfit,
  } = useQuery({
    queryKey: ['reaction-profitability', reactionId, regionId],
    queryFn: () => getReactionProfitability(reactionId, regionId),
    enabled: reactionId > 0,
    staleTime: 2 * 60 * 1000,
  })

  const isLoading = isLoadingFormula || isLoadingProfit
  const isError = isErrorFormula || isErrorProfit

  // Invalid ID check
  if (!reactionTypeId || isNaN(reactionId)) {
    return (
      <div>
        <Header title="Reaction Detail" subtitle="Invalid reaction ID" />
        <div className="p-6">
          <Card>
            <CardContent className="py-12 text-center">
              <FlaskConical className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Invalid Reaction ID</h3>
              <p className="text-muted-foreground mb-4">
                The reaction ID provided is not valid.
              </p>
              <Link
                to="/reactions"
                className="inline-flex items-center gap-2 text-primary hover:underline"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Reactions
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  const isProfitable = profitability && profitability.profit_per_run > 0

  return (
    <div>
      <Header
        title={formula?.reaction_name || 'Reaction Detail'}
        subtitle={formula?.product_name || 'Loading...'}
      />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/reactions"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Reactions
        </Link>

        {isLoading ? (
          <DetailSkeleton />
        ) : isError || !formula ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FlaskConical className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Failed to Load Reaction</h3>
              <p className="text-muted-foreground">
                Could not fetch reaction details. Please try again.
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Reaction Header */}
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-start gap-4">
                  <img
                    src={getItemIconUrl(formula.product_type_id, 64)}
                    alt={formula.product_name}
                    className="w-16 h-16 rounded-lg border border-border"
                  />
                  <div className="flex-1">
                    <h2 className="text-xl font-bold">{formula.reaction_name}</h2>
                    <p className="text-muted-foreground">{formula.product_name}</p>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <Badge
                        variant="outline"
                        className={cn('text-xs', getCategoryStyle(formula.reaction_category))}
                      >
                        {formula.reaction_category || 'Unknown'}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        <Clock className="h-3 w-3 mr-1" />
                        {formatDuration(formula.reaction_time)}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        <Package className="h-3 w-3 mr-1" />
                        Output: {formula.product_quantity.toLocaleString()}
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Region Selector */}
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Market Region:</span>
                  </div>
                  <Select
                    value={String(regionId)}
                    onValueChange={(value) => setRegionId(Number(value))}
                  >
                    <SelectTrigger className="w-64">
                      <SelectValue placeholder="Select region" />
                    </SelectTrigger>
                    <SelectContent>
                      {REGIONS.map((region) => (
                        <SelectItem key={region.id} value={String(region.id)}>
                          {region.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Reaction Chain Diagram */}
            <ReactionChainDiagram
              reactionName={formula.reaction_name}
              inputs={formula.inputs}
              outputName={formula.product_name}
              outputQuantity={formula.product_quantity}
            />

            {/* Profitability Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <ProfitCard
                icon={TrendingUp}
                label="Profit per Run"
                value={profitability ? formatISK(profitability.profit_per_run) : 'Loading...'}
                color={isProfitable ? 'text-green-400' : 'text-red-400'}
                iconBg={isProfitable ? 'bg-green-500/20' : 'bg-red-500/20'}
              />
              <ProfitCard
                icon={Timer}
                label="Profit per Hour"
                value={profitability ? formatISK(profitability.profit_per_hour) : 'Loading...'}
                subValue={profitability ? `${profitability.runs_per_hour.toFixed(1)} runs/h` : undefined}
                color={isProfitable ? 'text-green-400' : 'text-red-400'}
                iconBg={isProfitable ? 'bg-green-500/20' : 'bg-red-500/20'}
              />
              <ProfitCard
                icon={Percent}
                label="ROI"
                value={profitability ? `${profitability.roi_percent.toFixed(1)}%` : 'Loading...'}
                color={isProfitable ? 'text-green-400' : 'text-red-400'}
                iconBg={isProfitable ? 'bg-green-500/20' : 'bg-red-500/20'}
              />
              <ProfitCard
                icon={Coins}
                label="Input Cost"
                value={profitability ? formatISK(profitability.input_cost) : 'Loading...'}
                color="text-yellow-400"
                iconBg="bg-yellow-500/20"
              />
            </div>

            {/* Inputs Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ArrowRight className="h-5 w-5 text-blue-400" />
                  Input Materials ({formula.inputs.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {formula.inputs.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">
                    No input materials found.
                  </p>
                ) : (
                  <div className="space-y-0">
                    {formula.inputs.map((input) => (
                      <InputRow
                        key={input.input_type_id}
                        inputTypeId={input.input_type_id}
                        inputName={input.input_name}
                        quantity={input.quantity}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Output Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="h-5 w-5 text-green-400" />
                  Output Product
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <img
                    src={getItemIconUrl(formula.product_type_id, 64)}
                    alt={formula.product_name}
                    className="w-16 h-16 rounded-lg border border-border"
                  />
                  <div className="flex-1">
                    <div className="font-bold text-lg">{formula.product_name}</div>
                    <div className="text-muted-foreground">
                      Quantity: {formula.product_quantity.toLocaleString()} units per run
                    </div>
                    {profitability && (
                      <div className="mt-2 text-sm">
                        <span className="text-muted-foreground">Value: </span>
                        <span className={isProfitable ? 'text-green-400' : 'text-red-400'}>
                          {formatISK(profitability.output_value)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Vertical Integration Calculator */}
            <VerticalIntegrationCalculator inputs={formula.inputs} />
          </>
        )}
      </div>
    </div>
  )
}

export default ReactionDetail
