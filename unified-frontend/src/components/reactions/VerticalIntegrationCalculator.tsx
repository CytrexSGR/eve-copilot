import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  ChevronRight,
  Calculator,
  TrendingUp,
  Package,
  Factory,
  ShoppingCart,
  Lightbulb,
} from 'lucide-react'
import type { ReactionInput } from '@/types/reactions'

/**
 * Props for the VerticalIntegrationCalculator component
 */
interface Props {
  inputs: ReactionInput[]
}

/**
 * Extended input with make/buy selection state
 */
interface InputWithSelection extends ReactionInput {
  selected: boolean
  estimatedSavings: number // Estimated savings percentage if made
}

/**
 * Default estimated savings percentage for making vs buying
 * This is a simplified estimate - real savings would require
 * additional API calls for actual prices
 */
const DEFAULT_SAVINGS_PERCENT = 20

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Determine if an input is likely makeable (has a reaction or manufacturing chain)
 * This is a heuristic based on common EVE naming patterns
 */
function isMakeable(inputName: string): boolean {
  const makeablePatterns = [
    /^Fuel Block/i,
    /Composite/i,
    /Polymer/i,
    /Ceramic/i,
    /Fulleride/i,
    /Ferrofluid/i,
    /Nanotransistor/i,
    /Titanium Chromide/i,
    /Crystallite Alloy/i,
    /Fernite Alloy/i,
    /Rolled Tungsten Alloy/i,
    /Titanium Carbide/i,
    /Tungsten Carbide/i,
    /Silicon Diborite/i,
    /Carbon Fiber/i,
    /Hexite/i,
    /Hyperflurite/i,
    /Neo Mercurite/i,
    /Dysporite/i,
    /Prometium/i,
    /Sulfuric Acid/i,
    /Silicates/i,
    /Platinum Technite/i,
  ]
  return makeablePatterns.some((pattern) => pattern.test(inputName))
}

/**
 * Get the recommendation text based on savings
 */
function getRecommendation(totalSavingsPercent: number): {
  text: string
  color: string
  bgColor: string
} {
  if (totalSavingsPercent >= 15) {
    return {
      text: 'MAKE - Strong vertical integration opportunity',
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
    }
  }
  if (totalSavingsPercent >= 5) {
    return {
      text: 'CONSIDER - Moderate savings possible',
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20',
    }
  }
  return {
    text: 'BUY - Vertical integration not recommended',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
  }
}

/**
 * Single input row with make/buy toggle
 */
function InputRowWithToggle({
  input,
  onToggle,
}: {
  input: InputWithSelection
  onToggle: (typeId: number) => void
}) {
  const makeable = isMakeable(input.input_name)

  return (
    <div className="flex items-center gap-3 py-3 border-b border-border last:border-0">
      {/* Checkbox for selecting */}
      <div className="flex items-center">
        <Checkbox
          checked={input.selected}
          onCheckedChange={() => onToggle(input.input_type_id)}
          disabled={!makeable}
          className={cn(!makeable && 'opacity-50 cursor-not-allowed')}
        />
      </div>

      {/* Item icon */}
      <img
        src={getItemIconUrl(input.input_type_id)}
        alt={input.input_name}
        className="w-8 h-8 rounded-lg border border-border"
        loading="lazy"
        onError={(e) => {
          e.currentTarget.style.display = 'none'
        }}
      />

      {/* Item info */}
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{input.input_name}</div>
        <div className="text-xs text-muted-foreground">
          {input.quantity.toLocaleString()} units
        </div>
      </div>

      {/* Make/Buy indicator */}
      <div className="flex items-center gap-2">
        {makeable ? (
          input.selected ? (
            <Badge
              variant="outline"
              className="bg-green-500/20 text-green-400 border-green-500/30"
            >
              <Factory className="h-3 w-3 mr-1" />
              MAKE
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="bg-blue-500/20 text-blue-400 border-blue-500/30"
            >
              <ShoppingCart className="h-3 w-3 mr-1" />
              BUY
            </Badge>
          )
        ) : (
          <Badge
            variant="outline"
            className="bg-gray-500/20 text-gray-400 border-gray-500/30"
          >
            <ShoppingCart className="h-3 w-3 mr-1" />
            BUY ONLY
          </Badge>
        )}
      </div>

      {/* Estimated savings (if makeable) */}
      {makeable && (
        <div className="text-right w-20">
          <div
            className={cn(
              'text-sm font-mono',
              input.selected ? 'text-green-400' : 'text-muted-foreground'
            )}
          >
            ~{input.estimatedSavings}%
          </div>
          <div className="text-xs text-muted-foreground">savings</div>
        </div>
      )}
    </div>
  )
}

/**
 * Summary stats card
 */
function SummaryCard({
  icon: Icon,
  label,
  value,
  color = 'text-foreground',
}: {
  icon: React.ElementType
  label: string
  value: string | number
  color?: string
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
      <Icon className={cn('h-5 w-5', color)} />
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className={cn('font-bold', color)}>{value}</div>
      </div>
    </div>
  )
}

/**
 * Vertical Integration Calculator Component
 *
 * Analyzes make vs buy decisions for reaction inputs.
 * Since we don't have actual prices from the ReactionInput type,
 * this serves as a planning tool with estimated savings.
 */
