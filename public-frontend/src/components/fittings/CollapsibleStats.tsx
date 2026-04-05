import { useState } from 'react';
import type { FittingStats } from '../../types/fittings';
import { DAMAGE_COLORS } from '../../types/fittings';

interface CollapsibleStatsProps {
  stats: FittingStats | null;
  loading?: boolean;
  hasShip?: boolean;
}

// ────────────────────────────────────────────────────
// Helpers (reused from StatsPanel)
// ────────────────────────────────────────────────────

function fmt(n: number, decimals = 0): string {
  return n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtCompact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(2)}k`;
  return fmt(n);
}

function resistColor(pct: number): string {
  if (pct < 30) return '#f85149';
  if (pct < 50) return '#d29922';
  if (pct < 70) return '#00d4ff';
  return '#3fb950';
}

// ────────────────────────────────────────────────────
// Sub-components
// ────────────────────────────────────────────────────

function StatSection({ title, summary, summaryColor, defaultOpen, children }: {
  title: string;
  summary: string;
  summaryColor?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div style={{ borderBottom: '1px solid var(--border-color)' }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.5rem 0.75rem', cursor: 'pointer',
          background: open ? 'rgba(255,255,255,0.03)' : 'transparent',
        }}
      >
        <span style={{ fontSize: '0.7rem', width: 16 }}>{open ? '\u25BC' : '\u25B6'}</span>
        <span style={{ flex: 1, fontWeight: 600, fontSize: '0.8rem' }}>{title}</span>
        <span style={{ fontSize: '0.8rem', fontWeight: 500, color: summaryColor || 'var(--text-primary)' }}>
          {summary}
        </span>
      </div>
      {open && (
        <div style={{ padding: '0.25rem 0.75rem 0.5rem 2rem' }}>
          {children}
        </div>
      )}
    </div>
  );
}

function StatRow({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', fontSize: '0.75rem' }}>
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontFamily: 'monospace' }}>{value}{unit ? ` ${unit}` : ''}</span>
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
      background: `${color}${alpha}`, color: resistColor(pct),
      border: `1px solid ${color}44`,
    }}>
      {pct.toFixed(0)}%
    </div>
  );
}

function DamageBar({ breakdown }: { breakdown: { em: number; thermal: number; kinetic: number; explosive: number } }) {
  const total = breakdown.em + breakdown.thermal + breakdown.kinetic + breakdown.explosive;
  if (total === 0) return null;
  const segments = [
    { key: 'em', color: DAMAGE_COLORS.em, val: breakdown.em },
    { key: 'thermal', color: DAMAGE_COLORS.thermal, val: breakdown.thermal },
    { key: 'kinetic', color: DAMAGE_COLORS.kinetic, val: breakdown.kinetic },
    { key: 'explosive', color: DAMAGE_COLORS.explosive, val: breakdown.explosive },
  ].filter(s => s.val > 0);

  return (
    <div style={{ marginTop: '4px' }}>
      <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', gap: 1 }}>
        {segments.map(s => (
          <div key={s.key} style={{
            flex: s.val / total, background: s.color, minWidth: 2,
          }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '3px' }}>
        {segments.map(s => (
          <span key={s.key} style={{ fontSize: '0.6rem', color: s.color, display: 'flex', alignItems: 'center', gap: '2px' }}>
            <span style={{ width: 5, height: 5, borderRadius: 2, background: s.color, display: 'inline-block' }} />
            {fmt(s.val, 0)}
          </span>
        ))}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────
// Sections
// ────────────────────────────────────────────────────

function CapacitorSection({ stats }: { stats: FittingStats }) {
  const cap = stats.capacitor;
  const delta = (cap.peak_recharge_rate ?? 0) - (cap.usage_rate ?? 0);
  const rechargeS = cap.recharge_time ?? 0;  // already in seconds from backend
  const rechargeMin = Math.floor(rechargeS / 60);
  const rechargeSec = Math.floor(rechargeS % 60);

  const summary = cap.stable
    ? `${fmt(cap.capacity ?? 0, 1)} GJ / ${rechargeMin}m ${rechargeSec.toString().padStart(2, '0')}s`
    : `UNSTABLE ${cap.lasts_seconds > 0 ? `${Math.floor(cap.lasts_seconds / 60)}m ${Math.floor(cap.lasts_seconds % 60)}s` : ''}`;

  const summaryColor = cap.stable ? '#3fb950' : '#f85149';

  return (
    <StatSection title="Capacitor" summary={summary} summaryColor={summaryColor} defaultOpen>
      <StatRow label="\u0394 Rate" value={`${delta >= 0 ? '+' : ''}${delta.toFixed(1)} GJ/s (${fmt(cap.stable_percent ?? 0, 1)}%)`} />
      <StatRow label="Peak Recharge" value={fmt(cap.peak_recharge_rate ?? 0, 1)} unit="GJ/s" />
      <StatRow label="Drain Rate" value={fmt(cap.usage_rate ?? 0, 1)} unit="GJ/s" />
    </StatSection>
  );
}

function OffenseSection({ stats }: { stats: FittingStats }) {
  const off = stats.offense;
  const hasOverheat = off.overheated_total_dps != null && off.overheated_total_dps > 0 && off.overheated_total_dps !== off.total_dps;
  const summary = hasOverheat
    ? `${fmt(off.total_dps ?? 0, 1)} \u2192 ${fmt(off.overheated_total_dps!, 1)} DPS`
    : `${fmt(off.total_dps ?? 0, 1)} DPS`;
  const summaryColor = (off.total_dps ?? 0) > 0 ? '#f85149' : 'var(--text-tertiary)';

  return (
    <StatSection title="Offense" summary={summary} summaryColor={summaryColor} defaultOpen>
      <StatRow label="Total DPS" value={fmt(off.total_dps ?? 0, 1)} />
      {hasOverheat && (
        <StatRow label="Total DPS (OH)" value={fmt(off.overheated_total_dps!, 1)} />
      )}
      <StatRow label="Weapon DPS" value={fmt(off.weapon_dps ?? 0, 1)} />
      {off.overheated_weapon_dps != null && off.overheated_weapon_dps > 0 && off.overheated_weapon_dps !== off.weapon_dps && (
        <StatRow label="Weapon DPS (OH)" value={fmt(off.overheated_weapon_dps, 1)} />
      )}
      {stats.offense.spool && (
        <div style={{ paddingLeft: 12, marginTop: 2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            <span>Spool</span>
            <span style={{ fontFamily: 'monospace' }}>
              {fmt(stats.offense.spool.min_dps)} → {fmt(stats.offense.spool.max_dps)} DPS
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            <span>Avg / Time</span>
            <span style={{ fontFamily: 'monospace' }}>
              ~{fmt(stats.offense.spool.avg_dps)} DPS / {stats.offense.spool.time_to_max_s.toFixed(1)}s
            </span>
          </div>
        </div>
      )}
      <StatRow label="Drone DPS" value={fmt(off.drone_dps ?? 0, 1)} />
      {stats.offense.fighter_dps > 0 && (
        <StatRow label="Fighter DPS" value={fmt(stats.offense.fighter_dps, 1)} />
      )}
      {stats.offense.fighter_details && stats.offense.fighter_details.map((f: any, i: number) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', paddingLeft: 12, fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          <span>{f.type_name} x{f.squadrons}</span>
          <span style={{ fontFamily: 'monospace' }}>{fmt(f.total_dps)} DPS</span>
        </div>
      ))}
      <StatRow label="Alpha Strike" value={fmt(off.volley_damage ?? 0, 0)} />
      <DamageBar breakdown={off.damage_breakdown ?? { em: 0, thermal: 0, kinetic: 0, explosive: 0 }} />
    </StatSection>
  );
}

function AppliedDPSSection({ stats }: { stats: FittingStats }) {
  const applied = stats.applied_dps;
  if (!applied || applied.total_applied_dps <= 0) return null;

  const pctOfTotal = stats.offense.total_dps > 0
    ? ((applied.total_applied_dps / stats.offense.total_dps) * 100)
    : 0;
  const summary = `${fmt(applied.total_applied_dps, 1)} (${fmt(pctOfTotal, 0)}%)`;
  const summaryColor = pctOfTotal < 50 ? '#f85149' : pctOfTotal < 80 ? '#d29922' : '#3fb950';

  return (
    <StatSection title={`Applied (${applied.target_profile})`} summary={summary} summaryColor={summaryColor}>
      {applied.turret_applied_dps > 0 && (
        <StatRow label="Turrets" value={`${fmt(applied.turret_applied_dps, 1)} (${fmt(applied.turret_hit_chance * 100, 0)}% hit)`} />
      )}
      {applied.missile_applied_dps > 0 && (
        <StatRow label="Missiles" value={`${fmt(applied.missile_applied_dps, 1)} (${fmt(applied.missile_damage_factor * 100, 0)}% app)`} />
      )}
      {applied.drone_applied_dps > 0 && (
        <StatRow label="Drones" value={fmt(applied.drone_applied_dps, 1)} />
      )}
      {stats.applied_dps?.spool_applied && (
        <div style={{ paddingLeft: 12, marginTop: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            <span>Spool Applied</span>
            <span style={{ fontFamily: 'monospace' }}>
              {fmt(stats.applied_dps.spool_applied.min_dps)} → {fmt(stats.applied_dps.spool_applied.max_dps)} DPS
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            <span>Avg Applied</span>
            <span style={{ fontFamily: 'monospace' }}>
              ~{fmt(stats.applied_dps.spool_applied.avg_dps)} DPS
            </span>
          </div>
        </div>
      )}
    </StatSection>
  );
}

function DefenseSection({ stats }: { stats: FittingStats }) {
  const def = stats.defense;
  const rep = stats.repairs;
  const passiveRegen = rep?.shield_passive_regen ?? 0;
  const summary = passiveRegen > 0
    ? `${fmtCompact(def.total_ehp ?? 0)} EHP  ${fmt(passiveRegen, 0)} HP/s`
    : `${fmtCompact(def.total_ehp ?? 0)} EHP`;

  const layers = [
    { label: 'Shield', resists: def.shield_resists, hp: def.shield_hp ?? 0 },
    { label: 'Armor', resists: def.armor_resists, hp: def.armor_hp ?? 0 },
    { label: 'Hull', resists: def.hull_resists, hp: def.hull_hp ?? 0 },
  ];

  const totalRep = (rep?.shield_rep ?? 0) + (rep?.armor_rep ?? 0) + (rep?.hull_rep ?? 0);

  return (
    <StatSection title="Defense" summary={summary}>
      <StatRow label="Total EHP" value={fmtCompact(def.total_ehp ?? 0)} />

      {/* Resist table header */}
      <div style={{ display: 'flex', gap: '4px', marginTop: '6px', marginBottom: '3px', paddingLeft: '56px' }}>
        <div style={{ flex: 1, textAlign: 'center', fontSize: '0.6rem', color: DAMAGE_COLORS.em }}>EM</div>
        <div style={{ flex: 1, textAlign: 'center', fontSize: '0.6rem', color: DAMAGE_COLORS.thermal }}>Th</div>
        <div style={{ flex: 1, textAlign: 'center', fontSize: '0.6rem', color: DAMAGE_COLORS.kinetic }}>Ki</div>
        <div style={{ flex: 1, textAlign: 'center', fontSize: '0.6rem', color: DAMAGE_COLORS.explosive }}>Ex</div>
        <div style={{ width: '54px', textAlign: 'right', fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>HP</div>
      </div>

      {/* Resist rows */}
      {layers.map(layer => {
        const r = layer.resists ?? { em: 0, thermal: 0, kinetic: 0, explosive: 0 };
        return (
          <div key={layer.label} style={{ display: 'flex', gap: '4px', alignItems: 'center', marginBottom: '3px' }}>
            <span style={{ width: '52px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{layer.label}</span>
            <ResistCell value={r.em} color={DAMAGE_COLORS.em} />
            <ResistCell value={r.thermal} color={DAMAGE_COLORS.thermal} />
            <ResistCell value={r.kinetic} color={DAMAGE_COLORS.kinetic} />
            <ResistCell value={r.explosive} color={DAMAGE_COLORS.explosive} />
            <span style={{ width: '54px', textAlign: 'right', fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-primary)' }}>
              {fmtCompact(layer.hp)}
            </span>
          </div>
        );
      })}

      {/* Effective Repairs */}
      {totalRep > 0 && (
        <div style={{ marginTop: '6px', borderTop: '1px solid var(--border-color)', paddingTop: '4px' }}>
          {(rep?.sustained_tank_ehp ?? 0) > 0 && (
            <StatRow label="Sustained Tank" value={fmt(rep!.sustained_tank_ehp, 1)} unit="EHP/s" />
          )}
          {(rep?.shield_rep_ehp ?? 0) > 0 && <StatRow label="  Shield" value={fmt(rep!.shield_rep_ehp, 1)} unit="EHP/s" />}
          {(rep?.overheated_shield_rep ?? 0) > 0 && (
            <StatRow label="  Shield (OH)" value={fmt(rep!.overheated_shield_rep!, 1)} unit="HP/s" />
          )}
          {(rep?.sustained_shield_rep ?? 0) > 0 && (
            <StatRow label="  Sustained Shield" value={fmt(rep!.sustained_shield_rep!, 1)} unit="HP/s" />
          )}
          {(rep?.armor_rep_ehp ?? 0) > 0 && <StatRow label="  Armor" value={fmt(rep!.armor_rep_ehp, 1)} unit="EHP/s" />}
          {(rep?.overheated_armor_rep ?? 0) > 0 && (
            <StatRow label="  Armor (OH)" value={fmt(rep!.overheated_armor_rep!, 1)} unit="HP/s" />
          )}
          {(rep?.sustained_armor_rep ?? 0) > 0 && (
            <StatRow label="  Sustained Armor" value={fmt(rep!.sustained_armor_rep!, 1)} unit="HP/s" />
          )}
          {(rep?.hull_rep ?? 0) > 0 && <StatRow label="  Hull" value={fmt(rep!.hull_rep, 1)} unit="HP/s" />}
        </div>
      )}
      {(rep?.shield_passive_regen ?? 0) > 0 && (
        <div style={{ marginTop: '4px' }}>
          <StatRow label="Passive Shield Regen" value={fmt(rep!.shield_passive_regen, 1)} unit="HP/s" />
        </div>
      )}
    </StatSection>
  );
}

function TargetingSection({ stats }: { stats: FittingStats }) {
  const tgt = stats.targeting;
  const nav = stats.navigation;
  const rangeKm = (tgt.max_range ?? 0) / 1000;
  const summary = `${fmt(rangeKm, 2)} km`;

  return (
    <StatSection title="Targeting" summary={summary}>
      <StatRow label="Max Target Range" value={fmt(rangeKm, 2)} unit="km" />
      <StatRow label="Sensor Strength" value={`${fmt(tgt.sensor_strength ?? 0, 2)} points ${tgt.sensor_type || ''}`} />
      <StatRow label="Scan Resolution" value={fmt(tgt.scan_resolution ?? 0, 0)} unit="mm" />
      <StatRow label="Signature Radius" value={fmt(nav.signature_radius ?? 0, 0)} unit="m" />
      <StatRow label="Max Locked Targets" value={`${tgt.max_locked_targets ?? 0}x`} />
      {(tgt.lock_time ?? 0) > 0 && (
        <StatRow label="Lock Time" value={fmt(tgt.lock_time, 1)} unit="s" />
      )}
      {(tgt.scanability ?? 0) > 0 && (
        <StatRow label="Scanability" value={fmt(tgt.scanability, 2)} />
      )}
    </StatSection>
  );
}

function fmtMassTons(kg: number): string {
  const tons = kg / 1000;
  return tons.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function NavigationSection({ stats }: { stats: FittingStats }) {
  const nav = stats.navigation;
  const summary = `${fmt(nav.max_velocity ?? 0, 1)} m/s`;

  return (
    <StatSection title="Navigation" summary={summary}>
      <StatRow label="Max Speed" value={fmt(nav.max_velocity ?? 0, 1)} unit="m/s" />
      <StatRow label="Mass" value={fmtMassTons(nav.mass ?? 0)} unit="t" />
      <StatRow label="Inertia Modifier" value={`${fmt(nav.agility ?? 0, 4)}x`} />
      <StatRow label="Align Time" value={fmt(nav.align_time ?? 0, 2)} unit="s" />
      <StatRow label="Warp Speed" value={fmt(nav.warp_speed ?? 0, 2)} unit="AU/s" />
      {(nav.warp_time_5au ?? 0) > 0 && (
        <StatRow label="Warp 5 AU" value={fmt(nav.warp_time_5au, 1)} unit="s" />
      )}
      {(nav.warp_time_20au ?? 0) > 0 && (
        <StatRow label="Warp 20 AU" value={fmt(nav.warp_time_20au, 1)} unit="s" />
      )}
    </StatSection>
  );
}

function DronesSection({ stats }: { stats: FittingStats }) {
  const off = stats.offense;
  const res = stats.resources;
  const tgt = stats.targeting;
  const dps = off.drone_dps ?? 0;
  const bwUsed = res.drone_bandwidth_used ?? 0;
  const bwTotal = res.drone_bandwidth_total ?? 0;
  const summary = `${fmt(bwUsed, 0)}/${fmt(bwTotal, 0)} Mbit/sec`;
  const summaryColor = dps > 0 ? '#a855f7' : 'var(--text-tertiary)';

  return (
    <StatSection title="Drones" summary={summary} summaryColor={summaryColor}>
      <StatRow label="Drone DPS" value={fmt(dps, 1)} />
      <StatRow label="Bandwidth" value={`${fmt(bwUsed, 0)} / ${fmt(bwTotal, 0)}`} unit="Mbit/sec" />
      <StatRow label="Bay" value={`${fmt(res.drone_bay_used ?? 0, 0)} / ${fmt(res.drone_bay_total ?? 0, 0)}`} unit="m\u00B3" />
      {(tgt.drone_control_range ?? 0) > 0 && (
        <StatRow label="Control Range" value={fmt((tgt.drone_control_range ?? 0) / 1000, 2)} unit="km" />
      )}
    </StatSection>
  );
}

// ────────────────────────────────────────────────────
// Loading Shimmer
// ────────────────────────────────────────────────────

function ShimmerRow() {
  return (
    <div style={{
      height: 14, borderRadius: 3, marginBottom: 6,
      background: 'linear-gradient(90deg, var(--bg-tertiary) 25%, rgba(255,255,255,0.05) 50%, var(--bg-tertiary) 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
    }} />
  );
}

function LoadingSkeleton() {
  return (
    <>
      <style>{`@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
      {[...Array(6)].map((_, i) => (
        <div key={i} style={{ padding: '0.5rem 0.75rem', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <ShimmerRow />
          </div>
          {i < 2 && (
            <div style={{ paddingLeft: '2rem' }}>
              <ShimmerRow />
              <ShimmerRow />
              <ShimmerRow />
            </div>
          )}
        </div>
      ))}
    </>
  );
}

