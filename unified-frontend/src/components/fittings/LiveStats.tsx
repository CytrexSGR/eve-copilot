import { useQuery } from '@tanstack/react-query'
import { getFittingStats } from '@/api/fittings'
import { DAMAGE_COLORS, TANK_COLORS } from '@/types/fittings'
import type { FittingItem, FittingStats } from '@/types/fittings'

interface LiveStatsProps {
  shipTypeId: number | null
  items: FittingItem[]
}

function ResourceBar({ used, total, color }: { used: number; total: number; color: string }) {
  const pct = total > 0 ? Math.min((used / total) * 100, 100) : 0
  const overloaded = used > total
  return (
    <div className="h-1.5 rounded-full bg-border/30 overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{
          width: `${Math.min(pct, 100)}%`,
          backgroundColor: overloaded ? '#f85149' : color,
        }}
      />
    </div>
  )
}

export function LiveStats({ shipTypeId, items }: LiveStatsProps) {
  const moduleItems = items.filter((i) => i.flag !== 5 && i.flag !== 87 && i.flag !== 158)

  const { data: stats, isFetching } = useQuery({
    queryKey: ['fitting-stats-live', shipTypeId, JSON.stringify(moduleItems)],
    queryFn: () => getFittingStats(shipTypeId!, moduleItems),
    enabled: !!shipTypeId && moduleItems.length > 0,
    staleTime: 30 * 1000,
  })

  if (!shipTypeId) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3">Live Stats</h3>
        <p className="text-xs text-muted-foreground text-center py-4">
          Select a ship to see stats
        </p>
      </div>
    )
  }

  if (moduleItems.length === 0 && !stats) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3">Live Stats</h3>
        <p className="text-xs text-muted-foreground text-center py-4">
          Add modules to see stats
        </p>
      </div>
    )
  }

  if (isFetching && !stats) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3">Live Stats</h3>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 animate-pulse rounded bg-border/20" />
          ))}
        </div>
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium">Live Stats</h3>
        {isFetching && (
          <span className="text-[10px] text-muted-foreground animate-pulse">updating...</span>
        )}
      </div>

      <div className="space-y-3">
        <StatRow stats={stats} />
        <ResourceRow stats={stats} />
        <TankRow stats={stats} />
      </div>
    </div>
  )
}

function StatRow({ stats }: { stats: FittingStats }) {
  const tankColor = stats.defense.tank_type.includes('shield')
    ? TANK_COLORS.shield
    : stats.defense.tank_type.includes('armor')
      ? TANK_COLORS.armor
      : TANK_COLORS.hull

  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="rounded-md bg-background/50 px-3 py-2">
        <p className="text-[10px] text-muted-foreground">DPS</p>
        <p className="text-lg font-bold font-mono">{stats.offense.total_dps.toFixed(0)}</p>
        {stats.offense.total_dps > 0 && (
          <div className="flex gap-0.5 mt-1">
            {Object.entries(stats.offense.damage_breakdown).map(([type, value]) => {
              if (value === 0) return null
              return (
                <div
                  key={type}
                  className="h-1 rounded-full flex-1"
                  style={{
                    backgroundColor: DAMAGE_COLORS[type as keyof typeof DAMAGE_COLORS],
                    opacity: value / stats.offense.total_dps,
                  }}
                />
              )
            })}
          </div>
        )}
      </div>
      <div className="rounded-md bg-background/50 px-3 py-2">
        <p className="text-[10px] text-muted-foreground">EHP</p>
        <p className="text-lg font-bold font-mono">
          {stats.defense.total_ehp >= 1000
            ? `${(stats.defense.total_ehp / 1000).toFixed(1)}k`
            : stats.defense.total_ehp.toFixed(0)}
        </p>
        <div className="flex items-center gap-1 mt-1">
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: tankColor }} />
          <span className="text-[10px] text-muted-foreground">
            {stats.defense.tank_type.replace('_', ' ')}
          </span>
        </div>
      </div>
    </div>
  )
}

function ResourceRow({ stats }: { stats: FittingStats }) {
  const pgPct = stats.resources.pg_total > 0
    ? (stats.resources.pg_used / stats.resources.pg_total) * 100
    : 0
  const cpuPct = stats.resources.cpu_total > 0
    ? (stats.resources.cpu_used / stats.resources.cpu_total) * 100
    : 0
  const pgOver = stats.resources.pg_used > stats.resources.pg_total
  const cpuOver = stats.resources.cpu_used > stats.resources.cpu_total

  return (
    <div className="space-y-2">
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-muted-foreground">Power Grid</span>
          <span className={`text-[10px] font-mono ${pgOver ? 'text-red-400' : 'text-muted-foreground'}`}>
            {stats.resources.pg_used.toFixed(0)}/{stats.resources.pg_total.toFixed(0)} ({pgPct.toFixed(0)}%)
          </span>
        </div>
        <ResourceBar used={stats.resources.pg_used} total={stats.resources.pg_total} color="#ff8800" />
      </div>
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-muted-foreground">CPU</span>
          <span className={`text-[10px] font-mono ${cpuOver ? 'text-red-400' : 'text-muted-foreground'}`}>
            {stats.resources.cpu_used.toFixed(0)}/{stats.resources.cpu_total.toFixed(0)} ({cpuPct.toFixed(0)}%)
          </span>
        </div>
        <ResourceBar used={stats.resources.cpu_used} total={stats.resources.cpu_total} color="#00d4ff" />
      </div>
    </div>
  )
}

function TankRow({ stats }: { stats: FittingStats }) {
  return (
    <div className="grid grid-cols-3 gap-2 pt-1 border-t border-border">
      <div>
        <p className="text-[10px] text-muted-foreground">Velocity</p>
        <p className="text-xs font-mono">{stats.navigation.max_velocity.toFixed(0)} m/s</p>
      </div>
      <div>
        <p className="text-[10px] text-muted-foreground">Agility</p>
        <p className="text-xs font-mono">{stats.navigation.agility.toFixed(2)}</p>
      </div>
      <div>
        <p className="text-[10px] text-muted-foreground">Sig Radius</p>
        <p className="text-xs font-mono">{stats.navigation.signature_radius.toFixed(0)} m</p>
      </div>
    </div>
  )
}
