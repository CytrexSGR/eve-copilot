import { useEffect, useState } from 'react';
import { formatISK } from '../../utils/format';
import type { WarEconomy } from '../../types/reports';

interface CombatTabProps {
  report: WarEconomy;
  timeframeMinutes?: number;
}

interface HotSystem {
  solar_system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  kill_count: number;
  total_value: number;
  capital_kills: number;
  last_kill_minutes_ago: number | null;
  threat_level: 'critical' | 'hot' | 'active' | 'low';
  sov_alliance_id: number | null;
  sov_alliance_name: string | null;
  sov_alliance_ticker: string | null;
}

interface HotSystemsResponse {
  minutes: number;
  systems: HotSystem[];
  generated_at: string;
}

interface CapitalAlliance {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  total_caps: number;
  titans: number;
  supers: number;
  dreads: number;
}

interface CapitalIntelResponse {
  days: number;
  summary: {
    total_engagements: number;
    unique_alliances: number;
    systems_active: number;
  };
  top_alliances: CapitalAlliance[];
}

const THREAT_CONFIG = {
  critical: { color: '#ff0000', bg: 'rgba(255,0,0,0.15)', label: 'CRIT' },
  hot: { color: '#ff6600', bg: 'rgba(255,102,0,0.12)', label: 'HOT' },
  active: { color: '#ffcc00', bg: 'rgba(255,204,0,0.08)', label: 'ACTIVE' },
  low: { color: '#888888', bg: 'rgba(136,136,136,0.05)', label: 'LOW' },
};

export function CombatTab({ report, timeframeMinutes = 60 }: CombatTabProps) {
  const [hotSystems, setHotSystems] = useState<HotSystem[]>([]);
  const [capitalIntel, setCapitalIntel] = useState<CapitalIntelResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Convert minutes to days for capital intel (min 1 day)
  const capitalDays = Math.max(1, Math.ceil(timeframeMinutes / 1440));

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [hotRes, capRes] = await Promise.all([
          fetch(`/api/war/hot-systems?minutes=${timeframeMinutes}&limit=50`),
          fetch(`/api/war/economy/capital-intel?days=${capitalDays}`)
        ]);

        if (hotRes.ok) {
          const data: HotSystemsResponse = await hotRes.json();
          setHotSystems(data.systems);
        }

        if (capRes.ok) {
          const data: CapitalIntelResponse = await capRes.json();
          setCapitalIntel(data);
        }
      } catch (err) {
        console.error('Failed to fetch combat data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeframeMinutes, capitalDays]);

  return (
    <>
      {/* TOP ROW: 3 Columns */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: '0.75rem',
        marginBottom: '0.75rem'
      }}>
        {/* Column 1: Combat Hotspots */}
        <CombatHotspotsPanel systems={hotSystems} loading={loading} />

        {/* Column 2: Regional Losses - aggregated from hot systems */}
        <RegionalLossesPanel systems={hotSystems} timeframeMinutes={timeframeMinutes} loading={loading} />

        {/* Column 3: Capital Activity */}
        <CapitalActivityPanel intel={capitalIntel} loading={loading} days={capitalDays} />
      </div>

      {/* Full Width: Doctrine Demand */}
      <div style={{ marginBottom: '0.75rem' }}>
        <DoctrineDemandPanel report={report} />
      </div>

      {/* Full Width: Top Ships Lost */}
      <TopShipsLostPanel report={report} />
    </>
  );
}

// ============================================================
// COMBAT HOTSPOTS PANEL (Compact)
// ============================================================

function CombatHotspotsPanel({ systems, loading }: { systems: HotSystem[]; loading: boolean }) {
  const criticalCount = systems.filter(s => s.threat_level === 'critical').length;
  const hotCount = systems.filter(s => s.threat_level === 'hot').length;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      height: '340px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>🔥</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase' }}>
            Combat Hotspots
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.6rem' }}>
          {criticalCount > 0 && <span style={{ color: '#ff0000' }}>{criticalCount} crit</span>}
          {hotCount > 0 && <span style={{ color: '#ff6600' }}>{hotCount} hot</span>}
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>{systems.length} sys</span>
        </div>
      </div>

      {/* Systems List */}
      <div style={{ padding: '0.25rem', flex: 1, overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
            Loading...
          </div>
        ) : systems.length === 0 ? (
          <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
            No active combat zones
          </div>
        ) : (
          systems.slice(0, 12).map((sys, idx) => {
            const config = THREAT_CONFIG[sys.threat_level];
            return (
              <div
                key={sys.solar_system_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.35rem 0.4rem',
                  marginBottom: idx < 11 ? '0.15rem' : 0,
                  background: config.bg,
                  borderRadius: '4px',
                  borderLeft: `2px solid ${config.color}`,
                }}
              >
                {/* Threat Badge */}
                <span style={{ fontSize: '0.6rem', fontWeight: 700, color: config.color, minWidth: '42px' }}>
                  {config.label}
                </span>

                {/* System Info */}
                <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.7rem', color: '#fff' }}>{sys.system_name}</span>
                  <span style={{ fontSize: '0.6rem', color: getSecurityColor(sys.security_status), fontFamily: 'monospace' }}>
                    {sys.security_status.toFixed(1)}
                  </span>
                  <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.35)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {sys.region_name}
                  </span>
                  {sys.sov_alliance_ticker && (
                    <span style={{ fontSize: '0.6rem', color: '#00d4ff' }}>[{sys.sov_alliance_ticker}]</span>
                  )}
                </div>

                {/* Stats */}
                <span style={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace', color: config.color }}>
                  {sys.kill_count}
                </span>
                <span style={{ fontSize: '0.65rem', color: '#ffcc00', fontFamily: 'monospace', minWidth: '45px', textAlign: 'right' }}>
                  {formatISK(sys.total_value)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============================================================
// REGIONAL LOSSES PANEL (Compact) - Aggregated from Hot Systems
// ============================================================

interface RegionalLossesPanelProps {
  systems: HotSystem[];
  timeframeMinutes: number;
  loading: boolean;
}

function RegionalLossesPanel({ systems, timeframeMinutes, loading }: RegionalLossesPanelProps) {
  // Aggregate hot systems by region
  const regionMap = new Map<string, { kills: number; isk: number }>();
  systems.forEach(sys => {
    const existing = regionMap.get(sys.region_name) || { kills: 0, isk: 0 };
    existing.kills += sys.kill_count;
    existing.isk += sys.total_value;
    regionMap.set(sys.region_name, existing);
  });

  const regions = Array.from(regionMap.entries())
    .map(([name, data]) => ({ region_name: name, kills: data.kills, isk_destroyed: data.isk }))
    .sort((a, b) => b.kills - a.kills)
    .slice(0, 8);

  const totalKills = regions.reduce((sum, r) => sum + r.kills, 0);
  const totalIsk = regions.reduce((sum, r) => sum + r.isk_destroyed, 0);

  const timeLabel = timeframeMinutes < 60 ? `${timeframeMinutes}m` :
                    timeframeMinutes < 1440 ? `${timeframeMinutes / 60}h` :
                    `${timeframeMinutes / 1440}d`;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      height: '340px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>💀</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase' }}>
            Regional Losses
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>{timeLabel}</span>
      </div>

      {/* Summary Stats - Compact */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        display: 'flex',
        gap: '1rem',
      }}>
        <div>
          <span style={{ fontSize: '1rem', fontWeight: 800, color: '#ff4444', fontFamily: 'monospace' }}>
            {totalKills.toLocaleString()}
          </span>
          <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.3rem', textTransform: 'uppercase' }}>
            Total Kills
          </span>
        </div>
        <div>
          <span style={{ fontSize: '1rem', fontWeight: 800, color: '#ffcc00', fontFamily: 'monospace' }}>
            {formatISK(totalIsk)}
          </span>
          <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.3rem', textTransform: 'uppercase' }}>
            ISK Destroyed
          </span>
        </div>
      </div>

      {/* Regional Breakdown */}
      <div style={{ padding: '0.25rem', flex: 1, overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
            Loading...
          </div>
        ) : regions.length === 0 ? (
          <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
            No regional activity
          </div>
        ) : (
          regions.map((region, idx) => {
            const intensity = idx === 0 ? 1 : idx < 3 ? 0.6 : 0.3;
            return (
              <div
                key={region.region_name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.35rem 0.4rem',
                  marginBottom: idx < regions.length - 1 ? '0.15rem' : 0,
                  background: `rgba(168, 85, 247, ${0.05 * intensity})`,
                  borderRadius: '4px',
                  borderLeft: `2px solid rgba(168, 85, 247, ${intensity})`,
                }}
              >
                <span style={{ flex: 1, fontSize: '0.7rem', color: '#fff', fontWeight: 600 }}>{region.region_name}</span>
                <span style={{ fontSize: '0.75rem', color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>
                  {region.kills}
                </span>
                <span style={{ fontSize: '0.65rem', color: '#ffcc00', fontFamily: 'monospace', minWidth: '50px', textAlign: 'right' }}>
                  {formatISK(region.isk_destroyed)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============================================================
// CAPITAL ACTIVITY PANEL (Compact)
// ============================================================

function CapitalActivityPanel({ intel, loading, days }: { intel: CapitalIntelResponse | null; loading: boolean; days: number }) {
  const timeLabel = days === 1 ? '24h' : `${days}d`;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      height: '340px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>⚓</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#00d4ff', textTransform: 'uppercase' }}>
            Capital Activity
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>{timeLabel}</span>
      </div>

      {loading || !intel ? (
        <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem', flex: 1 }}>
          {loading ? 'Loading...' : 'No capital intel'}
        </div>
      ) : (
        <>
          {/* Summary Stats - Compact inline */}
          <div style={{
            padding: '0.4rem 0.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            display: 'flex',
            gap: '0.75rem',
          }}>
            <div>
              <span style={{ fontSize: '0.9rem', fontWeight: 800, color: '#00d4ff', fontFamily: 'monospace' }}>{intel.summary.total_engagements}</span>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>ops</span>
            </div>
            <div>
              <span style={{ fontSize: '0.9rem', fontWeight: 800, color: '#a855f7', fontFamily: 'monospace' }}>{intel.summary.unique_alliances}</span>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>alliances</span>
            </div>
            <div>
              <span style={{ fontSize: '0.9rem', fontWeight: 800, color: '#00ff88', fontFamily: 'monospace' }}>{intel.summary.systems_active}</span>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>systems</span>
            </div>
          </div>

          {/* Top Alliances */}
          <div style={{ padding: '0.25rem', flex: 1, overflowY: 'auto' }}>
            {intel.top_alliances.slice(0, 10).map((alliance, idx) => (
              <div
                key={alliance.alliance_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  padding: '0.25rem 0.4rem',
                  marginBottom: idx < 9 ? '0.1rem' : 0,
                  background: idx === 0 ? 'rgba(0, 212, 255, 0.08)' : 'rgba(0, 212, 255, 0.03)',
                  borderRadius: '4px',
                  borderLeft: `2px solid rgba(0, 212, 255, ${idx === 0 ? 1 : 0.4})`,
                }}
              >
                {/* Alliance Name - truncated */}
                <div style={{
                  flex: 1,
                  minWidth: 0,
                  fontSize: '0.65rem',
                  color: '#fff',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  [{alliance.ticker}] {alliance.alliance_name}
                </div>
                {/* Capital Badges inline */}
                <div style={{ display: 'flex', gap: '0.2rem', flexShrink: 0 }}>
                  {alliance.titans > 0 && <CapitalBadge type="T" count={alliance.titans} color="#ff2222" />}
                  {alliance.supers > 0 && <CapitalBadge type="S" count={alliance.supers} color="#ff8800" />}
                  {alliance.dreads > 0 && <CapitalBadge type="D" count={alliance.dreads} color="#00d4ff" />}
                </div>
                {/* Total */}
                <span style={{ fontSize: '0.75rem', color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace', minWidth: '28px', textAlign: 'right' }}>
                  {alliance.total_caps}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function CapitalBadge({ type, count, color }: { type: string; count: number; color: string }) {
  return (
    <span style={{
      fontSize: '0.5rem',
      fontWeight: 700,
      padding: '0.1rem 0.25rem',
      background: `${color}22`,
      color: color,
      borderRadius: '2px',
      fontFamily: 'monospace'
    }}>
      {type}:{count}
    </span>
  );
}

// ============================================================
// DOCTRINE DEMAND PANEL (Compact Full Width)
// ============================================================

function DoctrineDemandPanel({ report }: { report: WarEconomy }) {
  const doctrineHints: Map<string, { count: number; regions: string[] }> = new Map();

  report.fleet_compositions.forEach(fc => {
    fc.doctrine_hints?.forEach(hint => {
      const existing = doctrineHints.get(hint);
      if (existing) {
        existing.count++;
        if (!existing.regions.includes(fc.region_name)) {
          existing.regions.push(fc.region_name);
        }
      } else {
        doctrineHints.set(hint, { count: 1, regions: [fc.region_name] });
      }
    });
  });

  const sortedDoctrines = Array.from(doctrineHints.entries())
    .sort((a, b) => b[1].count - a[1].count);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>📋</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#00ff88', textTransform: 'uppercase' }}>
            Doctrine Demand
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          Detected from fleet compositions across {report.fleet_compositions.length} regions
        </span>
      </div>

      {/* Doctrine Tags */}
      <div style={{ padding: '0.4rem 0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
        {sortedDoctrines.length === 0 ? (
          <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>No doctrine patterns detected</span>
        ) : (
          sortedDoctrines.map(([doctrine, data]) => {
            const color = doctrine.includes('Capital') ? '#ff4444' :
                         doctrine.includes('HAC') ? '#a855f7' :
                         doctrine.includes('Logistics') ? '#00ff88' :
                         doctrine.includes('Battleship') ? '#ff8800' :
                         doctrine.includes('Destroyer') ? '#00d4ff' : '#ffcc00';
            return (
              <span
                key={doctrine}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.3rem',
                  padding: '0.3rem 0.5rem',
                  background: `${color}15`,
                  borderRadius: '4px',
                  border: `1px solid ${color}33`,
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: color,
                  textTransform: 'uppercase'
                }}
              >
                {doctrine}
                <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)', background: 'rgba(0,0,0,0.3)', padding: '0 0.25rem', borderRadius: '2px' }}>
                  {data.count} region{data.count > 1 ? 's' : ''}
                </span>
              </span>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============================================================
// TOP SHIPS LOST PANEL (Compact Full Width)
// ============================================================

function TopShipsLostPanel({ report }: { report: WarEconomy }) {
  const hullStats: Map<string, { losses: number; ship_class: string }> = new Map();

  report.fleet_compositions.forEach(fc => {
    fc.top_hulls?.forEach(hull => {
      const existing = hullStats.get(hull.ship_name);
      if (existing) {
        existing.losses += hull.losses;
      } else {
        hullStats.set(hull.ship_name, { losses: hull.losses, ship_class: hull.ship_class });
      }
    });
  });

  const sortedHulls = Array.from(hullStats.entries())
    .sort((a, b) => b[1].losses - a[1].losses)
    .slice(0, 10);

  const maxLosses = sortedHulls[0]?.[1].losses || 1;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>🚀</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff8800', textTransform: 'uppercase' }}>
            Top Ships Lost
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          Aggregated across all active regions
        </span>
      </div>

      {/* Ships Grid */}
      <div style={{ padding: '0.4rem 0.5rem', display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.35rem' }}>
        {sortedHulls.length === 0 ? (
          <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem', gridColumn: '1 / -1' }}>No ship loss data</span>
        ) : (
          sortedHulls.map(([shipName, data]) => {
            const barWidth = (data.losses / maxLosses) * 100;
            const shipClassColor =
              data.ship_class?.includes('Titan') ? '#ff2222' :
              data.ship_class?.includes('Supercarrier') ? '#ff4444' :
              data.ship_class?.includes('Dreadnought') || data.ship_class?.includes('Carrier') ? '#ff8800' :
              data.ship_class?.includes('Battleship') ? '#ffcc00' :
              data.ship_class?.includes('Cruiser') ? '#a855f7' :
              data.ship_class?.includes('Frigate') || data.ship_class?.includes('Destroyer') ? '#00d4ff' :
              '#888888';

            return (
              <div
                key={shipName}
                style={{
                  position: 'relative',
                  padding: '0.35rem 0.4rem',
                  background: 'rgba(0,0,0,0.2)',
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}
              >
                {/* Bar background */}
                <div style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${barWidth}%`,
                  background: `linear-gradient(90deg, ${shipClassColor}22, ${shipClassColor}08)`,
                  borderRadius: '4px 0 0 4px'
                }} />
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '0.65rem', color: '#fff', fontWeight: 600 }}>{shipName}</div>
                    <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>{data.ship_class}</div>
                  </div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
                    {data.losses}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function getSecurityColor(sec: number): string {
  if (sec >= 0.5) return '#00ff88';
  if (sec > 0) return '#ffcc00';
  return '#ff4444';
}
