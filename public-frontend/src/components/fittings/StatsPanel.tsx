import type { FittingStats } from '../../types/fittings';
import { DAMAGE_COLORS } from '../../types/fittings';

interface StatsPanelProps {
  stats: FittingStats | null;
  loading?: boolean;
}

// ────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────

function fmt(n: number, decimals = 0): string {
  return n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtCompact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(2)}k`;
  return fmt(n);
}

// ────────────────────────────────────────────────────
// Sub-components
// ────────────────────────────────────────────────────

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)',
      padding: '0.5rem 0', borderBottom: '1px solid var(--border-color)', marginBottom: '0.5rem',
    }}>
      {children}
    </div>
  );
}

function StatRow({ label, value, unit, icon, color }: {
  label: string; value: string; unit?: string; icon?: string; color?: string;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', padding: '3px 0', gap: '6px' }}>
      {icon && <span style={{ fontSize: '0.7rem', opacity: 0.5, width: 16, textAlign: 'center' }}>{icon}</span>}
      <span style={{ flex: 1, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 500, color: color || 'var(--text-primary)', whiteSpace: 'nowrap' }}>
        {value}
      </span>
      {unit && <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', minWidth: '30px' }}>{unit}</span>}
    </div>
  );
}

function ResourceRow({ label, used, available, unit, icon }: {
  label: string; used: number; available: number; unit: string; icon?: string;
}) {
  const overloaded = used > available;
  return (
    <div style={{ display: 'flex', alignItems: 'center', padding: '3px 0', gap: '6px' }}>
      {icon && <span style={{ fontSize: '0.85rem', opacity: 0.5, width: 16, textAlign: 'center' }}>{icon}</span>}
      <span style={{ flex: 1, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 500, color: overloaded ? '#f85149' : 'var(--text-primary)', whiteSpace: 'nowrap' }}>
        {fmt(used)}
      </span>
      <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>{unit}</span>
      <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-secondary)', whiteSpace: 'nowrap', minWidth: '70px', textAlign: 'right' }}>
        {fmt(available)}
      </span>
      <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>{unit}</span>
    </div>
  );
}

function ResistCell({ value, color }: { value: number; color: string }) {
  const pct = Math.max(0, Math.min(value, 100));
  const alpha = Math.round(pct * 2.55).toString(16).padStart(2, '0');
  return (
    <div style={{
      flex: 1, textAlign: 'center', fontSize: '0.7rem', fontWeight: 600,
      fontFamily: 'monospace', padding: '3px 4px', borderRadius: '3px',
      background: `${color}${alpha}`, color: 'var(--text-primary)',
      border: `1px solid ${color}44`,
    }}>
      {pct.toFixed(0)}%
    </div>
  );
}

// ────────────────────────────────────────────────────
// Section: Firepower
// ────────────────────────────────────────────────────

function FirepowerSection({ stats }: { stats: FittingStats }) {
  const { offense } = stats;
  return (
    <div>
      <SectionHeader>Firepower</SectionHeader>
      <div style={{ marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: offense.total_dps > 0 ? '#f85149' : 'var(--text-tertiary)' }}>
          {fmt(offense.total_dps, 1)}
        </span>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>total dps</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', fontSize: '0.75rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>Weapons</span>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{fmt(offense.weapon_dps, 1)}</span>
          <span style={{ color: 'var(--text-tertiary)', fontSize: '0.65rem' }}>dps</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', fontSize: '0.75rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>Drones</span>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{fmt(offense.drone_dps, 1)}</span>
          <span style={{ color: 'var(--text-tertiary)', fontSize: '0.65rem' }}>dps</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', fontSize: '0.75rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>Volley</span>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{fmt(offense.volley_damage, 0)}</span>
          <span style={{ color: 'var(--text-tertiary)', fontSize: '0.65rem' }}>dmg</span>
        </div>
      </div>
      {offense.total_dps > 0 && (
        <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
          {([
            { key: 'em' as const, color: DAMAGE_COLORS.em },
            { key: 'thermal' as const, color: DAMAGE_COLORS.thermal },
            { key: 'kinetic' as const, color: DAMAGE_COLORS.kinetic },
            { key: 'explosive' as const, color: DAMAGE_COLORS.explosive },
          ]).map(d => {
            const val = offense.damage_breakdown[d.key];
            if (val === 0) return null;
            return (
              <span key={d.key} style={{ fontSize: '0.6rem', color: d.color, display: 'flex', alignItems: 'center', gap: '3px' }}>
                <span style={{ width: 5, height: 5, borderRadius: 2, background: d.color, display: 'inline-block' }} />
                {fmt(val, 0)}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────
// Section: Applied DPS
// ────────────────────────────────────────────────────

function AppliedDPSSection({ stats }: { stats: FittingStats }) {
  const applied = stats.applied_dps;
  if (!applied || applied.total_applied_dps <= 0) return null;

  const pctOfTotal = stats.offense.total_dps > 0
    ? ((applied.total_applied_dps / stats.offense.total_dps) * 100)
    : 0;

  return (
    <div>
      <SectionHeader>Applied DPS ({applied.target_profile})</SectionHeader>
      <div style={{ marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1.3rem', fontWeight: 700, fontFamily: 'monospace', color: '#d29922' }}>
          {fmt(applied.total_applied_dps, 1)}
        </span>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginLeft: '6px' }}>
          ({fmt(pctOfTotal, 0)}% of {fmt(stats.offense.total_dps, 1)})
        </span>
      </div>
      {applied.turret_applied_dps > 0 && (
        <StatRow label="Turrets" value={fmt(applied.turret_applied_dps, 1)} unit="dps" icon="T"
          color={applied.turret_hit_chance < 0.5 ? '#f85149' : undefined} />
      )}
      {applied.turret_hit_chance > 0 && (
        <StatRow label="  Hit chance" value={fmt(applied.turret_hit_chance * 100, 1)} unit="%"
          color={applied.turret_hit_chance < 0.5 ? '#f85149' : applied.turret_hit_chance < 0.8 ? '#d29922' : '#3fb950'} />
      )}
      {applied.missile_applied_dps > 0 && (
        <StatRow label="Missiles" value={fmt(applied.missile_applied_dps, 1)} unit="dps" icon="M" />
      )}
      {applied.missile_damage_factor > 0 && (
        <StatRow label="  Application" value={fmt(applied.missile_damage_factor * 100, 1)} unit="%"
          color={applied.missile_damage_factor < 0.5 ? '#f85149' : applied.missile_damage_factor < 0.8 ? '#d29922' : '#3fb950'} />
      )}
      {applied.drone_applied_dps > 0 && (
        <StatRow label="Drones" value={fmt(applied.drone_applied_dps, 1)} unit="dps" icon={'\u{1F916}'} />
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────
// Section: Resource Usage
// ────────────────────────────────────────────────────

function ResourceUsageSection({ stats }: { stats: FittingStats }) {
  const { resources } = stats;
  return (
    <div>
      <SectionHeader>Resource usage</SectionHeader>
      <div style={{ display: 'flex', alignItems: 'center', padding: '3px 0', gap: '6px' }}>
        <span style={{ width: 16 }} />
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', fontWeight: 600 }}>used</span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', fontWeight: 600, minWidth: '70px', textAlign: 'right' }}>available</span>
        <span style={{ width: 20 }} />
      </div>
      <ResourceRow label="CPU" used={resources.cpu_used} available={resources.cpu_total} unit="tf" icon={'\u{1F4BB}'} />
      <ResourceRow label="Power Grid" used={resources.pg_used} available={resources.pg_total} unit="MW" icon={'\u26A1'} />
      {resources.turret_hardpoints_total > 0 && (
        <ResourceRow label="Turret Hardpoints" used={resources.turret_hardpoints_used} available={resources.turret_hardpoints_total} unit="" icon="T" />
      )}
      {resources.launcher_hardpoints_total > 0 && (
        <ResourceRow label="Launcher Hardpoints" used={resources.launcher_hardpoints_used} available={resources.launcher_hardpoints_total} unit="" icon="L" />
      )}
      <ResourceRow label="Drone Bay" used={resources.drone_bay_used} available={resources.drone_bay_total} unit="m3" icon={'\u{1F916}'} />
      <ResourceRow label="Drone Bandwidth" used={resources.drone_bandwidth_used} available={resources.drone_bandwidth_total} unit="mbit/s" icon={'\u{1F4E1}'} />
    </div>
  );
}

// ────────────────────────────────────────────────────
// Section: Resistance
// ────────────────────────────────────────────────────

function ResistanceSection({ stats }: { stats: FittingStats }) {
  const layers = [
    { icon: '\u{1F6E1}', label: 'Shield', resists: stats.defense.shield_resists, hp: stats.defense.shield_hp },
    { icon: '\u{1F530}', label: 'Armor', resists: stats.defense.armor_resists, hp: stats.defense.armor_hp },
    { icon: '\u2699', label: 'Hull', resists: stats.defense.hull_resists, hp: stats.defense.hull_hp },
  ];

  return (
    <div>
      <SectionHeader>Resistance</SectionHeader>
      {/* Column headers */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '4px', paddingLeft: '20px' }}>
        {[
          { label: '\u26A1', color: DAMAGE_COLORS.em },
          { label: '\u{1F525}', color: DAMAGE_COLORS.thermal },
          { label: '\u{1F4A5}', color: DAMAGE_COLORS.kinetic },
          { label: '\u{1F4A3}', color: DAMAGE_COLORS.explosive },
        ].map((d, i) => (
          <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: '0.65rem', color: d.color }}>
            {d.label}
          </div>
        ))}
        <div style={{ width: '70px' }} />
      </div>
      {/* Rows */}
      {layers.map(layer => (
        <div key={layer.label} style={{ display: 'flex', gap: '4px', alignItems: 'center', marginBottom: '4px' }}>
          <span style={{ width: 16, textAlign: 'center', fontSize: '0.7rem' }}>{layer.icon}</span>
          <ResistCell value={layer.resists.em} color={DAMAGE_COLORS.em} />
          <ResistCell value={layer.resists.thermal} color={DAMAGE_COLORS.thermal} />
          <ResistCell value={layer.resists.kinetic} color={DAMAGE_COLORS.kinetic} />
          <ResistCell value={layer.resists.explosive} color={DAMAGE_COLORS.explosive} />
          <span style={{ width: '70px', textAlign: 'right', fontSize: '0.7rem', fontFamily: 'monospace', fontWeight: 500, color: 'var(--text-primary)' }}>
            {fmtCompact(layer.hp)} <span style={{ color: 'var(--text-tertiary)', fontSize: '0.6rem' }}>HP</span>
          </span>
        </div>
      ))}
      {/* Total */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px', borderTop: '1px solid var(--border-color)' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
          Total: {fmtCompact(stats.defense.total_ehp)} <span style={{ color: 'var(--text-tertiary)', fontSize: '0.65rem' }}>ehp</span>
        </span>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────
// Section: Capacitor
// ────────────────────────────────────────────────────

function CapacitorSection({ stats }: { stats: FittingStats }) {
  const { capacitor } = stats;
  const delta = capacitor.peak_recharge_rate - capacitor.usage_rate;

  return (
    <div>
      <SectionHeader>Capacitor</SectionHeader>
      {/* Hero text */}
      <div style={{ textAlign: 'center', padding: '0.25rem 0 0.5rem 0' }}>
        {capacitor.stable ? (
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#3fb950' }}>STABLE</span>
        ) : (
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f85149' }}>
            UNSTABLE{' '}
            {capacitor.lasts_seconds > 0
              ? `${Math.floor(capacitor.lasts_seconds / 60)}m ${Math.floor(capacitor.lasts_seconds % 60)}s`
              : ''
            }
          </span>
        )}
      </div>
      <StatRow label="Capacity" value={fmt(capacitor.capacity, 0)} unit="GJ" icon={'\u{1F50B}'} />
      <StatRow label="Delta Percentage" value={fmt(capacitor.stable_percent, 1)} unit="%" icon={'\u{1F4CA}'} />
      <StatRow label="Delta" value={(delta >= 0 ? '+' : '') + delta.toFixed(1)} unit="GJ/s" icon={'\u{1F4C8}'}
        color={delta >= 0 ? '#3fb950' : '#f85149'} />
      <StatRow label="Recharge Rate" value={fmt(capacitor.recharge_time, 1)} unit="s" icon={'\u23F1'} />
    </div>
  );
}

// ────────────────────────────────────────────────────
// Section: Repairs
// ────────────────────────────────────────────────────

function RepairsSection({ stats }: { stats: FittingStats }) {
  const repairs = stats.repairs;
  if (!repairs) return null;
  const hasActiveRep = repairs.shield_rep > 0 || repairs.armor_rep > 0 || repairs.hull_rep > 0;
  const hasPassiveRegen = (repairs.shield_passive_regen ?? 0) > 0;
  const hasSustainedTank = (repairs.sustained_tank_ehp ?? 0) > 0;
  if (!hasActiveRep && !hasPassiveRegen) return null;

  return (
    <div>
      <SectionHeader>Repairs & Tank</SectionHeader>
      {hasSustainedTank && (
        <div style={{ marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'monospace', color: '#3fb950' }}>
            {fmt(repairs.sustained_tank_ehp, 1)}
          </span>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>sustained tank EHP/s</div>
        </div>
      )}
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'space-around' }}>
        {repairs.shield_rep > 0 && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>{'\u{1F6E1}'}</div>
            <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-primary)' }}>
              {fmt(repairs.shield_rep_ehp ?? repairs.shield_rep, 1)}
            </div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>EHP/s</div>
          </div>
        )}
        {repairs.armor_rep > 0 && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>{'\u{1F530}'}</div>
            <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-primary)' }}>
              {fmt(repairs.armor_rep_ehp ?? repairs.armor_rep, 1)}
            </div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>EHP/s</div>
          </div>
        )}
        {repairs.hull_rep > 0 && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>{'\u2699'}</div>
            <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-primary)' }}>
              {fmt(repairs.hull_rep, 1)}
            </div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>EHP/s</div>
          </div>
        )}
      </div>
      {hasPassiveRegen && (
        <StatRow label="Shield passive regen" value={fmt(repairs.shield_passive_regen, 1)} unit="HP/s" icon={'\u{1F504}'} />
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────
// Section: Targeting & Miscellaneous
// ────────────────────────────────────────────────────

function TargetingSection({ stats }: { stats: FittingStats }) {
  const { targeting, navigation } = stats;
  return (
    <div>
      <SectionHeader>Targeting & miscellaneous</SectionHeader>
      <StatRow label="Targets" value={String(targeting.max_locked_targets)} icon={'\u{1F3AF}'} />
      <StatRow label="Targeting range" value={fmt((targeting.max_range ?? 0) / 1000, 1)} unit="km" icon={'\u{1F4E1}'} />
      {(targeting.lock_time ?? 0) > 0 && (
        <StatRow label="Lock time" value={fmt(targeting.lock_time, 1)} unit="s" icon={'\u23F1'} />
      )}
      <StatRow label="Drone range" value={fmt((targeting.drone_control_range ?? 0) / 1000, 1)} unit="km" icon={'\u{1F916}'} />
      <StatRow label="Scan resolution" value={fmt(targeting.scan_resolution, 0)} unit="mm" icon={'\u{1F50D}'} />
      <StatRow label="Sensor strength" value={`${fmt(targeting.sensor_strength, 0)} ${targeting.sensor_type || ''}`} icon={'\u{1F4E1}'} />
      {(targeting.scanability ?? 0) > 0 && (
        <StatRow label="Scanability" value={fmt(targeting.scanability, 2)} icon={'\u{1F4E1}'} />
      )}
      <StatRow label="Signature radius" value={fmt(navigation.signature_radius, 0)} unit="m" icon={'\u25CE'} />
      <StatRow label="Speed" value={fmt(navigation.max_velocity, 0)} unit="m/s" icon={'\u25B6'} />
      <StatRow label="Warp Speed" value={fmt(navigation.warp_speed, 1)} unit="AU/s" icon={'\u226B'} />
      {(navigation.warp_time_5au ?? 0) > 0 && (
        <StatRow label="Warp 5 AU" value={fmt(navigation.warp_time_5au, 1)} unit="s" icon={'\u226B'} />
      )}
      {(navigation.warp_time_20au ?? 0) > 0 && (
        <StatRow label="Warp 20 AU" value={fmt(navigation.warp_time_20au, 1)} unit="s" icon={'\u226B'} />
      )}
      <StatRow label="Align time" value={fmt(navigation.align_time, 1)} unit="s" icon={'\u21BB'} />
      <StatRow label="Cargo" value={fmt(navigation.cargo_capacity ?? 0, 0)} unit="m3" icon={'\u{1F4E6}'} />
    </div>
  );
}

// ────────────────────────────────────────────────────
// Main Component
// ────────────────────────────────────────────────────

export function StatsPanel({ stats, loading }: StatsPanelProps) {
  if (!stats) {
    return (
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '2rem 1rem',
        textAlign: 'center',
        color: 'var(--text-secondary)',
        fontSize: '0.85rem',
      }}>
        {loading ? 'Calculating stats...' : 'Add modules to see stats'}
      </div>
    );
  }

  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
      borderRadius: '8px', padding: '1rem', fontSize: '0.75rem',
      display: 'flex', flexDirection: 'column', gap: '0.75rem',
      maxHeight: 'calc(100vh - 140px)', overflowY: 'auto',
    }}>
      <FirepowerSection stats={stats} />
      <AppliedDPSSection stats={stats} />
      <ResourceUsageSection stats={stats} />
      <ResistanceSection stats={stats} />
      <CapacitorSection stats={stats} />
      <RepairsSection stats={stats} />
      <TargetingSection stats={stats} />
      <div style={{
        padding: '0.5rem 0', marginTop: '0.25rem',
        borderTop: '1px solid var(--border-color)',
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        fontSize: '0.65rem', color: 'var(--text-tertiary)',
      }}>
        <span style={{ fontSize: '0.7rem' }}>&#x2139;</span>
        <span>{stats.skill_source && stats.skill_source !== 'all_v'
          ? `Skills: ${stats.skill_source}`
          : 'All Skills Level V assumed'}</span>
      </div>
    </div>
  );
}
