import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Plus } from 'lucide-react'
import { getModules } from '@/api/fittings'
import { getModuleIconUrl } from '@/types/fittings'
import type { SlotType, ModuleSummary } from '@/types/fittings'

interface ModulePickerProps {
  slotType: SlotType | null
  onSelectModule: (typeId: number) => void
}

const SLOT_LABELS: Record<SlotType, string> = {
  high: 'High Slot',
  mid: 'Mid Slot',
  low: 'Low Slot',
  rig: 'Rig Slot',
}

const SLOT_COLORS: Record<SlotType, string> = {
  high: '#f85149',
  mid: '#00d4ff',
  low: '#ff8800',
  rig: '#a855f7',
}

export function ModulePicker({ slotType, onSelectModule }: ModulePickerProps) {
  const [search, setSearch] = useState('')

  const { data: modules = [], isFetching } = useQuery({
    queryKey: ['sde-modules', slotType, search],
    queryFn: () =>
      getModules({
        slot_type: slotType || undefined,
        search: search || undefined,
        limit: 50,
      }),
    enabled: !!slotType,
    staleTime: 60 * 1000,
  })

  if (!slotType) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3">Module Browser</h3>
        <p className="text-xs text-muted-foreground text-center py-8">
          Click an empty slot to browse modules
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: SLOT_COLORS[slotType] }}
          />
          {SLOT_LABELS[slotType]} Modules
        </h3>
      </div>

      <div className="relative mb-3">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search modules..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 w-full rounded-md border border-border bg-background pl-8 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      <div className="max-h-[300px] overflow-y-auto space-y-0.5">
        {isFetching ? (
          <div className="py-6 text-xs text-muted-foreground text-center">Loading...</div>
        ) : modules.length === 0 ? (
          <div className="py-6 text-xs text-muted-foreground text-center">
            {search ? 'No modules found' : 'Type to search modules'}
          </div>
        ) : (
          modules.map((mod) => (
            <ModuleRow key={mod.type_id} module={mod} onClick={() => onSelectModule(mod.type_id)} />
          ))
        )}
      </div>
    </div>
  )
}

function ModuleRow({ module, onClick }: { module: ModuleSummary; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent transition-colors text-left group"
    >
      <img
        src={getModuleIconUrl(module.type_id)}
        alt=""
        className="h-6 w-6 rounded"
        loading="lazy"
      />
      <div className="flex-1 min-w-0">
        <p className="text-xs truncate">{module.type_name}</p>
        <p className="text-[10px] text-muted-foreground">{module.group_name}</p>
      </div>
      <div className="text-[10px] text-muted-foreground font-mono text-right shrink-0">
        {module.power > 0 && <span>{module.power} PG</span>}
        {module.power > 0 && module.cpu > 0 && <span> / </span>}
        {module.cpu > 0 && <span>{module.cpu} CPU</span>}
      </div>
      <Plus className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
    </button>
  )
}
