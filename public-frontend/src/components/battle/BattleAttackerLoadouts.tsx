import { useState } from 'react';
import { formatISKCompact } from '../../utils/format';

interface LoadoutEntry {
  ship_name: string;
  ship_class: string;
  weapon_name: string | null;
  weapon_class: string | null;
  range: string;
  damage_type: string | null;
  pilot_count: number;
  engagements: number;
  total_damage: number;
}

interface FleetSize {
  avg: number | null;
  median: number | null;
  max: number | null;
  kills_sampled: number;
}

interface AllianceLoadout {
  alliance_id: number;
  alliance_name: string;
  total_damage: number;
  pilot_count: number;
  fleet_size: FleetSize | null;
  loadouts: LoadoutEntry[];
}

export interface AttackerLoadoutsData {
  battle_id: number;
  alliances: AllianceLoadout[];
}

interface BattleAttackerLoadoutsProps {
  data: AttackerLoadoutsData | null;
}

const DAMAGE_COLORS: Record<string, string> = {
  EM: '#00d4ff',
  Thermal: '#ff4444',
  Kinetic: '#888888',
  Explosive: '#ff8800',
  Mixed: '#a855f7',
};

const RANGE_COLORS: Record<string, string> = {
  Close: '#f85149',
  Medium: '#d29922',
  Long: '#00d4ff',
  Unknown: '#6e7681',
};

const WEAPON_COLORS: Record<string, string> = {
  Hybrid: '#3fb950',
  Laser: '#ff4444',
  Projectile: '#ff8800',
  Drone: '#a855f7',
  Torpedo: '#00d4ff',
  'Cruise Missile': '#00d4ff',
  'Heavy Missile': '#58a6ff',
  'Heavy Assault Missile': '#58a6ff',
  'Light Missile': '#79c0ff',
  Precursor: '#d29922',
};

