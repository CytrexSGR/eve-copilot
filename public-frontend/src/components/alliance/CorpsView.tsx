import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  getCorpsRanking,
  getCorpsTrends,
  getCorpsShips,
  getCorpsRegions,
  type CorpRanking,
  type CorpTrend,
  type CorpShipClass,
  type CorpRegion,
} from '../../services/allianceApi';

interface CorpsViewProps {
  allianceId: number;
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

interface ProblemCorp {
  corp: CorpRanking;
  flags: string[];
}

export const CorpsView: React.FC<CorpsViewProps> = ({ allianceId, days }) => {
  const [ranking, setRanking] = useState<CorpRanking[]>([]);
  const [trends, setTrends] = useState<CorpTrend[]>([]);
  const [ships, setShips] = useState<CorpShipClass[]>([]);
  const [regions, setRegions] = useState<CorpRegion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [rankingData, trendsData, shipsData, regionsData] = await Promise.all([
          getCorpsRanking(allianceId, days),
          getCorpsTrends(allianceId, days),
          getCorpsShips(allianceId, days),
          getCorpsRegions(allianceId, days),
        ]);
        setRanking(rankingData);
        setTrends(trendsData);
        setShips(shipsData);
        setRegions(regionsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load corps data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [allianceId, days]);

  // Detect problem corps
  const problemCorps = useMemo((): ProblemCorp[] => {
    if (!ranking.length) return [];

    const problems: ProblemCorp[] = [];

    ranking.forEach(corp => {
      const flags: string[] = [];

      if (corp.efficiency < RED_FLAGS.EFFICIENCY_LOW) {
        flags.push(`Low Efficiency: ${corp.efficiency}%`);
      }
      if (corp.activity_share_pct < RED_FLAGS.ACTIVITY_LOW) {
        flags.push(`Dead Weight: ${corp.activity_share_pct}% activity`);
      }
      if (corp.deaths_per_pilot > RED_FLAGS.DEATHS_PER_PILOT_HIGH) {
        flags.push(`High Deaths: ${corp.deaths_per_pilot.toFixed(1)}/pilot`);
      }

      // Check region count (if available)
      const corpRegion = regions.find(r => r.corp_id === corp.corp_id);
      if (corpRegion && corpRegion.region_count < RED_FLAGS.REGIONS_LOW) {
        flags.push(`Isolated: ${corpRegion.region_count} regions`);
      }

      if (flags.length > 0) {
        problems.push({ corp, flags });
      }
    });

    return problems.sort((a, b) => b.flags.length - a.flags.length);
  }, [ranking, regions]);

  // Get top and bottom corps (show all with scroll)
  const topCorps = useMemo(() => ranking.slice(0, Math.ceil(ranking.length / 2)), [ranking]);
  const bottomCorps = useMemo(() => ranking.slice(Math.ceil(ranking.length / 2)).reverse(), [ranking]);

  // Get dominant ship class per corp
  const corpShipClass = useMemo(() => {
    const map = new Map<number, string>();
    ships.forEach(entry => {
      if (!map.has(entry.corp_id)) {
        map.set(entry.corp_id, entry.ship_class);
      }
    });
    return map;
  }, [ships]);

  // Group trends by corp for sparklines
  const corpTrendsMap = useMemo(() => {
    const map = new Map<number, CorpTrend[]>();
    trends.forEach(trend => {
      if (!map.has(trend.corp_id)) {
        map.set(trend.corp_id, []);
      }
      map.get(trend.corp_id)!.push(trend);
    });
    // Sort by date for each corp
    map.forEach(corpTrends => {
      corpTrends.sort((a, b) => a.day.localeCompare(b.day));
    });
    return map;
  }, [trends]);

  // Calculate trend indicator (⬆️⬇️→)
  const getTrendIndicator = (corpId: number): string => {
    const corpTrends = corpTrendsMap.get(corpId);
    if (!corpTrends || corpTrends.length < 4) return '→';

    const first3 = corpTrends.slice(0, 3).reduce((sum, t) => sum + t.efficiency, 0) / 3;
    const last3 = corpTrends.slice(-3).reduce((sum, t) => sum + t.efficiency, 0) / 3;
    const diff = last3 - first3;

    if (diff > 10) return '⬆️';
    if (diff < -10) return '⬇️';
    return '→';
  };

  // Simple sparkline (text-based)
  const getSparkline = (corpId: number): string => {
    const corpTrends = corpTrendsMap.get(corpId);
    if (!corpTrends || corpTrends.length < 2) return '▄▄▄▄▄▄▄';

    const values = corpTrends.map(t => t.efficiency);
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
        <div style={{ color: 'rgba(255,255,255,0.5)' }}>Loading corporations intel...</div>
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Panel 1: Problem Corps Alert */}
      {problemCorps.length > 0 && (
        <div style={{
          background: 'rgba(248, 81, 73, 0.1)',
          border: '1px solid rgba(248, 81, 73, 0.3)',
          borderRadius: '6px',
          padding: '0.5rem 0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f85149' }}>
              ⚠️ PROBLEM CORPS DETECTED ({problemCorps.length})
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            {problemCorps.slice(0, 5).map(({ corp, flags }) => (
              <div key={corp.corp_id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.75rem',
              }}>
                <img
                  src={`https://images.evetech.net/corporations/${corp.corp_id}/logo?size=32`}
                  alt=""
                  style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                />
                <span style={{ color: '#f85149', minWidth: '12ch' }}>{corp.corporation_name}</span>
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

        {/* Horizontal Grid: Top 5 | Bottom 5 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', overflowY: 'auto', flex: 1 }}>
          {/* Top Performers */}
          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#3fb950', marginBottom: '0.5rem' }}>
              TOP PERFORMERS (Carry)
            </div>
            {topCorps.map(corp => {
              const formatISK = (isk: number) => {
                if (isk >= 1e12) return `${(isk / 1e12).toFixed(1)}T`;
                if (isk >= 1e9) return `${(isk / 1e9).toFixed(1)}B`;
                return `${(isk / 1e6).toFixed(0)}M`;
              };
              const shipClass = corpShipClass.get(corp.corp_id) || 'Mixed';
              const corpRegion = regions.find(r => r.corp_id === corp.corp_id);

              return (
                <Link
                  key={corp.corp_id}
                  to={`/corporation/${corp.corp_id}`}
                  style={{
                    display: 'block',
                    padding: '0.4rem 0.5rem',
                    marginBottom: '0.3rem',
                    borderRadius: '4px',
                    background: 'rgba(63, 185, 80, 0.08)',
                    border: '1px solid rgba(63, 185, 80, 0.2)',
                    textDecoration: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(63, 185, 80, 0.15)';
                    e.currentTarget.style.borderColor = 'rgba(63, 185, 80, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(63, 185, 80, 0.08)';
                    e.currentTarget.style.borderColor = 'rgba(63, 185, 80, 0.2)';
                  }}
                >
                  {/* Row 1: Logo + Name + Activity% */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                    <img
                      src={`https://images.evetech.net/corporations/${corp.corp_id}/logo?size=32`}
                      alt=""
                      style={{ width: '20px', height: '20px', borderRadius: '2px' }}
                    />
                    <span style={{ color: '#3fb950', fontSize: '0.75rem', fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {corp.corporation_name}
                    </span>
                    <span style={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: '#3fb950',
                      background: 'rgba(63, 185, 80, 0.15)',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '3px',
                    }}>
                      {corp.activity_share_pct.toFixed(1)}%
                    </span>
                  </div>

                  {/* Row 2: Metrics */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.7rem', flexWrap: 'wrap' }}>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>K/D:</span>{' '}
                      <span style={{ color: getKDColor(corp.deaths > 0 ? corp.kills / corp.deaths : corp.kills), fontWeight: 600 }}>
                        {corp.deaths > 0 ? (corp.kills / corp.deaths).toFixed(2) : corp.kills.toFixed(0)}
                      </span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>Eff:</span>{' '}
                      <span style={{ color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>{corp.efficiency.toFixed(0)}%</span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>ISK:</span>{' '}
                      <span style={{ color: '#3fb950' }}>{formatISK(corp.isk_killed)}</span>
                      <span style={{ color: 'rgba(255,255,255,0.3)' }}>/</span>
                      <span style={{ color: '#f85149' }}>{formatISK(corp.isk_lost)}</span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>Pilots:</span>{' '}
                      <span style={{ color: 'rgba(255,255,255,0.9)' }}>{corp.active_pilots}</span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>Class:</span>{' '}
                      <span style={{ color: '#a855f7' }}>{shipClass}</span>
                    </div>
                    {corpRegion && (
                      <>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                        <div>
                          <span style={{ color: 'rgba(255,255,255,0.5)' }}>Regions:</span>{' '}
                          <span style={{ color: corpRegion.region_count < RED_FLAGS.REGIONS_LOW ? '#f85149' : '#ffa657' }}>
                            {corpRegion.region_count}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#f85149', marginBottom: '0.5rem' }}>
              BOTTOM PERFORMERS (Dead Weight)
            </div>
            {bottomCorps.map(corp => {
              const formatISK = (isk: number) => {
                if (isk >= 1e12) return `${(isk / 1e12).toFixed(1)}T`;
                if (isk >= 1e9) return `${(isk / 1e9).toFixed(1)}B`;
                return `${(isk / 1e6).toFixed(0)}M`;
              };
              const shipClass = corpShipClass.get(corp.corp_id) || 'Mixed';
              const corpRegion = regions.find(r => r.corp_id === corp.corp_id);

              return (
                <Link
                  key={corp.corp_id}
                  to={`/corporation/${corp.corp_id}`}
                  style={{
                    display: 'block',
                    padding: '0.4rem 0.5rem',
                    marginBottom: '0.3rem',
                    borderRadius: '4px',
                    background: 'rgba(248, 81, 73, 0.08)',
                    border: '1px solid rgba(248, 81, 73, 0.2)',
                    textDecoration: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(248, 81, 73, 0.15)';
                    e.currentTarget.style.borderColor = 'rgba(248, 81, 73, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(248, 81, 73, 0.08)';
                    e.currentTarget.style.borderColor = 'rgba(248, 81, 73, 0.2)';
                  }}
                >
                  {/* Row 1: Logo + Name + Activity% */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                    <img
                      src={`https://images.evetech.net/corporations/${corp.corp_id}/logo?size=32`}
                      alt=""
                      style={{ width: '20px', height: '20px', borderRadius: '2px' }}
                    />
                    <span style={{ color: '#f85149', fontSize: '0.75rem', fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {corp.corporation_name}
                    </span>
                    <span style={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: '#f85149',
                      background: 'rgba(248, 81, 73, 0.15)',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '3px',
                    }}>
                      {corp.activity_share_pct.toFixed(1)}%
                    </span>
                  </div>

                  {/* Row 2: Metrics */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.7rem', flexWrap: 'wrap' }}>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>K/D:</span>{' '}
                      <span style={{ color: getKDColor(corp.deaths > 0 ? corp.kills / corp.deaths : corp.kills), fontWeight: 600 }}>
                        {corp.deaths > 0 ? (corp.kills / corp.deaths).toFixed(2) : corp.kills.toFixed(0)}
                      </span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>Eff:</span>{' '}
                      <span style={{ color: corp.efficiency < 40 ? '#f85149' : 'rgba(255,255,255,0.9)', fontWeight: 600 }}>{corp.efficiency.toFixed(0)}%</span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>ISK:</span>{' '}
                      <span style={{ color: '#3fb950' }}>{formatISK(corp.isk_killed)}</span>
                      <span style={{ color: 'rgba(255,255,255,0.3)' }}>/</span>
                      <span style={{ color: '#f85149' }}>{formatISK(corp.isk_lost)}</span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>Pilots:</span>{' '}
                      <span style={{ color: 'rgba(255,255,255,0.9)' }}>{corp.active_pilots}</span>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}> ({corp.deaths_per_pilot.toFixed(1)} d/p{corp.deaths_per_pilot > RED_FLAGS.DEATHS_PER_PILOT_HIGH && ' 🔴'})</span>
                    </div>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                    <div>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>Class:</span>{' '}
                      <span style={{ color: '#a855f7' }}>{shipClass}</span>
                    </div>
                    {corpRegion && (
                      <>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                        <div>
                          <span style={{ color: 'rgba(255,255,255,0.5)' }}>Regions:</span>{' '}
                          <span style={{ color: corpRegion.region_count < RED_FLAGS.REGIONS_LOW ? '#f85149' : '#ffa657' }}>
                            {corpRegion.region_count}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </Link>
              );
            })}
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

        {/* Horizontal grid of trend cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.5rem', overflowY: 'auto', flex: 1 }}>
          {ranking.map(corp => {
            const indicator = getTrendIndicator(corp.corp_id);
            const sparkline = getSparkline(corp.corp_id);
            const isImproving = indicator === '⬆️';
            const isDeclining = indicator === '⬇️';
            const corpTrends = corpTrendsMap.get(corp.corp_id) || [];
            const recentActivity = corpTrends.slice(-3).reduce((sum, t) => sum + t.activity, 0);
            const shipClass = corpShipClass.get(corp.corp_id) || 'Mixed';
            const formatISK = (isk: number) => {
              if (isk >= 1e12) return `${(isk / 1e12).toFixed(1)}T`;
              if (isk >= 1e9) return `${(isk / 1e9).toFixed(1)}B`;
              return `${(isk / 1e6).toFixed(0)}M`;
            };

            return (
              <Link
                key={corp.corp_id}
                to={`/corporation/${corp.corp_id}`}
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
                    src={`https://images.evetech.net/corporations/${corp.corp_id}/logo?size=32`}
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
                    {corp.corporation_name}
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
                    color: corp.efficiency >= 50 ? '#3fb950' : corp.efficiency < 40 ? '#f85149' : 'rgba(255,255,255,0.9)',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                  }}>
                    {corp.efficiency.toFixed(0)}%
                  </span>
                </div>

                {/* Row 3: Detailed Metrics */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.7rem', flexWrap: 'wrap' }}>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>K/D:</span>{' '}
                    <span style={{ color: getKDColor(corp.deaths > 0 ? corp.kills / corp.deaths : corp.kills), fontWeight: 600 }}>
                      {corp.deaths > 0 ? (corp.kills / corp.deaths).toFixed(2) : corp.kills.toFixed(0)}
                    </span>
                  </div>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>ISK:</span>{' '}
                    <span style={{ color: '#3fb950' }}>{formatISK(corp.isk_killed)}</span>
                  </div>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>3d:</span>{' '}
                    <span style={{ color: 'rgba(255,255,255,0.9)' }}>{recentActivity}</span>
                  </div>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
                  <div>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>Pilots:</span>{' '}
                    <span style={{ color: 'rgba(255,255,255,0.9)' }}>{corp.active_pilots}</span>
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
        {/* Panel 4: Ship Specialization (simplified) */}
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
            {ranking.slice(0, 15).map(corp => {
              const shipClass = corpShipClass.get(corp.corp_id) || 'Other';
              return (
                <div key={corp.corp_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.75rem',
                }}>
                  <img
                    src={`https://images.evetech.net/corporations/${corp.corp_id}/logo?size=32`}
                    alt=""
                    style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                  />
                  <span style={{ color: 'rgba(255,255,255,0.9)', minWidth: '10ch', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {corp.corporation_name}
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
            {regions.slice(0, 20).map(corpRegion => {
              const isIsolated = corpRegion.region_count < RED_FLAGS.REGIONS_LOW;
              return (
                <div key={corpRegion.corp_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.75rem',
                }}>
                  <img
                    src={`https://images.evetech.net/corporations/${corpRegion.corp_id}/logo?size=32`}
                    alt=""
                    style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                  />
                  <span style={{ color: 'rgba(255,255,255,0.9)', minWidth: '10ch', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {corpRegion.corporation_name}
                  </span>
                  <span style={{ color: isIsolated ? '#f85149' : '#ffa657', marginLeft: 'auto' }}>
                    {corpRegion.region_count} reg {isIsolated && '🔴'}
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
            {ranking.slice(0, 20).map(corp => {
              const isFeedingCorp = corp.deaths_per_pilot > RED_FLAGS.DEATHS_PER_PILOT_HIGH;
              return (
                <div key={corp.corp_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.75rem',
                }}>
                  <img
                    src={`https://images.evetech.net/corporations/${corp.corp_id}/logo?size=32`}
                    alt=""
                    style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                  />
                  <span style={{ color: 'rgba(255,255,255,0.9)', minWidth: '8ch', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {corp.corporation_name}
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: 'auto' }}>
                    {corp.active_pilots} pilots
                  </span>
                  <span style={{ color: isFeedingCorp ? '#f85149' : 'rgba(255,255,255,0.7)' }}>
                    {corp.deaths_per_pilot.toFixed(1)} d/p {isFeedingCorp && '🔴'}
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
