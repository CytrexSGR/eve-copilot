// src/components/powerbloc/PBWormholeView.tsx - Power Bloc Wormhole Intel
import { useState, useEffect } from 'react';
import { powerblocApi } from '../../services/api/powerbloc';
import { formatISKCompact } from '../../utils/format';
import type { PBWormholeResponse } from '../../types/powerbloc';

interface PBWormholeViewProps {
  leaderId: number;
  days: number;
}

const WH_CLASS_COLORS: Record<number, string> = {
  1: '#3fb950', 2: '#3fb950', 3: '#3fb950',
  4: '#ffcc00',
  5: '#ff6600',
  6: '#f85149',
};

const EFFECT_COLORS: Record<string, string> = {
  'Wolf-Rayet': '#ff4444',
  'Pulsar': '#58a6ff',
  'Magnetar': '#a855f7',
  'Black Hole': '#333333',
  'Cataclysmic': '#00bcd4',
  'Red Giant': '#ff6600',
};

const THREAT_COLORS: Record<string, string> = {
  critical: '#ff0000',
  high: '#ff6600',
  moderate: '#ffcc00',
  low: '#3fb950',
};

const panelStyle = (color: string): React.CSSProperties => ({
  background: 'rgba(0,0,0,0.3)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderLeft: `3px solid ${color}`,
  borderRadius: '6px',
  overflow: 'hidden',
});

const headerStyle = (color: string): React.CSSProperties => ({
  padding: '0.4rem 0.6rem',
  borderBottom: '1px solid rgba(255,255,255,0.08)',
  fontSize: '0.7rem',
  fontWeight: 700,
  color,
  textTransform: 'uppercase',
});

function getWhClassColor(whClass: number | null): string {
  if (whClass === null) return '#888';
  if (whClass <= 3) return WH_CLASS_COLORS[1];
  if (whClass === 4) return WH_CLASS_COLORS[4];
  if (whClass === 5) return WH_CLASS_COLORS[5];
  return WH_CLASS_COLORS[6];
}