export function BattleAttackerLoadouts({ data }: BattleAttackerLoadoutsProps) {
  const [expanded, setExpanded] = useState(false);

  if (!data || data.alliances.length === 0) return null;

  const totalPilots = data.alliances.reduce((s, a) => s + a.pilot_count, 0);

  // Calculate global range distribution
  const rangeCounts: Record<string, number> = {};
  let totalDamageAll = 0;
  for (const alliance of data.alliances) {
    for (const lo of alliance.loadouts) {
      rangeCounts[lo.range] = (rangeCounts[lo.range] || 0) + lo.total_damage;
      totalDamageAll += lo.total_damage;
    }
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      marginBottom: '1rem',
      overflow: 'hidden',
    }}>
      {/* Header — clickable to toggle */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '0.5rem 1rem',
          borderBottom: expanded ? '1px solid rgba(255,255,255,0.06)' : 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <span style={{ color: '#6e7681', fontSize: '0.65rem', flexShrink: 0 }}>
          {expanded ? '\u25BC' : '\u25B6'}
        </span>
        <span style={{
          padding: '0.15rem 0.5rem',
          borderRadius: '4px',
          background: 'rgba(88, 166, 255, 0.15)',
          color: '#58a6ff',
          fontSize: '0.7rem',
          fontWeight: 700,
        }}>
          ATTACKER LOADOUT ANALYSIS
        </span>
        <span style={{ color: '#8b949e', fontSize: '0.65rem' }}>
          {totalPilots} pilots across {data.alliances.length} group{data.alliances.length !== 1 ? 's' : ''}
        </span>

        {/* Range distribution */}
        {totalDamageAll > 0 && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span style={{ color: '#6e7681', fontSize: '0.55rem' }}>RANGE:</span>
            {['Close', 'Medium', 'Long'].map(r => {
              const pct = totalDamageAll > 0 ? ((rangeCounts[r] || 0) / totalDamageAll * 100) : 0;
              if (pct === 0) return null;
              return (
                <span key={r} style={{
                  padding: '0.1rem 0.3rem',
                  borderRadius: '2px',
                  background: `${RANGE_COLORS[r]}20`,
                  color: RANGE_COLORS[r],
                  fontSize: '0.55rem',
                  fontWeight: 700,
                }}>
                  {r} {pct.toFixed(0)}%
                </span>
              );
            })}
          </div>
        )}
      </div>

      {/* Alliance sections — collapsible */}
      {expanded && <div style={{ padding: '0.5rem 1rem' }}>
        {data.alliances.map((alliance) => (
          <div key={alliance.alliance_id} style={{ marginBottom: '0.75rem' }}>
            {/* Alliance header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginBottom: '0.35rem',
              flexWrap: 'wrap',
            }}>
              <span style={{ color: '#c9d1d9', fontSize: '0.7rem', fontWeight: 700 }}>
                {alliance.alliance_name}
              </span>
              <span style={{ color: '#8b949e', fontSize: '0.6rem' }}>
                {alliance.pilot_count}p
              </span>
              {alliance.fleet_size && alliance.fleet_size.avg && (
                <span style={{
                  padding: '0.1rem 0.3rem',
                  borderRadius: '2px',
                  background: 'rgba(168, 85, 247, 0.15)',
                  color: '#a855f7',
                  fontSize: '0.55rem',
                  fontWeight: 700,
                }}>
                  ~{Math.round(alliance.fleet_size.avg)} fleet
                </span>
              )}
              <span style={{
                color: '#ff8800',
                fontSize: '0.6rem',
                fontFamily: 'monospace',
              }}>
                {formatISKCompact(alliance.total_damage)} dmg
              </span>
            </div>

            {/* Loadout rows */}
            <div style={{
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '4px',
              padding: '0.3rem 0.5rem',
              border: '1px solid rgba(255,255,255,0.04)',
            }}>
              {alliance.loadouts.map((lo, idx) => (
                <div key={idx} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.15rem 0',
                  borderBottom: idx < alliance.loadouts.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
                  flexWrap: 'wrap',
                }}>
                  {/* Pilot count + Ship */}
                  <span style={{
                    color: '#c9d1d9',
                    fontSize: '0.6rem',
                    fontFamily: 'monospace',
                    width: '24px',
                    textAlign: 'right',
                  }}>
                    {lo.pilot_count}x
                  </span>
                  <span style={{
                    color: '#c9d1d9',
                    fontSize: '0.6rem',
                    fontWeight: 600,
                    minWidth: '80px',
                  }}>
                    {lo.ship_name}
                  </span>

                  {/* Weapon class badge */}
                  {lo.weapon_class && (
                    <span style={{
                      padding: '0.05rem 0.2rem',
                      borderRadius: '2px',
                      background: `${WEAPON_COLORS[lo.weapon_class] || '#6e7681'}15`,
                      color: WEAPON_COLORS[lo.weapon_class] || '#6e7681',
                      fontSize: '0.5rem',
                      fontWeight: 600,
                    }}>
                      {lo.weapon_class}
                    </span>
                  )}

                  {/* Range badge */}
                  {lo.range !== 'Unknown' && (
                    <span style={{
                      padding: '0.05rem 0.2rem',
                      borderRadius: '2px',
                      background: `${RANGE_COLORS[lo.range]}15`,
                      color: RANGE_COLORS[lo.range],
                      fontSize: '0.5rem',
                      fontWeight: 700,
                    }}>
                      {lo.range}
                    </span>
                  )}

                  {/* Damage type badge */}
                  {lo.damage_type && (
                    <span style={{
                      padding: '0.05rem 0.2rem',
                      borderRadius: '2px',
                      background: `${DAMAGE_COLORS[lo.damage_type] || '#6e7681'}15`,
                      color: DAMAGE_COLORS[lo.damage_type] || '#6e7681',
                      fontSize: '0.5rem',
                      fontWeight: 600,
                    }}>
                      {lo.damage_type}
                    </span>
                  )}

                  {/* Damage amount */}
                  <span style={{
                    color: '#8b949e',
                    fontSize: '0.55rem',
                    fontFamily: 'monospace',
                    marginLeft: 'auto',
                  }}>
                    {formatISKCompact(lo.total_damage)} dmg
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>}
    </div>
  );
}
