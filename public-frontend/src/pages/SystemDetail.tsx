import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { battleApi } from '../services/api';
import { formatISKCompact } from '../utils/format';

interface ActiveBattleInfo {
  battle_id: number;
  total_kills: number;
  total_isk_destroyed: number;
  started_at: string;
}

interface SystemDanger {
  solarSystemId: number;
  solarSystemName: string;
  regionName: string | null;
  constellationName: string | null;
  security?: number;
  sovAllianceId: number | null;
  sovAllianceName: string | null;
  dangerScore: number;
  kills1H?: number;
  kills24H: number;
  iskDestroyed24H?: number;
  capitalKills: number;
  gateCampRisk?: number;
  activeBattles?: ActiveBattleInfo[];
}

interface SystemKill {
  killmailId: number;
  killmailTime: string;
  shipTypeId: number;
  shipName: string;
  shipValue: number;
  victimName: string | null;
  victimCorporationId: number | null;
  victimCorporationName: string | null;
  victimAllianceId: number | null;
  victimAllianceName: string | null;
  coalitionId: number | null;
  coalitionName: string | null;
  attackerCount: number;
}

interface ShipClassBreakdown {
  system_id: number;
  hours: number;
  total_kills: number;
  group_by: string;
  breakdown: Record<string, number>;
}

interface GroupedData {
  coalition_id: number | null;
  coalition_name: string | null;
  alliances: {
    alliance_id: number | null;
    alliance_name: string | null;
    kills: SystemKill[];
    total_value: number;
  }[];
  total_kills: number;
  total_value: number;
}

const TIMEFRAMES = [
  { value: 10, label: '10m' },
  { value: 60, label: '1h' },
  { value: 720, label: '12h' },
  { value: 1440, label: '24h' },
  { value: 10080, label: '7d' },
];

const SHIP_CLASS_COLORS: Record<string, string> = {
  frigate: '#3fb950',
  destroyer: '#58a6ff',
  cruiser: '#a855f7',
  battlecruiser: '#ff8800',
  battleship: '#ff4444',
  capital: '#ff0000',
  capsule: '#666',
  industrial: '#ffcc00',
  shuttle: '#888',
  deployable: '#00d4ff',
};

function getSecurityColor(sec: number): string {
  if (sec >= 0.5) return '#00ff88';
  if (sec > 0) return '#ffcc00';
  return '#ff4444';
}

