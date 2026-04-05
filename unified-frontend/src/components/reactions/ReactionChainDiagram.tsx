import { cn } from '@/lib/utils'
import { FlaskConical, ArrowRight, Package } from 'lucide-react'
import type { ReactionInput } from '@/types/reactions'

/**
 * Props for the ReactionChainDiagram component
 */
interface Props {
  reactionName: string
  inputs: ReactionInput[]
  outputName: string
  outputQuantity: number
}

/**
 * Get item icon URL from EVE image server
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * ReactionChainDiagram Component
 *
 * Visual diagram showing the reaction flow:
 * - Inputs on the left (blue boxes)
 * - Arrow pointing to reaction in the middle (purple box with FlaskConical icon)
 * - Arrow pointing to output on the right (green box)
 */
export function ReactionChainDiagram({
  reactionName,
  inputs,
  outputName,
  outputQuantity,
}: Props) {
  return (
    <div className="flex items-center justify-center gap-4 p-6 bg-secondary/30 rounded-lg overflow-x-auto">
      {/* Inputs Column (Blue) */}
      <div className="flex flex-col gap-2 min-w-[160px]">
        {inputs.map((input) => (
          <div
            key={input.input_type_id}
            className={cn(
              'flex items-center gap-2 p-3 rounded-lg',
              'bg-blue-500/20 border border-blue-500/30',
              'text-blue-100'
            )}
          >
            <img
              src={getItemIconUrl(input.input_type_id)}
              alt={input.input_name}
              className="w-6 h-6 rounded border border-blue-500/30"
              loading="lazy"
              onError={(e) => {
                e.currentTarget.style.display = 'none'
              }}
            />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{input.input_name}</div>
              <div className="text-xs text-blue-300/70">
                {input.quantity.toLocaleString()} units
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Arrow to Reaction */}
      <div className="flex items-center px-2">
        <ArrowRight className="h-6 w-6 text-muted-foreground" />
      </div>

      {/* Reaction Box (Purple) */}
      <div
        className={cn(
          'flex flex-col items-center justify-center p-4 rounded-lg min-w-[180px]',
          'bg-purple-500/20 border border-purple-500/30',
          'text-purple-100'
        )}
      >
        <FlaskConical className="h-8 w-8 text-purple-400 mb-2" />
        <div className="text-sm font-medium text-center">{reactionName}</div>
      </div>

      {/* Arrow to Output */}
      <div className="flex items-center px-2">
        <ArrowRight className="h-6 w-6 text-muted-foreground" />
      </div>

      {/* Output Box (Green) */}
      <div
        className={cn(
          'flex items-center gap-3 p-4 rounded-lg min-w-[160px]',
          'bg-green-500/20 border border-green-500/30',
          'text-green-100'
        )}
      >
        <Package className="h-6 w-6 text-green-400" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{outputName}</div>
          <div className="text-xs text-green-300/70">
            {outputQuantity.toLocaleString()} units
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReactionChainDiagram
