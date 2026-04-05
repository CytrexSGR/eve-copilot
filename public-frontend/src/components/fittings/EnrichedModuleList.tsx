import type { FittingStats, ModuleDetail } from '../../types/fittings';
import { SLOT_COLORS, getTypeIconUrl } from '../../types/fittings';

// ────────────────────────────────────────────────────
// Slot config
// ────────────────────────────────────────────────────

const SLOT_ORDER: { key: string; label: string; color: string; usedKey: string; totalKey: string }[] = [
  { key: 'high', label: 'HIGH', color: SLOT_COLORS.high, usedKey: 'hi_used', totalKey: 'hi_total' },
  { key: 'mid', label: 'MID', color: SLOT_COLORS.mid, usedKey: 'med_used', totalKey: 'med_total' },
  { key: 'low', label: 'LOW', color: SLOT_COLORS.low, usedKey: 'low_used', totalKey: 'low_total' },
  { key: 'rig', label: 'RIG', color: SLOT_COLORS.rig, usedKey: 'rig_used', totalKey: 'rig_total' },
  { key: 'drone', label: 'DRONE', color: '#a855f7', usedKey: '', totalKey: '' },
];

function fmt(n: number, d = 1): string {
  return n.toFixed(d);
}

// ────────────────────────────────────────────────────
// Module Row
// ────────────────────────────────────────────────────

function ModuleRow({ mod, color }: { mod: ModuleDetail; color: string }) {
  const isPassive = mod.cap_per_sec === 0;

  return (
    <>
      {/* Main row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '24px 1fr 52px 52px 56px',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 6px',
        borderRadius: '3px',
        transition: 'background 0.1s',
      }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        {/* Icon */}
        <img
          src={getTypeIconUrl(mod.type_id, 32)}
          alt=""
          style={{ width: 22, height: 22, borderRadius: 3 }}
        />

        {/* Name + quantity */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '4px',
          overflow: 'hidden', whiteSpace: 'nowrap',
        }}>
          {mod.quantity > 1 && (
            <span style={{
              fontSize: '0.65rem', fontWeight: 700, color,
              fontFamily: 'monospace', minWidth: '14px',
            }}>
              {mod.quantity}×
            </span>
          )}
          <span style={{
            fontSize: '0.72rem', color: '#58a6ff',
            overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {mod.type_name}
          </span>
          {mod.hardpoint_type && (
            <span style={{
              fontSize: '0.55rem', color: 'var(--text-tertiary)',
              fontFamily: 'monospace', flexShrink: 0,
            }}>
              {mod.hardpoint_type === 'turret' ? '◎' : '◆'}
            </span>
          )}
        </div>

        {/* CPU */}
        <span style={{
          fontSize: '0.68rem', fontFamily: 'monospace', color: 'var(--text-secondary)',
          textAlign: 'right',
        }}>
          {mod.cpu > 0 ? fmt(mod.cpu) : '—'}
        </span>

        {/* PG */}
        <span style={{
          fontSize: '0.68rem', fontFamily: 'monospace', color: 'var(--text-secondary)',
          textAlign: 'right',
        }}>
          {mod.pg > 0 ? fmt(mod.pg) : '—'}
        </span>

        {/* Cap/s */}
        <span style={{
          fontSize: '0.68rem', fontFamily: 'monospace',
          textAlign: 'right',
          color: isPassive ? 'var(--text-tertiary)' : mod.cap_per_sec > 10 ? '#f85149' : '#d29922',
        }}>
          {isPassive ? '—' : `${fmt(mod.cap_per_sec)}/s`}
        </span>
      </div>

      {/* Charge sub-row (indented) */}
      {mod.charge_name && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: '24px 1fr 52px 52px 56px',
          alignItems: 'center',
          gap: '4px',
          padding: '0 6px 1px 6px',
        }}>
          <div />
          <div style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            paddingLeft: '4px',
          }}>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>└</span>
            {mod.charge_type_id && (
              <img
                src={getTypeIconUrl(mod.charge_type_id, 32)}
                alt=""
                style={{ width: 16, height: 16, borderRadius: 2, opacity: 0.8 }}
              />
            )}
            <span style={{
              fontSize: '0.65rem', color: 'var(--text-tertiary)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {mod.charge_name}
            </span>
          </div>
          <div /><div /><div />
        </div>
      )}
    </>
  );
}

// ────────────────────────────────────────────────────
// Slot Group
// ────────────────────────────────────────────────────

function SlotGroup({ label, color, modules, used, total }: {
  label: string; color: string; modules: ModuleDetail[]; used: number; total: number;
}) {
  if (total === 0 && modules.length === 0) return null;

  // Group identical modules (same type_id) with summed quantity
  const grouped: ModuleDetail[] = [];
  const seen = new Map<number, number>(); // type_id → index in grouped
  for (const mod of modules) {
    const idx = seen.get(mod.type_id);
    if (idx !== undefined && !mod.charge_type_id) {
      // Same type without unique charge → merge quantity
      grouped[idx] = { ...grouped[idx], quantity: grouped[idx].quantity + mod.quantity };
    } else {
      seen.set(mod.type_id, grouped.length);
      grouped.push({ ...mod });
    }
  }

  return (
    <div style={{ marginBottom: '2px' }}>
      {/* Section header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '24px 1fr 52px 52px 56px',
        alignItems: 'center',
        gap: '4px',
        padding: '4px 6px 3px',
        borderBottom: `1px solid ${color}22`,
      }}>
        <div style={{
          width: 4, height: 14, borderRadius: 2, background: color,
        }} />
        <span style={{
          fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.06em',
          color: 'var(--text-primary)',
        }}>
          {label}
          {total > 0 && (
            <span style={{
              fontWeight: 400, fontSize: '0.65rem', color: 'var(--text-tertiary)',
              marginLeft: '6px', fontFamily: 'monospace',
            }}>
              {used}/{total}
            </span>
          )}
        </span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', textAlign: 'right', fontWeight: 600 }}>CPU</span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', textAlign: 'right', fontWeight: 600 }}>PG</span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', textAlign: 'right', fontWeight: 600 }}>CAP</span>
      </div>

      {/* Module rows */}
      {grouped.map((mod, i) => (
        <ModuleRow key={`${mod.type_id}-${mod.flag}-${i}`} mod={mod} color={color} />
      ))}

      {/* Empty slots */}
      {total > 0 && used < total && (
        <div style={{
          padding: '2px 6px 2px 34px',
          fontSize: '0.65rem', color: 'var(--text-tertiary)',
          fontStyle: 'italic', opacity: 0.5,
        }}>
          {total - used} empty
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────
// Main Component
// ────────────────────────────────────────────────────

interface EnrichedModuleListProps {
  stats: FittingStats;
}

export function EnrichedModuleList({ stats }: EnrichedModuleListProps) {
  const details = stats.module_details || [];
  if (details.length === 0) return null;

  // Group by slot_type
  const bySlot = new Map<string, ModuleDetail[]>();
  for (const mod of details) {
    const arr = bySlot.get(mod.slot_type) || [];
    arr.push(mod);
    bySlot.set(mod.slot_type, arr);
  }

  // Totals
  const totalCpu = details.filter(d => d.slot_type !== 'drone').reduce((s, d) => s + d.cpu * d.quantity, 0);
  const totalPg = details.filter(d => d.slot_type !== 'drone').reduce((s, d) => s + d.pg * d.quantity, 0);
  const totalCap = details.filter(d => d.slot_type !== 'drone').reduce((s, d) => s + d.cap_per_sec * d.quantity, 0);

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      {/* Slot groups */}
      {SLOT_ORDER.map(slot => {
        const mods = bySlot.get(slot.key) || [];
        const used = slot.usedKey ? (stats.slots as unknown as Record<string, number>)[slot.usedKey] ?? mods.length : mods.length;
        const total = slot.totalKey ? (stats.slots as unknown as Record<string, number>)[slot.totalKey] ?? 0 : 0;
        return (
          <SlotGroup
            key={slot.key}
            label={slot.label}
            color={slot.color}
            modules={mods}
            used={used}
            total={total}
          />
        );
      })}

      {/* Totals footer */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '24px 1fr 52px 52px 56px',
        alignItems: 'center',
        gap: '4px',
        padding: '5px 6px',
        borderTop: '1px solid var(--border-color)',
        background: 'rgba(255,255,255,0.02)',
      }}>
        <div />
        <span style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-secondary)' }}>TOTAL</span>
        <span style={{
          fontSize: '0.68rem', fontFamily: 'monospace', fontWeight: 600, textAlign: 'right',
          color: totalCpu > (stats.resources?.cpu_total ?? 0) ? '#f85149' : 'var(--text-primary)',
        }}>
          {fmt(totalCpu)}
        </span>
        <span style={{
          fontSize: '0.68rem', fontFamily: 'monospace', fontWeight: 600, textAlign: 'right',
          color: totalPg > (stats.resources?.pg_total ?? 0) ? '#f85149' : 'var(--text-primary)',
        }}>
          {fmt(totalPg)}
        </span>
        <span style={{
          fontSize: '0.68rem', fontFamily: 'monospace', fontWeight: 600, textAlign: 'right',
          color: '#d29922',
        }}>
          {fmt(totalCap)}/s
        </span>
      </div>
    </div>
  );
}