function getDangerColor(score: number): string {
  if (score >= 80) return '#ff0000';
  if (score >= 50) return '#ff6600';
  if (score >= 20) return '#ffcc00';
  return '#00ff88';
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h`;
  return `${Math.floor(diffHours / 24)}d`;
}

export function SystemDetail() {
  const { systemId } = useParams<{ systemId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const getInitialTimeframe = () => {
    const minutesParam = searchParams.get('minutes');
    if (minutesParam) {
      const parsed = parseInt(minutesParam, 10);
      if (TIMEFRAMES.some(t => t.value === parsed)) return parsed;
    }
    return 1440;
  };

  const [danger, setDanger] = useState<SystemDanger | null>(null);
  const [kills, setKills] = useState<SystemKill[]>([]);
  const [shipClasses, setShipClasses] = useState<ShipClassBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState(getInitialTimeframe);
  const [expandedCoalitions, setExpandedCoalitions] = useState<Set<string>>(new Set());
  const [expandedAlliances, setExpandedAlliances] = useState<Set<string>>(new Set());

  const toggleCoalition = (id: string) => {
    setExpandedCoalitions(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAlliance = (id: string) => {
    setExpandedAlliances(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  useEffect(() => {
    if (!systemId) return;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const sid = parseInt(systemId);
        const hours = Math.max(1, Math.ceil(timeframe / 60));
        const [dangerData, killsData, classData] = await Promise.all([
          battleApi.getSystemDanger(sid, timeframe),
          battleApi.getSystemKills(sid, 200, timeframe),
          fetch(`/api/war/system/${sid}/ship-classes?hours=${hours}`).then(r => r.json()),
        ]);
        setDanger(dangerData);
        setKills(Array.isArray(killsData) ? killsData : (killsData.kills || []));
        setShipClasses(classData);
      } catch (err) {
        console.error('Failed to fetch system data:', err);
        setError('Failed to load system data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [systemId, timeframe]);

  const groupedData = (): GroupedData[] => {
    const coalitionMap = new Map<number | null, Map<number | null, SystemKill[]>>();
    kills.forEach(kill => {
      if (!coalitionMap.has(kill.coalitionId)) coalitionMap.set(kill.coalitionId, new Map());
      const aMap = coalitionMap.get(kill.coalitionId)!;
      if (!aMap.has(kill.victimAllianceId)) aMap.set(kill.victimAllianceId, []);
      aMap.get(kill.victimAllianceId)!.push(kill);
    });

    const result: GroupedData[] = [];
    coalitionMap.forEach((allianceMap, coalitionId) => {
      const alliances: GroupedData['alliances'] = [];
      let coalitionName: string | null = null;
      let totalKills = 0, totalValue = 0;

      allianceMap.forEach((allianceKills, allianceId) => {
        const tv = allianceKills.reduce((s, k) => s + (k.shipValue || 0), 0);
        alliances.push({ alliance_id: allianceId, alliance_name: allianceKills[0]?.victimAllianceName || null, kills: allianceKills, total_value: tv });
        if (!coalitionName && allianceKills[0]?.coalitionName) coalitionName = allianceKills[0].coalitionName;
        totalKills += allianceKills.length;
        totalValue += tv;
      });
      alliances.sort((a, b) => b.total_value - a.total_value);
      result.push({ coalition_id: coalitionId, coalition_name: coalitionName, alliances, total_kills: totalKills, total_value: totalValue });
    });
    result.sort((a, b) => b.total_value - a.total_value);
    return result;
  };

  const timeframeLabel = TIMEFRAMES.find(t => t.value === timeframe)?.label || '24h';

  if (loading) {
    return (
      <div style={{ padding: '1rem', maxWidth: '1400px', margin: '0 auto' }}>
        <div className="skeleton" style={{ height: '80px', borderRadius: '8px', marginBottom: '0.5rem' }} />
        <div className="skeleton" style={{ height: '300px', borderRadius: '8px' }} />
      </div>
    );
  }

  if (error || !danger) {
    return (
      <div style={{ padding: '1rem', textAlign: 'center' }}>
        <h2 style={{ color: '#ff4444', fontSize: '1rem' }}>System Not Found</h2>
        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem' }}>{error || 'Unable to load system data'}</p>
        <button onClick={() => navigate(-1)} style={{ padding: '0.3rem 0.75rem', background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', fontSize: '0.75rem', cursor: 'pointer' }}>
          Go Back
        </button>
      </div>
    );
  }

  const security = danger.security ?? 0;
  const groups = groupedData();
  const dangerScore = Math.round(danger.dangerScore ?? 0);

  return (
    <div style={{ padding: '1rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Back Button */}
      <button
        onClick={() => navigate(-1)}
        style={{ padding: '0.3rem 0.75rem', background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer', marginBottom: '0.5rem' }}
      >
        &larr; Back
      </button>

      {/* System Header */}
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden', marginBottom: '1rem' }}>
        {/* Main Header Row */}
        <div style={{ padding: '0.75rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          {/* Title + Location */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: '1.25rem', margin: 0, color: '#fff' }}>
              {danger.solarSystemName}
            </h1>
            <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', alignItems: 'center' }}>
              {danger.constellationName && <span>{danger.constellationName}</span>}
              {danger.regionName && <><span style={{ color: 'rgba(255,255,255,0.2)' }}>·</span><span>{danger.regionName}</span></>}
              <span style={{ color: getSecurityColor(security), fontWeight: 600 }}>{security.toFixed(1)}</span>
            </div>
            {/* Danger Badge */}
            <div style={{ padding: '0.25rem 0.5rem', borderRadius: '4px', background: getDangerColor(dangerScore), color: 'white', fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase' }}>
              {dangerScore}
            </div>
            {(danger.gateCampRisk ?? 0) > 50 && (
              <div style={{ padding: '0.2rem 0.4rem', borderRadius: '3px', background: 'rgba(255,68,68,0.2)', color: '#ff4444', fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' }}>
                GATE CAMP
              </div>
            )}
          </div>

          {/* Stats Row */}
          <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
              <span style={{ color: '#ff4444', fontWeight: 700, fontSize: '1.5rem', fontFamily: 'monospace' }}>{danger.kills1H ?? 0}</span>
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>1h</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
              <span style={{ color: '#ff6644', fontWeight: 700, fontSize: '1.5rem', fontFamily: 'monospace' }}>{danger.kills24H}</span>
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>{timeframeLabel}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
              <span style={{ color: '#ffcc00', fontWeight: 700, fontSize: '1.5rem', fontFamily: 'monospace' }}>{formatISKCompact(danger.iskDestroyed24H ?? 0)}</span>
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>ISK</span>
            </div>
            {danger.capitalKills > 0 && (
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
                <span style={{ color: '#a855f7', fontWeight: 700, fontSize: '1.25rem', fontFamily: 'monospace' }}>{danger.capitalKills}</span>
                <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>caps</span>
              </div>
            )}
          </div>
        </div>

        {/* Sov + Timeframe Row */}
        <div style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', background: 'rgba(0,0,0,0.2)' }}>
          {/* Sovereignty */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {danger.sovAllianceId ? (
              <>
                <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>SOV</span>
                <Link to={`/alliance/${danger.sovAllianceId}`} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', textDecoration: 'none' }}>
                  <img src={`https://images.evetech.net/alliances/${danger.sovAllianceId}/logo?size=32`} alt="" style={{ width: 18, height: 18, borderRadius: '3px' }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                  <span style={{ color: '#58a6ff', fontSize: '0.75rem', fontWeight: 600 }}>{danger.sovAllianceName}</span>
                </Link>
              </>
            ) : (
              <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.65rem' }}>No sovereignty</span>
            )}
            {/* Active Battles inline */}
            {danger.activeBattles && danger.activeBattles.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginLeft: '1rem' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#ff4444', animation: 'pulse 2s infinite' }} />
                {danger.activeBattles.map(b => (
                  <Link key={b.battle_id} to={`/battle/${b.battle_id}`} style={{ padding: '0.15rem 0.4rem', borderRadius: '3px', background: 'rgba(255,68,68,0.15)', color: '#ff4444', fontSize: '0.6rem', fontWeight: 600, textDecoration: 'none', whiteSpace: 'nowrap' }}>
                    Battle #{b.battle_id} · {b.total_kills} kills
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Timeframe Selector */}
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            {TIMEFRAMES.map(tf => (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                style={{
                  padding: '0.2rem 0.5rem',
                  borderRadius: '3px',
                  border: timeframe === tf.value ? '1px solid #00d4ff' : '1px solid rgba(255,255,255,0.1)',
                  background: timeframe === tf.value ? 'rgba(0,212,255,0.2)' : 'transparent',
                  color: timeframe === tf.value ? '#00d4ff' : 'rgba(255,255,255,0.5)',
                  cursor: 'pointer',
                  fontSize: '0.65rem',
                  fontWeight: timeframe === tf.value ? 700 : 500,
                }}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content Grid: Ship Classes + Losses */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '0.5rem' }}>
        {/* Left: Ship Classes */}
        <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
          <div style={{ padding: '0.5rem 0.75rem', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ff8800' }} />
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#ff8800', textTransform: 'uppercase' }}>Ship Classes</span>
            {shipClasses && (
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.6rem' }}>{shipClasses.total_kills} kills</span>
            )}
          </div>
          <div style={{ padding: '0.4rem' }}>
            {shipClasses && Object.entries(shipClasses.breakdown).length > 0 ? (
              Object.entries(shipClasses.breakdown).map(([cls, count]) => {
                const pct = shipClasses.total_kills > 0 ? (count / shipClasses.total_kills) * 100 : 0;
                const color = SHIP_CLASS_COLORS[cls] || '#58a6ff';
                return (
                  <div key={cls} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', padding: '0.2rem 0.35rem', marginBottom: '0.1rem' }}>
                    <span style={{ fontSize: '0.65rem', fontWeight: 500, color: 'rgba(255,255,255,0.7)', width: '75px', textTransform: 'capitalize' }}>{cls}</span>
                    <div style={{ flex: 1, height: '10px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: '2px' }} />
                    </div>
                    <span style={{ fontSize: '0.65rem', fontWeight: 700, color, fontFamily: 'monospace', minWidth: '20px', textAlign: 'right' }}>{count}</span>
                  </div>
                );
              })
            ) : (
              <div style={{ textAlign: 'center', padding: '1rem', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>No data</div>
            )}
          </div>
        </div>

        {/* Right: Losses by Power Bloc */}
        <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
          <div style={{ padding: '0.5rem 0.75rem', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00d4ff' }} />
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#00d4ff', textTransform: 'uppercase' }}>Losses by Power Bloc</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.6rem' }}>{timeframeLabel}</span>
          </div>

          {groups.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '1.5rem', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
              No kills in this timeframe
            </div>
          ) : (
            <div style={{ padding: '0.35rem' }}>
              {groups.map(group => {
                const coalitionKey = String(group.coalition_id ?? 'independent');
                const isExpanded = expandedCoalitions.has(coalitionKey);

                return (
                  <div key={coalitionKey} style={{ marginBottom: '0.15rem' }}>
                    {/* Coalition Row */}
                    <div
                      onClick={() => toggleCoalition(coalitionKey)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        padding: '0.3rem 0.5rem',
                        background: group.coalition_id ? 'rgba(168,85,247,0.08)' : 'rgba(0,0,0,0.2)',
                        borderRadius: '4px',
                        borderLeft: `2px solid ${group.coalition_id ? '#a855f7' : 'rgba(255,255,255,0.15)'}`,
                        cursor: 'pointer',
                      }}
                    >
                      <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }}>▶</span>
                      {group.coalition_id ? (
                        <img src={`https://images.evetech.net/alliances/${group.coalition_id}/logo?size=32`} alt="" style={{ width: 18, height: 18, borderRadius: '3px' }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                      ) : (
                        <span style={{ width: 18, height: 18, borderRadius: '3px', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.6rem' }}>?</span>
                      )}
                      <span style={{ flex: 1, fontWeight: 600, fontSize: '0.75rem', color: group.coalition_id ? '#a855f7' : 'rgba(255,255,255,0.6)' }}>
                        {group.coalition_name || 'Independent / Unaffiliated'}
                      </span>
                      <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>{group.alliances.length}a</span>
                      <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>{group.total_kills}</span>
                      <span style={{ fontSize: '0.65rem', color: '#ffcc00', fontFamily: 'monospace' }}>{formatISKCompact(group.total_value)}</span>
                    </div>

                    {/* Alliances */}
                    {isExpanded && (
                      <div style={{ paddingLeft: '1.25rem', marginTop: '0.1rem' }}>
                        {group.alliances.map(alliance => {
                          const allianceKey = `${coalitionKey}-${alliance.alliance_id ?? 'nocorp'}`;
                          const isAllianceExpanded = expandedAlliances.has(allianceKey);

                          return (
                            <div key={allianceKey} style={{ marginBottom: '0.1rem' }}>
                              {/* Alliance Row */}
                              <div
                                onClick={() => toggleAlliance(allianceKey)}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.35rem',
                                  padding: '0.25rem 0.4rem',
                                  background: 'rgba(0,0,0,0.15)',
                                  borderRadius: '4px',
                                  borderLeft: '2px solid rgba(88,166,255,0.3)',
                                  cursor: 'pointer',
                                }}
                              >
                                <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.3)', transform: isAllianceExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }}>▶</span>
                                {alliance.alliance_id && (
                                  <img src={`https://images.evetech.net/alliances/${alliance.alliance_id}/logo?size=32`} alt="" style={{ width: 16, height: 16, borderRadius: '2px' }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                                )}
                                <span style={{ flex: 1, fontSize: '0.7rem', fontWeight: 500, color: 'rgba(255,255,255,0.8)' }}>
                                  {alliance.alliance_name || 'No Alliance'}
                                </span>
                                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff6644', fontFamily: 'monospace' }}>{alliance.kills.length}</span>
                                <span style={{ fontSize: '0.6rem', color: '#ffcc00', fontFamily: 'monospace' }}>{formatISKCompact(alliance.total_value)}</span>
                              </div>

                              {/* Kill List */}
                              {isAllianceExpanded && (
                                <div style={{ paddingLeft: '1rem', marginTop: '0.1rem' }}>
                                  {alliance.kills.slice(0, 10).map(kill => (
                                    <a
                                      key={kill.killmailId}
                                      href={`https://zkillboard.com/kill/${kill.killmailId}/`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.35rem',
                                        padding: '0.2rem 0.35rem',
                                        borderRadius: '3px',
                                        textDecoration: 'none',
                                        color: 'inherit',
                                        marginBottom: '0.1rem',
                                        borderLeft: '2px solid rgba(255,255,255,0.06)',
                                      }}
                                    >
                                      <img src={`https://images.evetech.net/types/${kill.shipTypeId}/icon?size=32`} alt="" style={{ width: 18, height: 18, borderRadius: '2px', flexShrink: 0 }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                                      <span style={{ flex: 1, fontSize: '0.65rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {kill.shipName}
                                        <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.35rem' }}>{kill.victimName || 'Unknown'}</span>
                                      </span>
                                      <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', minWidth: '25px', textAlign: 'right' }}>{formatTimeAgo(kill.killmailTime)}</span>
                                      <span style={{ fontSize: '0.6rem', fontWeight: 600, color: '#ffcc00', fontFamily: 'monospace', minWidth: '40px', textAlign: 'right' }}>{formatISKCompact(kill.shipValue)}</span>
                                    </a>
                                  ))}
                                  {alliance.kills.length > 10 && (
                                    <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', textAlign: 'center', padding: '0.15rem' }}>
                                      +{alliance.kills.length - 10} more
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
