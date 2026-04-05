import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { powerblocApi } from '../../services/api/powerbloc';

interface PBAlliancesViewProps {
  leaderId: number;
  days: number;
}

// Red Flag Thresholds
const RED_FLAGS = {
  EFFICIENCY_LOW: 40,
  ACTIVITY_LOW: 5,
  DEATHS_PER_PILOT_HIGH: 10,
  REGIONS_LOW: 3,
};

// K/D Ratio color coding
const getKDColor = (ratio: number): string => {
  if (ratio >= 2.0) return '#3fb950'; // Green (excellent)
  if (ratio >= 1.0) return '#ffa657'; // Orange (good)
  return '#f85149'; // Red (poor)
};

interface ProblemAlliance {
  ally: any;
  flags: string[];
}

export const PBAlliancesView: React.FC<PBAlliancesViewProps> = ({ leaderId, days }) => {
  const [ranking, setRanking] = useState<any[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [ships, setShips] = useState<any[]>([]);
  const [regions, setRegions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [rankingData, trendsData, shipsData, regionsData] = await Promise.all([
          powerblocApi.getAlliancesRanking(leaderId, days),
          powerblocApi.getAlliancesTrends(leaderId, days),
          powerblocApi.getAlliancesShips(leaderId, days),
          powerblocApi.getAlliancesRegions(leaderId, days),
        ]);
        setRanking(rankingData);
        setTrends(trendsData);
        setShips(shipsData);
        setRegions(regionsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load alliances data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [leaderId, days]);

  // Detect problem alliances
  const problemAlliances = useMemo((): ProblemAlliance[] => {
    if (!ranking.length) return [];

    const problems: ProblemAlliance[] = [];

    ranking.forEach(ally => {
      const flags: string[] = [];

      if (ally.efficiency < RED_FLAGS.EFFICIENCY_LOW) {
        flags.push(`Low Efficiency: ${ally.efficiency}%`);
      }
      if (ally.activity_share_pct < RED_FLAGS.ACTIVITY_LOW) {
        flags.push(`Dead Weight: ${ally.activity_share_pct}% activity`);
      }
      if (ally.deaths_per_pilot > RED_FLAGS.DEATHS_PER_PILOT_HIGH) {
        flags.push(`High Deaths: ${ally.deaths_per_pilot.toFixed(1)}/pilot`);
      }

      // Check region count (if available)
      const allyRegion = regions.find(r => r.alliance_id === ally.alliance_id);
      if (allyRegion && allyRegion.region_count < RED_FLAGS.REGIONS_LOW) {
        flags.push(`Isolated: ${allyRegion.region_count} regions`);
      }

      if (flags.length > 0) {
        problems.push({ ally, flags });
      }
    });

    return problems.sort((a, b) => b.flags.length - a.flags.length);
  }, [ranking, regions]);

  // Get top and bottom alliances
  const topAlliances = useMemo(() => ranking.slice(0, Math.ceil(ranking.length / 2)), [ranking]);
  const bottomAlliances = useMemo(() => ranking.slice(Math.ceil(ranking.length / 2)).reverse(), [ranking]);

  // Get dominant ship class per alliance
  const allyShipClass = useMemo(() => {
    const map = new Map<number, string>();
    ships.forEach(entry => {
      if (!map.has(entry.alliance_id)) {
        map.set(entry.alliance_id, entry.ship_class);
      }
    });
    return map;
  }, [ships]);

  // Group trends by alliance for sparklines
  const allyTrendsMap = useMemo(() => {
    const map = new Map<number, any[]>();
    trends.forEach(trend => {
      if (!map.has(trend.alliance_id)) {
        map.set(trend.alliance_id, []);
      }
      map.get(trend.alliance_id)!.push(trend);
    });
    // Sort by date for each alliance
    map.forEach(allyTrends => {
      allyTrends.sort((a, b) => a.day.localeCompare(b.day));
    });
    return map;
  }, [trends]);

  // Calculate trend indicator
  const getTrendIndicator = (allianceId: number): string => {
    const allyTrends = allyTrendsMap.get(allianceId);
    if (!allyTrends || allyTrends.length < 4) return '→';

    const first3 = allyTrends.slice(0, 3).reduce((sum, t) => sum + t.efficiency, 0) / 3;
    const last3 = allyTrends.slice(-3).reduce((sum, t) => sum + t.efficiency, 0) / 3;
    const diff = last3 - first3;

    if (diff > 10) return '⬆️';
    if (diff < -10) return '⬇️';
    return '→';
  };

  // Simple sparkline (text-based)
  const getSparkline = (allianceId: number): string => {
    const allyTrends = allyTrendsMap.get(allianceId);
    if (!allyTrends || allyTrends.length < 2) return '▄▄▄▄▄▄▄';

    const values = allyTrends.map(t => t.efficiency);
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = max - min || 1;

    const chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
    return values.map(v => {
      const normalized = (v - min) / range;
      const index = Math.min(7, Math.floor(normalized * 8));
      return chars[index];
    }).join('');
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '16rem' }}>
        <div style={{ color: 'rgba(255,255,255,0.5)' }}>Loading alliances intel...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '16rem' }}>
        <div style={{ color: '#f85149' }}>{error}</div>
      </div>
    );
  }

  const formatISK = (isk: number) => {
    if (isk >= 1e12) return `${(isk / 1e12).toFixed(1)}T`;
    if (isk >= 1e9) return `${(isk / 1e9).toFixed(1)}B`;
    return `${(isk / 1e6).toFixed(0)}M`;
  };

  const renderAllianceRow = (ally: any, colorTheme: 'green' | 'red') => {
    const isGreen = colorTheme === 'green';
    const mainColor = isGreen ? '#3fb950' : '#f85149';
    const bgColor = isGreen ? 'rgba(63, 185, 80, 0.08)' : 'rgba(248, 81, 73, 0.08)';
    const bgHover = isGreen ? 'rgba(63, 185, 80, 0.15)' : 'rgba(248, 81, 73, 0.15)';
    const borderColor = isGreen ? 'rgba(63, 185, 80, 0.2)' : 'rgba(248, 81, 73, 0.2)';
    const borderHover = isGreen ? 'rgba(63, 185, 80, 0.4)' : 'rgba(248, 81, 73, 0.4)';
    const shipClass = allyShipClass.get(ally.alliance_id) || 'Mixed';
    const allyRegion = regions.find(r => r.alliance_id === ally.alliance_id);

    return (
      <Link
        key={ally.alliance_id}
        to={`/alliance/${ally.alliance_id}`}
        style={{
          display: 'block',
          padding: '0.4rem 0.5rem',
          marginBottom: '0.3rem',
          borderRadius: '4px',
          background: bgColor,
          border: `1px solid ${borderColor}`,
          textDecoration: 'none',
          color: 'inherit',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = bgHover;
          e.currentTarget.style.borderColor = borderHover;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = bgColor;
          e.currentTarget.style.borderColor = borderColor;
        }}
      >
        {/* Row 1: Logo + Name + Ticker + Activity% */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
          <img
            src={`https://images.evetech.net/alliances/${ally.alliance_id}/logo?size=32`}
            alt=""
            style={{ width: '20px', height: '20px', borderRadius: '2px' }}
          />
          <span style={{ color: mainColor, fontSize: '0.75rem', fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {ally.alliance_name}
          </span>
          {ally.ticker && (
            <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>[{ally.ticker}]</span>
          )}
          <span style={{
            fontSize: '0.8rem',
            fontWeight: 700,
            color: mainColor,
            background: isGreen ? 'rgba(63, 185, 80, 0.15)' : 'rgba(248, 81, 73, 0.15)',
            padding: '0.1rem 0.4rem',
            borderRadius: '3px',
          }}>
            {ally.activity_share_pct.toFixed(1)}%
          </span>
        </div>

        {/* Row 2: Metrics */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.7rem', flexWrap: 'wrap' }}>
          <div>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>K/D:</span>{' '}
            <span style={{ color: getKDColor(ally.deaths > 0 ? ally.kills / ally.deaths : ally.kills), fontWeight: 600 }}>
              {ally.deaths > 0 ? (ally.kills / ally.deaths).toFixed(2) : ally.kills.toFixed(0)}
            </span>
          </div>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
          <div>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>Eff:</span>{' '}
            <span style={{ color: ally.efficiency < 40 ? '#f85149' : 'rgba(255,255,255,0.9)', fontWeight: 600 }}>{ally.efficiency.toFixed(0)}%</span>
          </div>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
          <div>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>ISK:</span>{' '}
            <span style={{ color: '#3fb950' }}>{formatISK(ally.isk_killed)}</span>
            <span style={{ color: 'rgba(255,255,255,0.3)' }}>/</span>
            <span style={{ color: '#f85149' }}>{formatISK(ally.isk_lost)}</span>
          </div>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
          <div>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>Pilots:</span>{' '}
            <span style={{ color: 'rgba(255,255,255,0.9)' }}>{ally.active_pilots}</span>
            {!isGreen && (
              <span style={{ color: 'rgba(255,255,255,0.5)' }}> ({ally.deaths_per_pilot.toFixed(1)} d/p{ally.deaths_per_pilot > RED_FLAGS.DEATHS_PER_PILOT_HIGH && ' 🔴'})</span>
            )}
          </div>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
          <div>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>Class:</span>{' '}
            <span style={{ color: '#a855f7' }}>{shipClass}</span>
          </div>
          {allyRegion && (
            <>
              <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
              <div>
                <span style={{ color: 'rgba(255,255,255,0.5)' }}>Regions:</span>{' '}
                <span style={{ color: allyRegion.region_count < RED_FLAGS.REGIONS_LOW ? '#f85149' : '#ffa657' }}>
                  {allyRegion.region_count}
                </span>
              </div>
            </>
          )}
        </div>
      </Link>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Panel 1: Problem Alliances Alert */}
      {problemAlliances.length > 0 && (
        <div style={{
          background: 'rgba(248, 81, 73, 0.1)',
          border: '1px solid rgba(248, 81, 73, 0.3)',
          borderRadius: '6px',
          padding: '0.5rem 0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f85149' }}>
              ⚠️ PROBLEM ALLIANCES DETECTED ({problemAlliances.length})
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            {problemAlliances.slice(0, 5).map(({ ally, flags }) => (
              <div key={ally.alliance_id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.75rem',
              }}>
                <img
                  src={`https://images.evetech.net/alliances/${ally.alliance_id}/logo?size=32`}
                  alt=""
                  style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                />
                <span style={{ color: '#f85149', minWidth: '12ch' }}>{ally.alliance_name}</span>
                <span style={{ color: 'rgba(255,255,255,0.5)' }}>|</span>
                <span style={{ color: 'rgba(255,255,255,0.7)' }}>{flags.join(' • ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Carry vs Dead Weight - Full Width */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderLeft: '2px solid #3fb950',
        borderRadius: '6px',
        padding: '0.75rem',
        maxHeight: '550px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: '#3fb950', fontSize: '0.625rem' }}>●</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.9)', letterSpacing: '0.05em' }}>
            CARRY vs DEAD WEIGHT
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', overflowY: 'auto', flex: 1 }}>
          {/* Top Performers */}
          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#3fb950', marginBottom: '0.5rem' }}>
              TOP PERFORMERS (Carry)
            </div>
            {topAlliances.map(ally => renderAllianceRow(ally, 'green'))}
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#f85149', marginBottom: '0.5rem' }}>
              BOTTOM PERFORMERS (Dead Weight)
            </div>
            {bottomAlliances.map(ally => renderAllianceRow(ally, 'red'))}
          </div>
        </div>
      </div>

      {/* Performance Trends - Full Width */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderLeft: '2px solid #58a6ff',
        borderRadius: '6px',
        padding: '0.75rem',
        maxHeight: '500px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: '#58a6ff', fontSize: '0.625rem' }}>●</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.9)', letterSpacing: '0.05em' }}>
            PERFORMANCE TRENDS
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.5rem', overflowY: 'auto', flex: 1 }}>
          {ranking.map(ally => {
            const indicator = getTrendIndicator(ally.alliance_id);
            const sparkline = getSparkline(ally.alliance_id);
            const isImproving = indicator === '⬆️';
            const isDeclining = indicator === '⬇️';
            const allyTrends = allyTrendsMap.get(ally.alliance_id) || [];
            const recentActivity = allyTrends.slice(-3).reduce((sum, t) => sum + t.activity, 0);
            const shipClass = allyShipClass.get(ally.alliance_id) || 'Mixed';

            return (
              <Link
                key={ally.alliance_id}
                to={`/alliance/${ally.alliance_id}`}
                style={{
                  display: 'block',
                  padding: '0.4rem 0.5rem',
                  borderRadius: '4px',
                  background: isImproving ? 'rgba(63, 185, 80, 0.08)' : isDeclining ? 'rgba(248, 81, 73, 0.08)' : 'rgba(88, 166, 255, 0.05)',
                  border: `1px solid ${isImproving ? 'rgba(63, 185, 80, 0.2)' : isDeclining ? 'rgba(248, 81, 73, 0.2)' : 'rgba(88, 166, 255, 0.15)'}`,
                  textDecoration: 'none',
                  color: 'inherit',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  const bg = isImproving ? 'rgba(63, 185, 80, 0.15)' : isDeclining ? 'rgba(248, 81, 73, 0.15)' : 'rgba(88, 166, 255, 0.1)';
                  const border = isImproving ? 'rgba(63, 185, 80, 0.4)' : isDeclining ? 'rgba(248, 81, 73, 0.4)' : 'rgba(88, 166, 255, 0.3)';
                  e.currentTarget.style.background = bg;
                  e.currentTarget.style.borderColor = border;
                }}
                onMouseLeave={(e) => {
                  const bg = isImproving ? 'rgba(63, 185, 80, 0.08)' : isDeclining ? 'rgba(248, 81, 73, 0.08)' : 'rgba(88, 166, 255, 0.05)';
                  const border = isImproving ? 'rgba(63, 185, 80, 0.2)' : isDeclining ? 'rgba(248, 81, 73, 0.2)' : 'rgba(88, 166, 255, 0.15)';
                  e.currentTarget.style.background = bg;
                  e.currentTarget.style.borderColor = border;
                }}
              >
                {/* Row 1: Logo + Name + Indicator */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                  <img
                    src={`https://images.evetech.net/alliances/${ally.alliance_id}/logo?size=32`}
                    alt=""
                    style={{ width: '20px', height: '20px', borderRadius: '2px' }}
                  />
                  <span style={{
                    color: isImproving ? '#3fb950' : isDeclining ? '#f85149' : 'rgba(255,255,255,0.9)',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    flex: 1,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {ally.alliance_name}
                  </span>
                  <span style={{ fontSize: '1rem' }}>{indicator}</span>
                </div>

                {/* Row 2: Sparkline + Efficiency */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                  <span style={{ color: '#58a6ff', fontFamily: 'monospace', fontSize: '0.8rem', letterSpacing: '0.05em' }}>
                    {sparkline}
                  </span>
                  <span style={{
                    marginLeft: 'auto',
                    color: ally.efficiency >= 50 ? '#3fb950' : ally.efficiency < 40 ? '#f85149' : 'rgba(255,255,255,0.9)',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                  }}>
                    {ally.efficiency.toFixed(0)}%
                  </span>
                </div>

                {/* Row 3: Detailed Metrics */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.7rem', flexWrap: 'wrap' }}>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>K/D:</span>{' '}
                    <span style={{ color: getKDColor(ally.deaths > 0 ? ally.kills / ally.deaths : ally.kills), fontWeight: 600 }}>
                      {ally.deaths > 0 ? (ally.kills / ally.deaths).toFixed(2) : ally.kills.toFixed(0)}
                    </span>
                  </div>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>ISK:</span>{' '}
                    <span style={{ color: '#3fb950' }}>{formatISK(ally.isk_killed)}</span>
                  </div>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>3d:</span>{' '}
                    <span style={{ color: 'rgba(255,255,255,0.9)' }}>{recentActivity}</span>
                  </div>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>Pilots:</span>{' '}
                    <span style={{ color: 'rgba(255,255,255,0.9)' }}>{ally.active_pilots}</span>
                  </div>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                  <div>
                    <span style={{ color: '#a855f7' }}>{shipClass}</span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Bottom Row: Ship Specialization + Geographic Spread + Pilot Engagement */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        {/* Panel 4: Ship Specialization */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderLeft: '2px solid #a855f7',
          borderRadius: '6px',
          padding: '0.75rem',
          overflow: 'hidden',
        }}>
          <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: '#a855f7', fontSize: '0.625rem' }}>●</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.9)', letterSpacing: '0.05em' }}>
              SHIP SPECIALIZATION
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            {ranking.slice(0, 15).map(ally => {
              const shipClass = allyShipClass.get(ally.alliance_id) || 'Other';
              return (
                <div key={ally.alliance_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.75rem',
                }}>
                  <img
                    src={`https://images.evetech.net/alliances/${ally.alliance_id}/logo?size=32`}
                    alt=""
                    style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                  />
                  <span style={{ color: 'rgba(255,255,255,0.9)', minWidth: '10ch', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ally.alliance_name}
                  </span>
                  <span style={{ color: '#a855f7', marginLeft: 'auto' }}>{shipClass}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Panel 5: Geographic Spread */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderLeft: '2px solid #ffa657',
          borderRadius: '6px',
          padding: '0.75rem',
          overflow: 'hidden',
        }}>
          <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: '#ffa657', fontSize: '0.625rem' }}>●</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.9)', letterSpacing: '0.05em' }}>
              GEOGRAPHIC SPREAD
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            {regions.slice(0, 20).map(allyRegion => {
              const isIsolated = allyRegion.region_count < RED_FLAGS.REGIONS_LOW;
              return (
                <div key={allyRegion.alliance_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.75rem',
                }}>
                  <img
                    src={`https://images.evetech.net/alliances/${allyRegion.alliance_id}/logo?size=32`}
                    alt=""
                    style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                  />
                  <span style={{ color: 'rgba(255,255,255,0.9)', minWidth: '10ch', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {allyRegion.alliance_name}
                  </span>
                  <span style={{ color: isIsolated ? '#f85149' : '#ffa657', marginLeft: 'auto' }}>
                    {allyRegion.region_count} reg {isIsolated && '🔴'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Panel 6: Pilot Engagement */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderLeft: '2px solid #58a6ff',
          borderRadius: '6px',
          padding: '0.75rem',
          overflow: 'hidden',
        }}>
          <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: '#58a6ff', fontSize: '0.625rem' }}>●</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.9)', letterSpacing: '0.05em' }}>
              PILOT ENGAGEMENT
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            {ranking.slice(0, 20).map(ally => {
              const isFeedingAlliance = ally.deaths_per_pilot > RED_FLAGS.DEATHS_PER_PILOT_HIGH;
              return (
                <div key={ally.alliance_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.75rem',
                }}>
                  <img
                    src={`https://images.evetech.net/alliances/${ally.alliance_id}/logo?size=32`}
                    alt=""
                    style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                  />
                  <span style={{ color: 'rgba(255,255,255,0.9)', minWidth: '8ch', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ally.alliance_name}
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: 'auto' }}>
                    {ally.active_pilots} pilots
                  </span>
                  <span style={{ color: isFeedingAlliance ? '#f85149' : 'rgba(255,255,255,0.7)' }}>
                    {ally.deaths_per_pilot.toFixed(1)} d/p {isFeedingAlliance && '🔴'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
