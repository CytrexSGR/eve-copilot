import { useQuery } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { apiClient } from '@/api/client'
import { getModuleIconUrl } from '@/types/fittings'
import type { FittingItem, ShipDetail, SlotType } from '@/types/fittings'

interface SlotEditorProps {
  shipDetail: ShipDetail | null
  items: FittingItem[]
  activeSlot: { type: SlotType; flag: number } | null
  onSlotClick: (slotType: SlotType, flag: number) => void
  onRemoveModule: (flag: number) => void
}

const SLOT_CONFIG: { type: SlotType; label: string; color: string; startFlag: number; countKey: keyof ShipDetail }[] = [
  { type: 'high', label: 'High Slots', color: '#f85149', startFlag: 27, countKey: 'hi_slots' },
  { type: 'mid', label: 'Mid Slots', color: '#00d4ff', startFlag: 19, countKey: 'med_slots' },
  { type: 'low', label: 'Low Slots', color: '#ff8800', startFlag: 11, countKey: 'low_slots' },
  { type: 'rig', label: 'Rig Slots', color: '#a855f7', startFlag: 92, countKey: 'rig_slots' },
]

export function SlotEditor({ shipDetail, items, activeSlot, onSlotClick, onRemoveModule }: SlotEditorProps) {
  // Resolve type names for fitted modules
  const typeIds = [...new Set(items.map((i) => i.type_id))]
  const { data: typeNames = {} } = useQuery({
    queryKey: ['type-names', typeIds.sort().join(',')],
    queryFn: async () => {
      if (typeIds.length === 0) return {}
      const { data } = await apiClient.get<{ types: Record<string, string> }>(
        '/dogma/types/names',
        { params: { ids: typeIds.join(',') } }
      )
      const result: Record<number, string> = {}
      for (const [k, v] of Object.entries(data.types || {})) {
        result[Number(k)] = v
      }
      return result
    },
    staleTime: 60 * 60 * 1000,
    enabled: typeIds.length > 0,
  })

  if (!shipDetail) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card/50 p-8 text-center">
        <p className="text-sm text-muted-foreground">Select a ship to start fitting</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {SLOT_CONFIG.map((slot) => {
        const total = Number(shipDetail[slot.countKey]) || 0
        if (total === 0) return null

        const flags = Array.from({ length: total }, (_, i) => slot.startFlag + i)
        const filled = flags.map((flag) => ({
          flag,
          item: items.find((i) => i.flag === flag),
        }))
        const usedCount = filled.filter((f) => f.item).length

        return (
          <div key={slot.type} className="rounded-lg border border-border bg-card p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-medium flex items-center gap-1.5">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: slot.color }}
                />
                {slot.label}
              </h4>
              <span className="text-[10px] text-muted-foreground">
                {usedCount}/{total}
              </span>
            </div>

            <div className="space-y-1">
              {filled.map(({ flag, item }) => {
                const isActive = activeSlot?.flag === flag
                if (item) {
                  return (
                    <div
                      key={flag}
                      className="flex items-center gap-2 py-1 px-2 rounded bg-background/50 group"
                    >
                      <img
                        src={getModuleIconUrl(item.type_id)}
                        alt=""
                        className="h-6 w-6 rounded"
                      />
                      <span className="text-xs flex-1 truncate">
                        {typeNames[item.type_id] || `Type ${item.type_id}`}
                      </span>
                      <button
                        onClick={() => onRemoveModule(flag)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-red-500/20"
                        title="Remove module"
                      >
                        <X className="h-3 w-3 text-red-400" />
                      </button>
                    </div>
                  )
                }
                return (
                  <button
                    key={flag}
                    onClick={() => onSlotClick(slot.type, flag)}
                    className={`w-full flex items-center gap-2 py-1 px-2 rounded border transition-colors ${
                      isActive
                        ? 'border-primary/60 bg-primary/10'
                        : 'border-dashed border-border/50 hover:border-primary/30'
                    }`}
                  >
                    <div className="h-6 w-6 rounded bg-border/20 flex items-center justify-center">
                      <Plus className="h-3 w-3 text-muted-foreground" />
                    </div>
                    <span className="text-xs text-muted-foreground/50">
                      {isActive ? 'Select a module...' : 'Empty'}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