export function PBWormholeView({ leaderId, days }: PBWormholeViewProps) {
  const [data, setData] = useState<PBWormholeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    powerblocApi.getWormhole(leaderId, days)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [leaderId, days]);

  if (loading) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        {[1, 2, 3].map(i => (
          <div key={i} className="skeleton" style={{ height: '120px', borderRadius: '6px' }} />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{
        background: 'rgba(248,81,73,0.2)',
        border: '1px solid #f85149',
        borderRadius: '8px',
        padding: '2rem',
        textAlign: 'center',
      }}>
        <h3 style={{ color: '#f85149', margin: '0 0 0.5rem 0' }}>Failed to load wormhole data</h3>
        <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0 }}>{error || 'Unknown error'}</p>
      </div>
    );
  }

  const { summary, controlled_systems, visitors, sov_threats } = data;
  const classEntries = Object.entries(summary.class_breakdown).sort(([, a], [, b]) => b - a);
  const maxClassCount = Math.max(...classEntries.map(([, v]) => v), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>

      {/* SUMMARY ROW */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '6px',
          padding: '0.6rem',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            Controlled Systems
          </div>
          <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {summary.total_systems}
          </div>
        </div>
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '6px',
          padding: '0.6rem',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            ISK Potential / Month
          </div>
          <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>
            {formatISKCompact(summary.total_isk_potential_m * 1e6)}
          </div>
        </div>
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '6px',
          padding: '0.5rem',
        }}>
          <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.35rem', textAlign: 'center' }}>
            Class Breakdown
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', height: '40px', gap: '3px', justifyContent: 'center' }}>
            {classEntries.slice(0, 8).map(([cls, count]) => (
              <div key={cls} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                <div style={{
                  width: '16px',
                  height: `${Math.max((count / maxClassCount) * 36, 4)}px`,
                  background: getWhClassColor(parseInt(cls.replace('C', '')) || null),
                  borderRadius: '2px 2px 0 0',
                }} title={`${cls}: ${count}`} />
                <span style={{ fontSize: '0.45rem', color: 'rgba(255,255,255,0.5)' }}>{cls}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* MAIN: 2-col (2/3 + 1/3) */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>

        {/* Left: Controlled Systems */}
        <div style={panelStyle('#3fb950')}>
          <div style={headerStyle('#3fb950')}>
            Controlled Systems ({controlled_systems.length})
          </div>
          <div style={{ padding: '0.25rem 0.5rem', maxHeight: '450px', overflowY: 'auto' }}>
            {controlled_systems.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', padding: '1rem', textAlign: 'center' }}>
                No controlled wormhole systems found
              </div>
            ) : controlled_systems.map((sys, i) => {
              const classColor = getWhClassColor(sys.wh_class);
              const effectColor = sys.effect_name ? (EFFECT_COLORS[sys.effect_name] || '#888') : null;
              return (
                <div key={`${sys.system_id}-${i}`} style={{
                  padding: '0.5rem 0.4rem',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.3rem',
                }}>
                  {/* System header row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    {/* WH Class badge */}
                    <span style={{
                      fontSize: '0.55rem',
                      fontWeight: 700,
                      color: '#fff',
                      background: classColor,
                      padding: '2px 5px',
                      borderRadius: '3px',
                      minWidth: '24px',
                      textAlign: 'center',
                    }}>
                      {sys.wh_class !== null ? `C${sys.wh_class}` : '??'}
                    </span>

                    {/* Effect badge */}
                    {sys.effect_name && effectColor && (
                      <span style={{
                        fontSize: '0.5rem',
                        fontWeight: 600,
                        color: '#fff',
                        background: effectColor,
                        padding: '1px 4px',
                        borderRadius: '2px',
                      }}>
                        {sys.effect_name}
                      </span>
                    )}

                    {/* System name */}
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff' }}>
                      {sys.system_name}
                    </span>

                    <div style={{ flex: 1 }} />

                    {/* Alliance logo + name */}
                    <img
                      src={`https://images.evetech.net/alliances/${sys.alliance_id}/logo?size=32`}
                      alt=""
                      loading="lazy"
                      style={{ width: 18, height: 18, borderRadius: 2 }}
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                    <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.6)' }}>
                      {sys.alliance_name}
                    </span>
                  </div>

                  {/* Stats row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.6rem' }}>
                    <span style={{ color: '#3fb950' }}>{sys.kills} kills</span>
                    <span style={{ color: '#f85149' }}>{sys.losses} losses</span>
                    {sys.last_seen && (
                      <span style={{ color: 'rgba(255,255,255,0.4)' }}>
                        Last: {new Date(sys.last_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    )}
                    <div style={{ flex: 1 }} />
                    <span style={{ fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>
                      {formatISKCompact(sys.isk_per_month_m * 1e6)}/mo
                    </span>
                  </div>

                  {/* Statics */}
                  {sys.statics.length > 0 && (
                    <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                      {sys.statics.map((s, si) => (
                        <span key={si} style={{
                          fontSize: '0.5rem',
                          padding: '1px 4px',
                          background: 'rgba(255,255,255,0.08)',
                          borderRadius: '2px',
                          color: 'rgba(255,255,255,0.6)',
                        }}>
                          {s.type}{s.destination_class ? ` -> ${s.destination_class}` : ''}
                          {s.lifetime ? ` (${s.lifetime}h)` : ''}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right column: Class Distribution + Visitors */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>

          {/* Class Distribution */}
          <div style={panelStyle('#58a6ff')}>
            <div style={headerStyle('#58a6ff')}>Class Distribution</div>
            <div style={{ padding: '0.4rem 0.5rem' }}>
              {classEntries.map(([cls, count]) => {
                const whNum = parseInt(cls.replace('C', '')) || null;
                const color = getWhClassColor(whNum);
                return (
                  <div key={cls} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.2rem 0',
                  }}>
                    <span style={{ fontSize: '0.65rem', color: '#fff', width: '2rem', fontWeight: 600 }}>{cls}</span>
                    <div style={{
                      flex: 1,
                      height: '10px',
                      background: 'rgba(255,255,255,0.05)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        width: `${(count / maxClassCount) * 100}%`,
                        height: '100%',
                        background: color,
                        borderRadius: '2px',
                      }} />
                    </div>
                    <span style={{ fontSize: '0.65rem', fontWeight: 600, color, fontFamily: 'monospace', minWidth: '1.5rem', textAlign: 'right' }}>
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Visitors */}
          <div style={panelStyle('#ff6600')}>
            <div style={headerStyle('#ff6600')}>
              Visitors ({visitors.length})
            </div>
            <div style={{ padding: '0.25rem 0.5rem', maxHeight: '250px', overflowY: 'auto' }}>
              {visitors.length === 0 ? (
                <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', padding: '1rem', textAlign: 'center' }}>
                  No visitors detected
                </div>
              ) : visitors.slice(0, 15).map((v, i) => {
                const threatColor = THREAT_COLORS[v.threat_level] || '#888';
                return (
                  <div key={`${v.alliance_id}-${v.system_id}-${i}`} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.3rem 0',
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                  }}>
                    <img
                      src={`https://images.evetech.net/alliances/${v.alliance_id}/logo?size=32`}
                      alt=""
                      loading="lazy"
                      style={{ width: 20, height: 20, borderRadius: 2 }}
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.65rem', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {v.alliance_name}
                      </div>
                      <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
                        <span style={{ color: '#3fb950' }}>{v.kills}k</span> / <span style={{ color: '#f85149' }}>{v.losses}l</span>
                      </div>
                    </div>
                    <span style={{
                      fontSize: '0.5rem',
                      fontWeight: 700,
                      color: '#fff',
                      background: threatColor,
                      padding: '1px 5px',
                      borderRadius: '2px',
                      textTransform: 'uppercase',
                    }}>
                      {v.threat_level}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* SOV THREATS (full width, conditional) */}
      {sov_threats.length > 0 && (
        <div style={panelStyle('#f85149')}>
          <div style={headerStyle('#f85149')}>
            SOV Threats ({sov_threats.length} alliances)
          </div>
          <div style={{ padding: '0.5rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '0.5rem' }}>
            {sov_threats.map((threat, i) => {
              const totalThreats = threat.threat_breakdown.critical + threat.threat_breakdown.high +
                threat.threat_breakdown.moderate + threat.threat_breakdown.low;
              const overallLevel = threat.threat_breakdown.critical > 0 ? 'critical'
                : threat.threat_breakdown.high > 0 ? 'high'
                : threat.threat_breakdown.moderate > 0 ? 'moderate' : 'low';
              const levelColor = THREAT_COLORS[overallLevel];

              return (
                <div key={`${threat.alliance_id}-${i}`} style={{
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: '4px',
                  borderLeft: `3px solid ${levelColor}`,
                  padding: '0.5rem',
                }}>
                  {/* Alliance header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
                    <img
                      src={`https://images.evetech.net/alliances/${threat.alliance_id}/logo?size=32`}
                      alt=""
                      loading="lazy"
                      style={{ width: 24, height: 24, borderRadius: 3 }}
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff', flex: 1 }}>
                      {threat.alliance_name}
                    </span>
                    <span style={{
                      fontSize: '0.5rem',
                      fontWeight: 700,
                      color: '#fff',
                      background: levelColor,
                      padding: '1px 5px',
                      borderRadius: '2px',
                      textTransform: 'uppercase',
                    }}>
                      {overallLevel}
                    </span>
                  </div>

                  {/* Stats grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.3rem', marginBottom: '0.4rem' }}>
                    <div style={{ fontSize: '0.55rem' }}>
                      <div style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>WH Systems</div>
                      <div style={{ color: '#58a6ff', fontWeight: 700, fontFamily: 'monospace' }}>{threat.total_wh_systems}</div>
                    </div>
                    <div style={{ fontSize: '0.55rem' }}>
                      <div style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Kills</div>
                      <div style={{ color: '#3fb950', fontWeight: 700, fontFamily: 'monospace' }}>{threat.total_kills.toLocaleString()}</div>
                    </div>
                    <div style={{ fontSize: '0.55rem' }}>
                      <div style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>ISK Destroyed</div>
                      <div style={{ color: '#ffcc00', fontWeight: 700, fontFamily: 'monospace' }}>{formatISKCompact(threat.total_isk_destroyed)}</div>
                    </div>
                  </div>

                  {/* Threat breakdown bar */}
                  {totalThreats > 0 && (
                    <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.3rem' }}>
                      {threat.threat_breakdown.critical > 0 && (
                        <div style={{ width: `${(threat.threat_breakdown.critical / totalThreats) * 100}%`, background: '#ff0000' }}
                          title={`Critical: ${threat.threat_breakdown.critical}`} />
                      )}
                      {threat.threat_breakdown.high > 0 && (
                        <div style={{ width: `${(threat.threat_breakdown.high / totalThreats) * 100}%`, background: '#ff6600' }}
                          title={`High: ${threat.threat_breakdown.high}`} />
                      )}
                      {threat.threat_breakdown.moderate > 0 && (
                        <div style={{ width: `${(threat.threat_breakdown.moderate / totalThreats) * 100}%`, background: '#ffcc00' }}
                          title={`Moderate: ${threat.threat_breakdown.moderate}`} />
                      )}
                      {threat.threat_breakdown.low > 0 && (
                        <div style={{ width: `${(threat.threat_breakdown.low / totalThreats) * 100}%`, background: '#3fb950' }}
                          title={`Low: ${threat.threat_breakdown.low}`} />
                      )}
                    </div>
                  )}

                  {/* Timezone distribution */}
                  <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.55rem' }}>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                      US: <span style={{ color: '#58a6ff', fontWeight: 600 }}>{threat.timezone.us}%</span>
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                      EU: <span style={{ color: '#3fb950', fontWeight: 600 }}>{threat.timezone.eu}%</span>
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                      AU: <span style={{ color: '#ffcc00', fontWeight: 600 }}>{threat.timezone.au}%</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default PBWormholeView;