export function VerticalIntegrationCalculator({ inputs }: Props) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedInputs, setSelectedInputs] = useState<Set<number>>(new Set())

  // Create inputs with selection state
  const inputsWithSelection: InputWithSelection[] = useMemo(() => {
    return inputs.map((input) => ({
      ...input,
      selected: selectedInputs.has(input.input_type_id),
      estimatedSavings: isMakeable(input.input_name)
        ? DEFAULT_SAVINGS_PERCENT
        : 0,
    }))
  }, [inputs, selectedInputs])

  // Calculate summary stats
  const stats = useMemo(() => {
    const makeableInputs = inputsWithSelection.filter((i) =>
      isMakeable(i.input_name)
    )
    const selectedCount = inputsWithSelection.filter((i) => i.selected).length
    const makeableCount = makeableInputs.length
    const totalInputs = inputs.length

    // Calculate average savings for selected items
    const avgSavings =
      selectedCount > 0
        ? inputsWithSelection
            .filter((i) => i.selected)
            .reduce((sum, i) => sum + i.estimatedSavings, 0) / selectedCount
        : 0

    return {
      totalInputs,
      makeableCount,
      selectedCount,
      avgSavings,
    }
  }, [inputsWithSelection, inputs.length])

  // Toggle selection for an input
  const handleToggle = (typeId: number) => {
    setSelectedInputs((prev) => {
      const next = new Set(prev)
      if (next.has(typeId)) {
        next.delete(typeId)
      } else {
        next.add(typeId)
      }
      return next
    })
  }

  // Select all makeable inputs
  const selectAllMakeable = () => {
    const makeableIds = inputsWithSelection
      .filter((i) => isMakeable(i.input_name))
      .map((i) => i.input_type_id)
    setSelectedInputs(new Set(makeableIds))
  }

  // Clear all selections
  const clearAll = () => {
    setSelectedInputs(new Set())
  }

  const recommendation = getRecommendation(stats.avgSavings)

  // Don't render if no inputs
  if (inputs.length === 0) {
    return null
  }

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-3">
          <CollapsibleTrigger className="flex items-center justify-between w-full">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calculator className="h-5 w-5 text-purple-400" />
              Vertical Integration Analysis
              <Badge variant="secondary" className="ml-2 text-xs">
                {stats.makeableCount} makeable
              </Badge>
            </CardTitle>
            <ChevronRight
              className={cn(
                'h-5 w-5 text-muted-foreground transition-transform duration-200',
                isOpen && 'rotate-90'
              )}
            />
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <SummaryCard
                icon={Package}
                label="Total Inputs"
                value={stats.totalInputs}
              />
              <SummaryCard
                icon={Factory}
                label="Makeable"
                value={stats.makeableCount}
                color="text-blue-400"
              />
              <SummaryCard
                icon={TrendingUp}
                label="Selected to Make"
                value={stats.selectedCount}
                color="text-green-400"
              />
              <SummaryCard
                icon={Calculator}
                label="Est. Savings"
                value={`~${stats.avgSavings.toFixed(0)}%`}
                color={stats.avgSavings >= 10 ? 'text-green-400' : 'text-yellow-400'}
              />
            </div>

            {/* Recommendation Banner */}
            {stats.selectedCount > 0 && (
              <div
                className={cn(
                  'flex items-center gap-3 p-4 rounded-lg',
                  recommendation.bgColor
                )}
              >
                <Lightbulb className={cn('h-5 w-5', recommendation.color)} />
                <div>
                  <div className={cn('font-medium', recommendation.color)}>
                    {recommendation.text}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Based on {stats.selectedCount} selected input
                    {stats.selectedCount !== 1 ? 's' : ''} with estimated{' '}
                    {stats.avgSavings.toFixed(0)}% average savings
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={selectAllMakeable}
                className="text-sm px-3 py-1.5 rounded-md bg-secondary hover:bg-secondary/80 transition-colors"
              >
                Select All Makeable
              </button>
              <button
                onClick={clearAll}
                className="text-sm px-3 py-1.5 rounded-md bg-secondary hover:bg-secondary/80 transition-colors"
              >
                Clear All
              </button>
            </div>

            {/* Input List */}
            <div className="border border-border rounded-lg">
              <div className="p-3 border-b border-border bg-secondary/30">
                <div className="text-sm font-medium">Input Materials</div>
                <div className="text-xs text-muted-foreground">
                  Select inputs you want to produce yourself instead of buying
                </div>
              </div>
              <div className="p-2">
                {inputsWithSelection.map((input) => (
                  <InputRowWithToggle
                    key={input.input_type_id}
                    input={input}
                    onToggle={handleToggle}
                  />
                ))}
              </div>
            </div>

            {/* Disclaimer */}
            <div className="text-xs text-muted-foreground p-3 bg-secondary/30 rounded-lg">
              <strong>Note:</strong> Savings estimates are based on typical
              vertical integration margins (~{DEFAULT_SAVINGS_PERCENT}%).
              Actual savings depend on current market prices, your production
              capabilities, and material efficiency. Use this as a planning
              tool to identify integration opportunities.
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}

export default VerticalIntegrationCalculator
