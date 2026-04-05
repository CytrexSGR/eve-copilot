import { formatISKCompact } from '../../utils/format';
import type { DamageAnalysisResponse } from '../../services/api';

interface BattleDamageAnalysisProps {
  damageAnalysis: DamageAnalysisResponse | null;
}

const DAMAGE_COLORS = {
  em: '#00d4ff',
  thermal: '#ff4444',
  kinetic: '#888888',
  explosive: '#ff8800',
};

const DAMAGE_LABELS = {
  em: 'EM',
  thermal: 'Thermal',
  kinetic: 'Kinetic',
  explosive: 'Explosive',
};

export function BattleDamageAnalysis({ damageAnalysis }: BattleDamageAnalysisProps) {
  if (!damageAnalysis || damageAnalysis.total_damage_analyzed === 0) {
    return null;
  }

  const { damage_profile, primary_damage_type, secondary_damage_type, tank_recommendation, alliance_profiles, top_damage_ships } = damageAnalysis;

  // Sort damage types by percentage
  const sortedTypes = Object.entries(damage_profile)
    .map(([type, pct]) => ({ type, pct }))
    .sort((a, b) => b.pct - a.pct);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: primary_damage_type ? DAMAGE_COLORS[primary_damage_type as keyof typeof DAMAGE_COLORS] : '#ff4444',
          }} />
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: '#ff4444',
            textTransform: 'uppercase'
          }}>
            Damage Analysis
          </span>
          {primary_damage_type && (
            <span style={{
              padding: '2px 6px',
              borderRadius: '3px',
              background: `${DAMAGE_COLORS[primary_damage_type as keyof typeof DAMAGE_COLORS]}30`,
              color: DAMAGE_COLORS[primary_damage_type as keyof typeof DAMAGE_COLORS],
              fontSize: '0.55rem',
              fontWeight: 700,
              textTransform: 'uppercase',
            }}>
              {DAMAGE_LABELS[primary_damage_type as keyof typeof DAMAGE_LABELS]} Primary
            </span>
          )}
        </div>

        {/* Summary Stats */}
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.65rem' }}>
          <span>
            <span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>
              {formatISKCompact(damageAnalysis.total_damage_analyzed)}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>dmg analyzed</span>
          </span>
          <span>
            <span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>
              {alliance_profiles.length}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>alliances</span>
          </span>
        </div>
      </div>

      {/* Content Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '0.3rem',
        padding: '0.4rem',
      }}>
        {/* Left: Damage Profile + Tank Recommendation */}
        <div style={{
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '6px',
          overflow: 'hidden',
        }}>
          {/* Section Header */}
          <div style={{
            padding: '0.4rem 0.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#ff4444' }} />
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase' }}>
                Incoming Damage Profile
              </span>
            </div>
          </div>

          {/* Damage Bars */}
          <div style={{ padding: '0.35rem' }}>
            {sortedTypes.map(({ type, pct }) => (
              <div key={type} style={{ marginBottom: '0.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem' }}>
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: type === primary_damage_type ? 700 : 500,
                    color: type === primary_damage_type ? DAMAGE_COLORS[type as keyof typeof DAMAGE_COLORS] : 'rgba(255,255,255,0.7)',
                  }}>
                    {DAMAGE_LABELS[type as keyof typeof DAMAGE_LABELS]}
                    {type === primary_damage_type && ' ★'}
                  </span>
                  <span style={{
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    color: DAMAGE_COLORS[type as keyof typeof DAMAGE_COLORS],
                    fontFamily: 'monospace',
                  }}>
                    {pct.toFixed(1)}%
                  </span>
                </div>
                <div style={{
                  height: '8px',
                  background: 'rgba(255,255,255,0.05)',
                  borderRadius: '2px',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${pct}%`,
                    background: `linear-gradient(90deg, ${DAMAGE_COLORS[type as keyof typeof DAMAGE_COLORS]}60, ${DAMAGE_COLORS[type as keyof typeof DAMAGE_COLORS]})`,
                    borderRadius: '2px',
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            ))}

            {/* Tank Recommendation */}
            {tank_recommendation && (
              <div style={{
                marginTop: '0.4rem',
                padding: '0.3rem 0.4rem',
                background: 'rgba(0, 255, 136, 0.1)',
                borderRadius: '4px',
                borderLeft: '2px solid #00ff88',
              }}>
                <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.1rem' }}>
                  Tank Recommendation
                </div>
                <div style={{ fontSize: '0.65rem', color: '#00ff88', fontWeight: 600 }}>
                  {tank_recommendation}
                </div>
                {primary_damage_type && secondary_damage_type && (
                  <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', marginTop: '0.25rem' }}>
                    Prioritize {DAMAGE_LABELS[primary_damage_type as keyof typeof DAMAGE_LABELS]} &amp; {DAMAGE_LABELS[secondary_damage_type as keyof typeof DAMAGE_LABELS]} hardeners
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Top Damage Ships */}
        <div style={{
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '6px',
          overflow: 'hidden',
        }}>
          {/* Section Header */}
          <div style={{
            padding: '0.4rem 0.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#ff8800' }} />
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff8800', textTransform: 'uppercase' }}>
                Top Damage Dealers
              </span>
            </div>
            <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
              by ship type
            </span>
          </div>

          {/* Ship List */}
          <div style={{ padding: '0.35rem', maxHeight: '200px', overflowY: 'auto' }}>
            {top_damage_ships.slice(0, 8).map((ship, idx) => {
              const maxDmg = top_damage_ships[0]?.total_damage || 1;
              const pct = (ship.total_damage / maxDmg) * 100;
              const isTop = idx === 0;

              return (
                <div
                  key={`${ship.ship_name}-${idx}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    padding: '0.2rem 0.35rem',
                    marginBottom: '0.15rem',
                    background: isTop ? 'rgba(255, 136, 0, 0.15)' : 'rgba(0,0,0,0.2)',
                    borderRadius: '4px',
                    borderLeft: `2px solid ${isTop ? '#ff8800' : 'rgba(255, 136, 0, 0.3)'}`,
                  }}
                >
                  {/* Rank */}
                  <span style={{
                    fontSize: '0.55rem',
                    fontWeight: 700,
                    color: isTop ? '#ff8800' : 'rgba(255,255,255,0.4)',
                    width: '16px',
                    textAlign: 'center',
                  }}>
                    #{idx + 1}
                  </span>

                  {/* Ship Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '0.65rem',
                      fontWeight: isTop ? 700 : 500,
                      color: isTop ? '#fff' : 'rgba(255,255,255,0.8)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {ship.ship_name}
                    </div>
                    <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
                      {ship.alliance_name} • {ship.engagements} uses
                    </div>
                  </div>

                  {/* Damage Bar + Value */}
                  <div style={{ width: '80px' }}>
                    <div style={{
                      height: '8px',
                      background: 'rgba(255,255,255,0.05)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                      marginBottom: '0.15rem',
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${pct}%`,
                        background: isTop ? '#ff8800' : 'rgba(255, 136, 0, 0.6)',
                        borderRadius: '2px',
                      }} />
                    </div>
                    <div style={{
                      fontSize: '0.6rem',
                      fontWeight: 700,
                      color: isTop ? '#ff8800' : 'rgba(255,255,255,0.6)',
                      fontFamily: 'monospace',
                      textAlign: 'right',
                    }}>
                      {formatISKCompact(ship.total_damage)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
