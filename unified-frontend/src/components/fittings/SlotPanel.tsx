import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { getModuleIconUrl } from '@/types/fittings'
import type { FittingItem } from '@/types/fittings'

interface SlotPanelProps {
  label: string
  items: FittingItem[]
  total: number
  color: string
}

export function SlotPanel({ label, items, total, color }: SlotPanelProps) {
  const used = items.length
  const empty = Math.max(0, total - used)

  // Collect unique type IDs for name resolution
  const typeIds = [...new Set(items.map((i) => i.type_id))]

  // Fetch type names via Dogma types/names endpoint
  const { data: typeNames = {} } = useQuery({
    queryKey: ['type-names', typeIds.sort().join(',')],
    queryFn: async () => {
      if (typeIds.length === 0) return {}
      const { data } = await apiClient.get<{ types: Record<string, string> }>(
        `/dogma/types/names`,
        { params: { ids: typeIds.join(',') } }
      )
      // Convert string keys to number keys
      const result: Record<number, string> = {}
      for (const [k, v] of Object.entries(data.types || {})) {
        result[Number(k)] = v
      }
      return result
    },
    staleTime: 60 * 60 * 1000, // 1 hour
    enabled: typeIds.length > 0,
  })

  // Group items by type_id for display
  const groupedItems = items.reduce<{ type_id: number; count: number }[]>((acc, item) => {
    const existing = acc.find((g) => g.type_id === item.type_id)
    if (existing) {
      existing.count += item.quantity
    } else {
      acc.push({ type_id: item.type_id, count: item.quantity })
    }
    return acc
  }, [])

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: color }}
          />
          {label}
        </h3>
        <span className="text-xs text-muted-foreground">
          {used}/{total}
        </span>
      </div>

      <div className="space-y-1.5">
        {groupedItems.map((item, i) => (
          <div
            key={`${item.type_id}-${i}`}
            className="flex items-center gap-2 py-1 px-2 rounded bg-background/50"
          >
            <img
              src={getModuleIconUrl(item.type_id)}
              alt=""
              className="h-6 w-6 rounded"
              loading="lazy"
            />
            <span className="text-xs flex-1 truncate">
              {typeNames[item.type_id] || `Type ${item.type_id}`}
            </span>
            {item.count > 1 && (
              <span className="text-xs text-muted-foreground">x{item.count}</span>
            )}
          </div>
        ))}

        {/* Empty slots */}
        {Array.from({ length: empty }).map((_, i) => (
          <div
            key={`empty-${i}`}
            className="flex items-center gap-2 py-1 px-2 rounded border border-dashed border-border/50"
          >
            <div className="h-6 w-6 rounded bg-border/20" />
            <span className="text-xs text-muted-foreground/50">Empty</span>
          </div>
        ))}
      </div>
    </div>
  )
}
