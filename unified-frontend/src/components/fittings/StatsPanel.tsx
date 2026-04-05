import { DAMAGE_COLORS, TANK_COLORS } from '@/types/fittings'
import type { FittingStats } from '@/types/fittings'

interface StatsPanelProps {
  stats: FittingStats
}

function ResourceBar({ label, used, total, color }: {
  label: string
  used: number
  total: number
  color: string
}) {
  const pct = total > 0 ? Math.min((used / total) * 100, 100) : 0
  const overloaded = used > total

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className={`text-xs font-mono ${overloaded ? 'text-red-400' : ''}`}>
          {used.toFixed(0)}/{total.toFixed(0)}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-border/30 overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${Math.min(pct, 100)}%`,
            backgroundColor: overloaded ? '#f85149' : color,
          }}
        />
      </div>
    </div>
  )
}

export function StatsPanel({ stats }: StatsPanelProps) {
  const tankColor = stats.defense.tank_type.includes('shield')
    ? TANK_COLORS.shield
    : stats.defense.tank_type.includes('armor')
      ? TANK_COLORS.armor
      : TANK_COLORS.hull

  const tankLabel = stats.defense.tank_type.includes('shield')
    ? 'Shield'
    : stats.defense.tank_type.includes('armor')
      ? 'Armor'
      : stats.defense.tank_type === 'unknown'
        ? 'Mixed'
        : 'Hull'

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {/* DPS */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground mb-1">DPS</p>
        <p className="text-2xl font-bold font-mono">
          {stats.offense.total_dps.toFixed(0)}
        </p>
        {stats.offense.total_dps > 0 && (
          <div className="flex gap-1 mt-2">
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
                  title={`${type}: ${value.toFixed(0)}`}
                />
              )
            })}
          </div>
        )}
      </div>

      {/* EHP */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground mb-1">EHP</p>
        <p className="text-2xl font-bold font-mono">
          {stats.defense.total_ehp >= 1000
            ? `${(stats.defense.total_ehp / 1000).toFixed(1)}k`
            : stats.defense.total_ehp.toFixed(0)}
        </p>
        <div className="flex items-center gap-1.5 mt-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: tankColor }}
          />
          <span className="text-xs text-muted-foreground">{tankLabel} Tank</span>
        </div>
      </div>

      {/* PG */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground mb-2">Power Grid</p>
        <ResourceBar
          label=""
          used={stats.resources.pg_used}
          total={stats.resources.pg_total}
          color="#ff8800"
        />
        <p className="text-xs text-muted-foreground mt-1.5">
          {stats.resources.pg_total > 0
            ? `${((stats.resources.pg_used / stats.resources.pg_total) * 100).toFixed(0)}%`
            : '0%'}
        </p>
      </div>

      {/* CPU */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground mb-2">CPU</p>
        <ResourceBar
          label=""
          used={stats.resources.cpu_used}
          total={stats.resources.cpu_total}
          color="#00d4ff"
        />
        <p className="text-xs text-muted-foreground mt-1.5">
          {stats.resources.cpu_total > 0
            ? `${((stats.resources.cpu_used / stats.resources.cpu_total) * 100).toFixed(0)}%`
            : '0%'}
        </p>
      </div>
    </div>
  )
}