// ────────────────────────────────────────────────────
// Main Component
// ────────────────────────────────────────────────────

export function CollapsibleStats({ stats, loading, hasShip }: CollapsibleStatsProps) {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      overflow: 'hidden',
      height: '100%',
      overflowY: 'auto',
    }}>
      {loading && !stats ? (
        <LoadingSkeleton />
      ) : !stats ? (
        <div style={{
          padding: '2rem 1rem',
          textAlign: 'center',
          color: 'var(--text-secondary)',
          fontSize: '0.85rem',
        }}>
          {hasShip ? 'Add modules to see stats' : 'No ship selected'}
        </div>
      ) : (
        <>
          {stats.violations && stats.violations.length > 0 && (
            <div style={{
              padding: '0.5rem 0.75rem',
              background: 'rgba(248, 81, 73, 0.1)',
              borderBottom: '1px solid rgba(248, 81, 73, 0.3)',
            }}>
              {stats.violations.map((v, i) => {
                const label = v.resource === 'maxGroupFitted' ? 'Max Group'
                  : v.resource === 'maxTypeFitted' ? 'Max Type'
                  : v.resource === 'turret_hardpoints' ? 'Turret Hardpoints'
                  : v.resource === 'launcher_hardpoints' ? 'Launcher Hardpoints'
                  : v.resource.toUpperCase();
                return (
                  <div key={i} style={{ fontSize: '0.75rem', color: '#f85149', padding: '2px 0', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{label} exceeded</span>
                    <span style={{ fontFamily: 'monospace' }}>{v.used.toFixed(1)} / {v.total.toFixed(1)}</span>
                  </div>
                );
              })}
            </div>
          )}
          {stats.mode && (
            <div style={{
              padding: '4px 8px',
              marginBottom: 4,
              background: 'rgba(168, 85, 247, 0.1)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              borderRadius: 4,
              fontSize: '0.7rem',
              color: '#a855f7',
              textAlign: 'center',
            }}>
              {stats.mode.replace(/^.+\s-\s/, '')}
            </div>
          )}
          {stats.active_boosts && stats.active_boosts.length > 0 && (
            <div style={{
              padding: '4px 8px',
              marginBottom: 4,
              background: 'rgba(0, 212, 255, 0.08)',
              border: '1px solid rgba(0, 212, 255, 0.25)',
              borderRadius: 4,
              fontSize: '0.65rem',
            }}>
              <div style={{ color: '#00d4ff', marginBottom: 2, fontWeight: 600 }}>Fleet Boosts</div>
              {stats.active_boosts.map((b: any, i: number) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                  <span>{b.name}</span>
                  <span style={{ fontFamily: 'monospace' }}>{b.value > 0 ? '+' : ''}{b.value.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}
          <CapacitorSection stats={stats} />
          <OffenseSection stats={stats} />
          <AppliedDPSSection stats={stats} />
          <DefenseSection stats={stats} />
          <TargetingSection stats={stats} />
          <NavigationSection stats={stats} />
          <DronesSection stats={stats} />
          {stats.active_implants && stats.active_implants.filter((i: any) => i.slot >= 6).length > 0 && (
            <StatSection title="Active Implants" summary={`${stats.active_implants.filter((i: any) => i.slot >= 6).length} hardwiring(s)`} summaryColor="#a855f7">
              {stats.active_implants.filter((i: any) => i.slot >= 6).map((imp: any) => (
                <StatRow key={imp.type_id} label={`Slot ${imp.slot}`} value={imp.type_name} />
              ))}
            </StatSection>
          )}
          <div style={{
            padding: '0.5rem 0.75rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex', alignItems: 'center', gap: '0.4rem',
            fontSize: '0.65rem', color: 'var(--text-tertiary)',
          }}>
            <span style={{ fontSize: '0.7rem' }}>&#x2139;</span>
            <span>{stats.skill_source && stats.skill_source !== 'all_v'
              ? `Skills: ${stats.skill_source}`
              : 'All Skills Level V assumed'}</span>
          </div>
        </>
      )}
    </div>
  );
}
