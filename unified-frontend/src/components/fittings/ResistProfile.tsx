import { DAMAGE_COLORS, TANK_COLORS } from '@/types/fittings'
import type { DefenseStats, ResistProfile as ResistProfileType } from '@/types/fittings'

interface ResistProfileProps {
  defense: DefenseStats
}

function ResistBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-border/30 overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${Math.min(Math.max(value, 0), 100)}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <span className="text-xs font-mono w-10 text-right">{value.toFixed(0)}%</span>
    </div>
  )
}

function ResistRow({ label, resists, ehp, color }: {
  label: string
  resists: ResistProfileType
  ehp: number
  color: string
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
          <span className="text-xs font-medium">{label}</span>
        </div>
        <span className="text-xs font-mono text-muted-foreground">
          {ehp >= 1000 ? `${(ehp / 1000).toFixed(1)}k` : ehp.toFixed(0)} EHP
        </span>
      </div>
      <div className="grid grid-cols-4 gap-2">
        <div>
          <p className="text-[10px] text-muted-foreground mb-0.5" style={{ color: DAMAGE_COLORS.em }}>
            EM
          </p>
          <ResistBar value={resists.em} color={DAMAGE_COLORS.em} />
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground mb-0.5" style={{ color: DAMAGE_COLORS.thermal }}>
            Therm
          </p>
          <ResistBar value={resists.thermal} color={DAMAGE_COLORS.thermal} />
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground mb-0.5" style={{ color: DAMAGE_COLORS.kinetic }}>
            Kin
          </p>
          <ResistBar value={resists.kinetic} color={DAMAGE_COLORS.kinetic} />
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground mb-0.5" style={{ color: DAMAGE_COLORS.explosive }}>
            Exp
          </p>
          <ResistBar value={resists.explosive} color={DAMAGE_COLORS.explosive} />
        </div>
      </div>
    </div>
  )
}

export function ResistProfile({ defense }: ResistProfileProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-medium mb-4">Resist Profile</h3>

      <div className="space-y-4">
        <ResistRow
          label="Shield"
          resists={defense.shield_resists}
          ehp={defense.shield_ehp}
          color={TANK_COLORS.shield}
        />
        <ResistRow
          label="Armor"
          resists={defense.armor_resists}
          ehp={defense.armor_ehp}
          color={TANK_COLORS.armor}
        />
        <ResistRow
          label="Hull"
          resists={defense.hull_resists}
          ehp={defense.hull_ehp}
          color={TANK_COLORS.hull}
        />
      </div>

      {/* Total */}
      <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
        <span className="text-xs font-medium">Total EHP</span>
        <span className="text-sm font-bold font-mono">
          {defense.total_ehp >= 1000
            ? `${(defense.total_ehp / 1000).toFixed(1)}k`
            : defense.total_ehp.toFixed(0)}
        </span>
      </div>
    </div>
  )
}
