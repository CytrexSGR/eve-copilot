// src/components/powerbloc/PBCapsuleersView.tsx - Power Bloc Capsuleer Intel
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { powerblocApi } from '../../services/api/powerbloc';
import type { PBCapsuleersResponse } from '../../types/powerbloc';

interface PBCapsuleersViewProps {
  leaderId: number;
  days: number;
}

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

function effColor(eff: number): string {
  if (eff >= 55) return '#3fb950';
  if (eff >= 45) return '#ffcc00';
  return '#f85149';
}

function formatISKShort(v: number): string {
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return v.toLocaleString();
}

export function PBCapsuleersView({ leaderId, days }: PBCapsuleersViewProps) {
  const [data, setData] = useState<PBCapsuleersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    powerblocApi.getCapsuleers(leaderId, days)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [leaderId, days]);

  if (loading) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.75rem' }}>
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="skeleton" style={{ height: '80px', borderRadius: '6px' }} />
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
        <h3 style={{ color: '#f85149', margin: '0 0 0.5rem 0' }}>Failed to load capsuleer data</h3>
        <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0 }}>{error || 'Unknown error'}</p>
      </div>
    );
  }

  const { summary, alliance_rankings, corp_rankings, top_pilots } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>

      {/* SUMMARY ROW: 6 stat boxes */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.75rem' }}>
        {[
          { label: 'Active Pilots', value: summary.active_pilots.toLocaleString(), color: '#a855f7' },
          { label: 'Total Kills', value: summary.total_kills.toLocaleString(), color: '#3fb950' },
          { label: 'Total Deaths', value: summary.total_deaths.toLocaleString(), color: '#f85149' },
          { label: 'Pod Deaths', value: summary.pod_deaths.toLocaleString(), color: '#ff6600' },
          { label: 'Pod Survival', value: `${summary.pod_survival_rate.toFixed(1)}%`, color: '#58a6ff' },
          { label: 'K/D Ratio', value: summary.kd_ratio.toFixed(2), color: '#ffcc00' },
        ].map(stat => (
          <div key={stat.label} style={{
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px',
            padding: '0.6rem',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
              {stat.label}
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: stat.color, fontFamily: 'monospace' }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* ROW 1: Alliance Rankings (full width table) */}
      <div style={panelStyle('#58a6ff')}>
        <div style={headerStyle('#58a6ff')}>
          Alliance Rankings ({alliance_rankings.length})
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.7rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th style={{ padding: '0.4rem 0.5rem', textAlign: 'left', color: 'rgba(255,255,255,0.4)', fontWeight: 600, fontSize: '0.6rem', textTransform: 'uppercase' }}>#</th>
                <th style={{ padding: '0.4rem 0.5rem', textAlign: 'left', color: 'rgba(255,255,255,0.4)', fontWeight: 600, fontSize: '0.6rem', textTransform: 'uppercase' }}>Alliance</th>
                <th style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: 'rgba(255,255,255,0.4)', fontWeight: 600, fontSize: '0.6rem', textTransform: 'uppercase' }}>Pilots</th>
                <th style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: 'rgba(255,255,255,0.4)', fontWeight: 600, fontSize: '0.6rem', textTransform: 'uppercase' }}>Kills</th>
                <th style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: 'rgba(255,255,255,0.4)', fontWeight: 600, fontSize: '0.6rem', textTransform: 'uppercase' }}>Deaths</th>
                <th style={{ padding: '0.4rem 0.5rem', textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontWeight: 600, fontSize: '0.6rem', textTransform: 'uppercase', minWidth: '120px' }}>Efficiency</th>
                <th style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: 'rgba(255,255,255,0.4)', fontWeight: 600, fontSize: '0.6rem', textTransform: 'uppercase' }}>ISK Lost</th>
              </tr>
            </thead>
            <tbody>
              {alliance_rankings.map((a, i) => {
                const ec = effColor(a.efficiency);
                return (
                  <tr key={a.alliance_id} style={{
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    background: i < 3 ? 'rgba(88,166,255,0.05)' : 'transparent',
                  }}>
                    <td style={{ padding: '0.4rem 0.5rem', color: 'rgba(255,255,255,0.3)', fontSize: '0.6rem' }}>
                      {i + 1}
                    </td>
                    <td style={{ padding: '0.4rem 0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <img
                          src={`https://images.evetech.net/alliances/${a.alliance_id}/logo?size=32`}
                          alt=""
                          loading="lazy"
                          style={{ width: 22, height: 22, borderRadius: 3 }}
                          onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                        <Link
                          to={`/alliance/${a.alliance_id}`}
                          style={{ color: '#58a6ff', textDecoration: 'none', fontWeight: 600, fontSize: '0.7rem' }}
                        >
                          {a.alliance_name}
                        </Link>
                        <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)' }}>[{a.ticker}]</span>
                      </div>
                    </td>
                    <td style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: '#a855f7', fontFamily: 'monospace', fontWeight: 600 }}>
                      {a.pilots.toLocaleString()}
                    </td>
                    <td style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: '#3fb950', fontFamily: 'monospace', fontWeight: 600 }}>
                      {a.kills.toLocaleString()}
                    </td>
                    <td style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: '#f85149', fontFamily: 'monospace', fontWeight: 600 }}>
                      {a.deaths.toLocaleString()}
                    </td>
                    <td style={{ padding: '0.4rem 0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <div style={{
                          flex: 1,
                          height: '8px',
                          background: 'rgba(255,255,255,0.05)',
                          borderRadius: '4px',
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${Math.min(a.efficiency, 100)}%`,
                            height: '100%',
                            background: ec,
                            borderRadius: '4px',
                          }} />
                        </div>
                        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: ec, fontFamily: 'monospace', minWidth: '2.5rem', textAlign: 'right' }}>
                          {a.efficiency.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '0.4rem 0.5rem', textAlign: 'right', color: '#ff6600', fontFamily: 'monospace', fontSize: '0.65rem' }}>
                      {formatISKShort(a.isk_lost)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ROW 2: Corp Rankings + Top Pilots */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>

        {/* Corp Rankings */}
        <div style={panelStyle('#a855f7')}>
          <div style={{
            ...headerStyle('#a855f7'),
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>Corp Rankings</span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', fontWeight: 400 }}>
              {corp_rankings.length} corps
            </span>
          </div>
          <div style={{ padding: '0.25rem 0.5rem', maxHeight: '350px', overflowY: 'auto' }}>
            {(() => {
              const maxCorpKills = Math.max(...corp_rankings.slice(0, 20).map(c => c.kills), 1);
              return corp_rankings.slice(0, 20).map((corp, i) => (
                <div key={corp.corporation_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.35rem 0',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  background: i < 3 ? 'rgba(168,85,247,0.08)' : 'transparent',
                  borderLeft: i < 3 ? '2px solid #a855f7' : '2px solid transparent',
                  borderRadius: '2px',
                  paddingLeft: '0.4rem',
                  marginBottom: '0.1rem',
                }}>
                  <span style={{
                    fontSize: '0.6rem',
                    color: 'rgba(255,255,255,0.3)',
                    width: '1.5rem',
                    textAlign: 'center',
                    flexShrink: 0,
                  }}>
                    #{i + 1}
                  </span>
                  <img
                    src={`https://images.evetech.net/corporations/${corp.corporation_id}/logo?size=32`}
                    alt=""
                    loading="lazy"
                    style={{ width: 20, height: 20, borderRadius: 3, flexShrink: 0 }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '0.7rem',
                      color: '#fff',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontWeight: i < 3 ? 600 : 400,
                    }}>
                      {corp.corporation_name}
                    </div>
                    {/* Kill bar */}
                    <div style={{
                      marginTop: '0.15rem',
                      height: '4px',
                      background: 'rgba(255,255,255,0.05)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        width: `${(corp.kills / maxCorpKills) * 100}%`,
                        height: '100%',
                        background: i < 3 ? '#a855f7' : 'rgba(168,85,247,0.5)',
                        borderRadius: '2px',
                      }} />
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', flexShrink: 0 }}>
                    <span style={{
                      fontSize: '0.6rem',
                      color: '#a855f7',
                      fontFamily: 'monospace',
                    }}>
                      {corp.pilots} pilots
                    </span>
                    <span style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      color: '#3fb950',
                      fontFamily: 'monospace',
                    }}>
                      {corp.kills.toLocaleString()} kills
                    </span>
                  </div>
                </div>
              ));
            })()}
          </div>
        </div>

        {/* Top Pilots */}
        <div style={panelStyle('#ffcc00')}>
          <div style={headerStyle('#ffcc00')}>
            Top Pilots ({top_pilots.length})
          </div>
          <div style={{ padding: '0.25rem 0.5rem', maxHeight: '350px', overflowY: 'auto' }}>
            {top_pilots.slice(0, 20).map((pilot, i) => {
              const ec = effColor(pilot.efficiency);
              return (
                <div key={pilot.character_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.35rem 0',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                }}>
                  <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', width: '1.2rem' }}>#{i + 1}</span>
                  <img
                    src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
                    alt=""
                    loading="lazy"
                    style={{ width: 24, height: 24, borderRadius: '50%' }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <a
                        href={`https://zkillboard.com/character/${pilot.character_id}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontSize: '0.7rem', color: '#58a6ff', textDecoration: 'none', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      >
                        {pilot.character_name}
                      </a>
                      <img
                        src={`https://images.evetech.net/alliances/${pilot.alliance_id}/logo?size=32`}
                        alt=""
                        loading="lazy"
                        style={{ width: 14, height: 14, borderRadius: 2 }}
                        onError={(e) => { e.currentTarget.style.display = 'none'; }}
                      />
                    </div>
                    <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
                      {pilot.alliance_name}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.1rem' }}>
                    <div style={{ fontSize: '0.6rem', fontFamily: 'monospace' }}>
                      <span style={{ color: '#3fb950', fontWeight: 700 }}>{pilot.kills}</span>
                      <span style={{ color: 'rgba(255,255,255,0.3)' }}>/</span>
                      <span style={{ color: '#f85149' }}>{pilot.deaths}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.55rem' }}>
                      <span style={{ color: ec, fontWeight: 600 }}>{pilot.efficiency.toFixed(1)}%</span>
                      {pilot.pod_deaths > 0 && (
                        <span style={{ color: '#ff6600' }}>{pilot.pod_deaths} pods</span>
                      )}
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

export default PBCapsuleersView;
