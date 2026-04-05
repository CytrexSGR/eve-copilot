import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { formatISKCompact } from '../../utils/format';
import { reportsApi } from '../../services/api';
import type { BattleSidesResponse, CommanderIntelResponse } from '../../services/api';

// Power bloc cache (module-level for sharing across renders)
let powerBlocCache: Map<number, string> | null = null;

interface ParticipantAlliance {
  alliance_id: number;
  alliance_name: string;
  kills?: number;
  losses?: number;
  isk_lost?: number;
  corps_involved: number;
}

interface BattleParticipants {
  battle_id: number;
  attackers: {
    alliances: ParticipantAlliance[];
    total_alliances: number;
    total_kills: number;
  };
  defenders: {
    alliances: ParticipantAlliance[];
    total_alliances: number;
    total_losses: number;
    total_isk_lost: number;
  };
}

interface BattleSidesPanelProps {
  battleSides: BattleSidesResponse | null;
  participants: BattleParticipants | null;
  commanderIntel?: CommanderIntelResponse | null;
}

// CSS for animations
const STYLES = `
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
  }
`;

export function BattleSidesPanel({ battleSides, participants, commanderIntel }: BattleSidesPanelProps) {
  const [powerBlocs, setPowerBlocs] = useState<Map<number, string> | null>(powerBlocCache);

  // Fetch power blocs on mount
  useEffect(() => {
    const fetchPowerBlocs = async () => {
      if (powerBlocCache) {
        setPowerBlocs(powerBlocCache);
        return;
      }
      try {
        const data = await reportsApi.getPowerBlocsLive(1440);
        const map = new Map<number, string>();
        for (const coalition of data.coalitions || []) {
          for (const member of coalition.members || []) {
            map.set(member.alliance_id, coalition.name);
          }
        }
        powerBlocCache = map;
        setPowerBlocs(map);
      } catch (err) {
        console.error('Error fetching power blocs:', err);
      }
    };
    fetchPowerBlocs();
  }, []);

  // Render determined sides view (has full data)
  if (battleSides && battleSides.sides_determined) {
    return <DeterminedSidesView battleSides={battleSides} commanderIntel={commanderIntel} />;
  }

  // Fallback to belligerents display if sides not determined
  if (participants && (participants.attackers.alliances.length > 0 || participants.defenders.alliances.length > 0)) {
    return <BelligerentsView battleSides={battleSides} participants={participants} powerBlocs={powerBlocs} />;
  }

  return null;
}

// ============================================
// DETERMINED SIDES VIEW (Full Battlefield Style)
// ============================================

function DeterminedSidesView({
  battleSides,
  commanderIntel
}: {
  battleSides: BattleSidesResponse;
  commanderIntel?: CommanderIntelResponse | null;
}) {
  const sideAWinning = battleSides.side_a.totals.efficiency >= 50;
  const sideBWinning = battleSides.side_b.totals.efficiency >= 50;

  // Get top alliance names for each side
  const getSideName = (side: typeof battleSides.side_a) => {
    if (side.alliances.length === 0) return 'Unknown';
    const topAlliance = side.alliances[0];
    if (topAlliance.coalition_name && side.alliances.length > 1) {
      return topAlliance.coalition_name.replace(' Coalition', '');
    }
    return topAlliance.alliance_name;
  };

  const sideAName = getSideName(battleSides.side_a);
  const sideBName = getSideName(battleSides.side_b);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
    }}>
      <style>{STYLES}</style>

      {/* Header with Battle Summary */}
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
            background: '#ff4444',
            animation: 'pulse 1.5s infinite',
          }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase' }}>
            Battle Intel
          </span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
          <span>
            <span style={{ color: '#00ff88', fontWeight: 700, fontFamily: 'monospace' }}>
              {battleSides.side_a.totals.pilots + battleSides.side_b.totals.pilots}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>pilots</span>
          </span>
          <span>
            <span style={{ color: '#ffcc00', fontWeight: 700, fontFamily: 'monospace' }}>
              {formatISKCompact(battleSides.side_a.totals.isk_destroyed + battleSides.side_b.totals.isk_destroyed)}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>destroyed</span>
          </span>
          <span>
            <span style={{ color: '#a855f7', fontWeight: 700, fontFamily: 'monospace' }}>
              {battleSides.side_a.totals.alliance_count + battleSides.side_b.totals.alliance_count}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>alliances</span>
          </span>
        </div>
      </div>

      {/* VS Header with Efficiency Bar */}
      <div style={{ padding: '0.5rem 0.75rem' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: '0.75rem',
          alignItems: 'center',
          marginBottom: '0.5rem',
        }}>
          {/* Side A Header */}
          <SideHeader
            side={battleSides.side_a}
            name={sideAName}
            isWinning={sideAWinning}
            align="left"
            color="#00d4ff"
          />

          {/* VS Badge */}
          <div style={{
            padding: '0.4rem 0.8rem',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '4px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
              Efficiency
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 700, fontFamily: 'monospace' }}>
              <span style={{ color: sideAWinning ? '#00ff88' : '#ff4444' }}>
                {battleSides.side_a.totals.efficiency.toFixed(0)}%
              </span>
              <span style={{ color: 'rgba(255,255,255,0.2)', margin: '0 0.25rem' }}>vs</span>
              <span style={{ color: sideBWinning ? '#00ff88' : '#ff4444' }}>
                {battleSides.side_b.totals.efficiency.toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Side B Header */}
          <SideHeader
            side={battleSides.side_b}
            name={sideBName}
            isWinning={sideBWinning}
            align="right"
            color="#ff8800"
          />
        </div>

        {/* ISK Balance Bar */}
        <div style={{ marginBottom: '0.25rem' }}>
          <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', background: 'rgba(255,255,255,0.1)' }}>
            <div style={{
              width: `${battleSides.side_a.totals.efficiency}%`,
              background: 'linear-gradient(90deg, #00d4ff 0%, #00ff88 100%)',
            }} />
            <div style={{
              width: `${100 - battleSides.side_a.totals.efficiency}%`,
              background: 'linear-gradient(90deg, #ff8800 0%, #ff4444 100%)',
            }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem' }}>
            <span>
              <span style={{ color: '#00ff88' }}>+{formatISKCompact(battleSides.side_a.totals.isk_destroyed)}</span>
              <span> / </span>
              <span style={{ color: '#ff4444' }}>-{formatISKCompact(battleSides.side_a.totals.isk_lost)}</span>
            </span>
            <span>
              <span style={{ color: '#ff4444' }}>-{formatISKCompact(battleSides.side_b.totals.isk_lost)}</span>
              <span> / </span>
              <span style={{ color: '#00ff88' }}>+{formatISKCompact(battleSides.side_b.totals.isk_destroyed)}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Side A | Side B */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '0.3rem',
        padding: '0 0.5rem 0.5rem',
      }}>
        {/* Side A */}
        <SidePanel
          side={battleSides.side_a}
          commanderDoctrines={commanderIntel?.doctrines}
        />

        {/* Side B */}
        <SidePanel
          side={battleSides.side_b}
          commanderDoctrines={commanderIntel?.doctrines}
        />
      </div>
    </div>
  );
}

// Side Header Component
function SideHeader({ side, name, isWinning, align, color }: {
  side: BattleSidesResponse['side_a'];
  name: string;
  isWinning: boolean;
  align: 'left' | 'right';
  color: string;
}) {
  const topAlliance = side.alliances[0];

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      justifyContent: align === 'right' ? 'flex-end' : 'flex-start',
      flexDirection: align === 'right' ? 'row-reverse' : 'row',
    }}>
      {topAlliance && (
        <img
          src={`https://images.evetech.net/alliances/${topAlliance.alliance_id}/logo?size=64`}
          alt=""
          loading="lazy"
          decoding="async"
          style={{ width: 32, height: 32, borderRadius: 4, border: `2px solid ${color}` }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
      )}
      <div style={{ textAlign: align }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', justifyContent: align === 'right' ? 'flex-end' : 'flex-start' }}>
          {isWinning && (
            <span style={{
              fontSize: '0.7rem',
              padding: '1px 5px',
              borderRadius: '2px',
              background: 'rgba(0,255,136,0.3)',
              color: '#00ff88',
              fontWeight: 700,
            }}>
              WINNING
            </span>
          )}
          <span style={{ fontWeight: 700, fontSize: '1.1rem', color: '#fff' }}>{name}</span>
        </div>
        <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)' }}>
          <span style={{ color, fontWeight: 600 }}>{side.totals.pilots}</span> pilots
          <span style={{ margin: '0 0.35rem' }}>•</span>
          <span style={{ color, fontWeight: 600 }}>{side.totals.alliance_count}</span> alliances
        </div>
      </div>
    </div>
  );
}

// Side Panel Component with Alliance Cards
function SidePanel({ side, commanderDoctrines }: {
  side: BattleSidesResponse['side_a'];
  commanderDoctrines?: Record<string, { fielding: Array<{ ship_name: string; engagements: number }>; losses: Array<{ ship_name: string; count: number }> }>;
}) {
  // Group alliances by power bloc
  const groups: Map<string, typeof side.alliances> = new Map();
  const ungrouped: typeof side.alliances = [];

  for (const alliance of side.alliances) {
    // Use API-provided coalition_name only (backend strips it for internal conflicts)
    const blocName = alliance.coalition_name;
    if (blocName) {
      if (!groups.has(blocName)) {
        groups.set(blocName, []);
      }
      groups.get(blocName)!.push(alliance);
    } else {
      ungrouped.push(alliance);
    }
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      padding: '0.35rem',
      maxHeight: '500px',
      overflowY: 'auto',
    }}>
      {/* Grouped by Power Bloc */}
      {Array.from(groups.entries()).map(([blocName, blocAlliances]) => (
        <div key={blocName} style={{ marginBottom: '0.5rem' }}>
          <PowerBlocHeader name={blocName} allianceCount={blocAlliances.length} />
          {blocAlliances.map((alliance) => (
            <AllianceCard
              key={alliance.alliance_id}
              alliance={alliance}
              doctrineShips={commanderDoctrines?.[alliance.alliance_name]?.fielding}
            />
          ))}
        </div>
      ))}

      {/* Independent Alliances */}
      {ungrouped.length > 0 && (
        <div>
          {groups.size > 0 && (
            <div style={{
              fontSize: '0.75rem',
              color: 'rgba(255,255,255,0.4)',
              padding: '0.25rem 0.35rem',
              marginTop: '0.25rem',
              marginBottom: '0.25rem',
              borderLeft: '2px solid rgba(255,255,255,0.2)',
              textTransform: 'uppercase',
            }}>
              Independent ({ungrouped.length})
            </div>
          )}
          {ungrouped.map((alliance) => (
            <AllianceCard
              key={alliance.alliance_id}
              alliance={alliance}
              doctrineShips={commanderDoctrines?.[alliance.alliance_name]?.fielding}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Power Bloc Header
function PowerBlocHeader({ name, allianceCount }: { name: string; allianceCount: number }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.3rem 0.4rem',
      marginBottom: '0.25rem',
      borderLeft: '3px solid #a855f7',
      background: 'rgba(168, 85, 247, 0.1)',
      borderRadius: '0 4px 4px 0',
    }}>
      <span style={{
        fontSize: '0.85rem',
        fontWeight: 700,
        color: '#a855f7',
        textTransform: 'uppercase',
        letterSpacing: '0.02em',
      }}>
        {name}
      </span>
      <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
        {allianceCount} alliance{allianceCount !== 1 ? 's' : ''}
      </span>
    </div>
  );
}

// Alliance Card Component (Compact Single-Line)
// Cache for alliance typical stats (lazy-loaded, persists across re-renders)
const allianceStatsCache = new Map<number, { efficiency: number; kd_ratio: number } | 'loading' | 'error'>();

function AllianceCard({ alliance, doctrineShips: _doctrineShips }: {
  alliance: BattleSidesResponse['side_a']['alliances'][0];
  doctrineShips?: Array<{ ship_name: string; engagements: number }>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [typicalStats, setTypicalStats] = useState<{ efficiency: number; kd_ratio: number; fleet_profile?: { avg_fleet_size: number; median_fleet_size: number | null; max_fleet_size: number | null } | null } | null>(null);

  const efficiency = alliance.efficiency;
  const isWinning = efficiency >= 50;
  const borderColor = isWinning ? '#00ff88' : '#ff4444';

  const handleExpand = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (expanded) { setExpanded(false); return; }
    setExpanded(true);

    const cached = allianceStatsCache.get(alliance.alliance_id);
    if (cached && cached !== 'loading' && cached !== 'error') {
      setTypicalStats(cached);
      return;
    }
    if (cached === 'loading') return;

    allianceStatsCache.set(alliance.alliance_id, 'loading');
    try {
      const res = await fetch(`/api/intelligence/fast/alliance/${alliance.alliance_id}/offensive-stats?days=7`);
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      const stats = {
        efficiency: data.summary?.isk_efficiency ?? data.summary?.efficiency ?? 0,
        kd_ratio: data.summary?.kd_ratio ?? (data.summary?.kills && data.summary?.deaths
          ? data.summary.kills / Math.max(data.summary.deaths, 1) : 0),
        fleet_profile: data.fleet_profile || null,
      };
      allianceStatsCache.set(alliance.alliance_id, stats);
      setTypicalStats(stats);
    } catch {
      allianceStatsCache.set(alliance.alliance_id, 'error');
    }
  };

  const battleKD = alliance.losses > 0 ? alliance.kills / alliance.losses : alliance.kills;

  return (
    <div style={{ marginBottom: '0.15rem' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0.25rem 0.4rem',
        background: `${borderColor}08`,
        borderRadius: expanded ? '4px 4px 0 0' : '4px',
        borderLeft: `2px solid ${borderColor}`,
        transition: 'all 0.15s ease',
      }}>
        {/* Expand toggle */}
        <button
          onClick={handleExpand}
          style={{
            background: 'none', border: 'none', color: '#6e7681', cursor: 'pointer',
            fontSize: '0.65rem', padding: '0 0.1rem', flexShrink: 0, lineHeight: 1,
          }}
          title="Compare with 7d average"
        >
          {expanded ? '\u25BC' : '\u25B6'}
        </button>

        <Link
          to={`/alliance/${alliance.alliance_id}`}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.35rem', flex: 1, minWidth: 0,
            textDecoration: 'none',
          }}
        >
          <img
            src={`https://images.evetech.net/alliances/${alliance.alliance_id}/logo?size=32`}
            alt=""
            loading="lazy"
            decoding="async"
            style={{ width: 22, height: 22, borderRadius: '2px', background: 'rgba(0,0,0,0.3)', flexShrink: 0 }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, minWidth: 0 }}>
            {alliance.alliance_name}
          </span>
        </Link>

        <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', flexShrink: 0 }}>
          {alliance.pilots}p
        </span>

        <span style={{ fontSize: '0.7rem', color: '#00ff88', fontFamily: 'monospace', fontWeight: 600, flexShrink: 0 }}>
          {alliance.kills}
        </span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.15)' }}>/</span>
        <span style={{ fontSize: '0.7rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 600, flexShrink: 0 }}>
          {alliance.losses}
        </span>

        <span style={{
          fontSize: '0.7rem', fontWeight: 700,
          color: isWinning ? '#00ff88' : '#ff4444',
          fontFamily: 'monospace', minWidth: '26px', textAlign: 'right', flexShrink: 0,
        }}>
          {efficiency.toFixed(0)}%
        </span>

        <span style={{
          fontSize: '0.7rem', fontWeight: 600,
          color: '#ffcc00', fontFamily: 'monospace', minWidth: '40px', textAlign: 'right', flexShrink: 0,
        }}>
          {formatISKCompact(alliance.isk_destroyed)}
        </span>
      </div>

      {/* Expandable comparison row */}
      {expanded && (
        <div style={{
          padding: '0.2rem 0.4rem 0.2rem 1.6rem',
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '0 0 4px 4px',
          borderLeft: `2px solid ${borderColor}40`,
          fontSize: '0.7rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          color: '#8b949e',
        }}>
          {!typicalStats ? (
            <span>Loading 7d stats...</span>
          ) : (
            <>
              <span>
                7d avg: <span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{typicalStats.efficiency.toFixed(0)}%</span> eff
                {' '}<span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{typicalStats.kd_ratio.toFixed(1)}</span> K/D
                {typicalStats.fleet_profile && (
                  <>
                    <span style={{ color: 'rgba(255,255,255,0.15)', margin: '0 0.3rem' }}>|</span>
                    Fleet: <span style={{ color: '#a855f7', fontFamily: 'monospace' }}>~{Math.round(typicalStats.fleet_profile.avg_fleet_size)}</span> avg
                    {typicalStats.fleet_profile.median_fleet_size != null && (
                      <> <span style={{ color: '#8b949e', fontFamily: 'monospace' }}>({typicalStats.fleet_profile.median_fleet_size} med)</span></>
                    )}
                    {typicalStats.fleet_profile.max_fleet_size != null && (
                      <> max <span style={{ color: '#6e7681', fontFamily: 'monospace' }}>{typicalStats.fleet_profile.max_fleet_size}</span></>
                    )}
                  </>
                )}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.15)' }}>vs</span>
              <span>
                Battle: <span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{efficiency.toFixed(0)}%</span> eff
                {' '}<span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{battleKD.toFixed(1)}</span> K/D
              </span>
              {(() => {
                const effDelta = efficiency - typicalStats.efficiency;
                const color = effDelta >= 0 ? '#00ff88' : '#ff4444';
                const arrow = effDelta >= 0 ? '\u25B2' : '\u25BC';
                return (
                  <span style={{
                    padding: '0.05rem 0.25rem', borderRadius: '2px',
                    background: `${color}15`, color, fontWeight: 700, fontSize: '0.65rem',
                  }}>
                    {arrow} {Math.abs(effDelta).toFixed(0)}%
                  </span>
                );
              })()}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================
// BELLIGERENTS VIEW (Fallback when sides not determined)
// ============================================

function BelligerentsView({ battleSides, participants, powerBlocs }: {
  battleSides: BattleSidesResponse | null;
  participants: BattleParticipants;
  powerBlocs: Map<number, string> | null;
}) {
  const attackersIsk = participants.attackers.alliances.reduce((sum, a) => sum + (a.isk_lost || 0), 0);
  const defendersIsk = participants.defenders.total_isk_lost || 0;
  const totalIsk = attackersIsk + defendersIsk;
  const attackerPercent = totalIsk > 0 ? (defendersIsk / totalIsk) * 100 : 50;

  const topAttacker = participants.attackers.alliances[0];
  const topDefender = participants.defenders.alliances[0];

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1.5rem',
    }}>
      <style>{STYLES}</style>

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
            background: '#ffcc00',
            animation: 'pulse 1.5s infinite',
          }} />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#ffcc00', textTransform: 'uppercase' }}>
            Battle Participants
          </span>
          <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
            (sides not yet determined)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.65rem' }}>
          <span>
            <span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>
              {participants.attackers.total_alliances}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>attackers</span>
          </span>
          <span>
            <span style={{ color: '#ff8800', fontWeight: 700, fontFamily: 'monospace' }}>
              {participants.defenders.total_alliances}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>defenders</span>
          </span>
        </div>
      </div>

      {/* VS Header */}
      <div style={{ padding: '0.75rem' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: '1rem',
          alignItems: 'center',
          marginBottom: '0.75rem',
        }}>
          {/* Attackers Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {topAttacker && (
              <img
                src={`https://images.evetech.net/alliances/${topAttacker.alliance_id}/logo?size=64`}
                alt=""
                loading="lazy"
                decoding="async"
                style={{ width: 36, height: 36, borderRadius: 4, border: '2px solid #00d4ff' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            )}
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#00d4ff' }}>
                {topAttacker?.alliance_name || 'Unknown'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)' }}>
                {participants.attackers.total_kills} kills
              </div>
            </div>
          </div>

          {/* VS */}
          <div style={{
            padding: '0.3rem 0.6rem',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '4px',
            fontSize: '0.75rem',
            color: 'rgba(255,255,255,0.3)',
            fontWeight: 700,
          }}>
            VS
          </div>

          {/* Defenders Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#ff8800' }}>
                {topDefender?.alliance_name || 'Unknown'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)' }}>
                {participants.defenders.total_losses} losses
              </div>
            </div>
            {topDefender && (
              <img
                src={`https://images.evetech.net/alliances/${topDefender.alliance_id}/logo?size=64`}
                alt=""
                loading="lazy"
                decoding="async"
                style={{ width: 36, height: 36, borderRadius: 4, border: '2px solid #ff8800' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            )}
          </div>
        </div>

        {/* ISK Bar */}
        {totalIsk > 0 && (
          <div>
            <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden', background: 'rgba(255,255,255,0.1)' }}>
              <div style={{ width: `${attackerPercent}%`, background: '#00d4ff' }} />
              <div style={{ width: `${100 - attackerPercent}%`, background: '#ff8800' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem' }}>
              <span>+{formatISKCompact(defendersIsk)} destroyed</span>
              <span>-{formatISKCompact(defendersIsk)} lost</span>
            </div>
          </div>
        )}
      </div>

      {battleSides?.message && (
        <p style={{ color: '#ffcc00', fontSize: '0.7rem', padding: '0 0.75rem 0.5rem', fontStyle: 'italic' }}>
          Note: {battleSides.message}
        </p>
      )}

      {/* Two Column Alliance List */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '0.5rem',
        padding: '0 0.75rem 0.75rem',
      }}>
        {/* Attackers */}
        <BelligerentSidePanel
          alliances={participants.attackers.alliances}
          powerBlocs={powerBlocs}
          side="attacker"
        />

        {/* Defenders */}
        <BelligerentSidePanel
          alliances={participants.defenders.alliances}
          powerBlocs={powerBlocs}
          side="defender"
        />
      </div>
    </div>
  );
}

// Belligerent Side Panel
function BelligerentSidePanel({ alliances, powerBlocs, side }: {
  alliances: ParticipantAlliance[];
  powerBlocs: Map<number, string> | null;
  side: 'attacker' | 'defender';
}) {
  // Group by power bloc
  const groups: Map<string, ParticipantAlliance[]> = new Map();
  const ungrouped: ParticipantAlliance[] = [];

  for (const alliance of alliances) {
    const blocName = powerBlocs?.get(alliance.alliance_id);
    if (blocName) {
      if (!groups.has(blocName)) groups.set(blocName, []);
      groups.get(blocName)!.push(alliance);
    } else {
      ungrouped.push(alliance);
    }
  }

  const color = side === 'attacker' ? '#00d4ff' : '#ff8800';
  const statLabel = side === 'attacker' ? 'K' : 'L';
  const statValue = (a: ParticipantAlliance) => side === 'attacker' ? (a.kills || 0) : (a.losses || 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      padding: '0.5rem',
      maxHeight: '400px',
      overflowY: 'auto',
    }}>
      {/* Grouped */}
      {Array.from(groups.entries()).map(([blocName, blocAlliances]) => (
        <div key={blocName} style={{ marginBottom: '0.5rem' }}>
          <PowerBlocHeader name={blocName} allianceCount={blocAlliances.length} />
          {blocAlliances.map((alliance) => (
            <BelligerentAllianceRow
              key={alliance.alliance_id}
              alliance={alliance}
              color={color}
              statLabel={statLabel}
              statValue={statValue(alliance)}
            />
          ))}
        </div>
      ))}

      {/* Ungrouped */}
      {ungrouped.length > 0 && (
        <div>
          {groups.size > 0 && (
            <div style={{
              fontSize: '0.6rem',
              color: 'rgba(255,255,255,0.4)',
              padding: '0.25rem 0.35rem',
              marginBottom: '0.25rem',
              borderLeft: '2px solid rgba(255,255,255,0.2)',
              textTransform: 'uppercase',
            }}>
              Independent ({ungrouped.length})
            </div>
          )}
          {ungrouped.map((alliance) => (
            <BelligerentAllianceRow
              key={alliance.alliance_id}
              alliance={alliance}
              color={color}
              statLabel={statLabel}
              statValue={statValue(alliance)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Belligerent Alliance Row
function BelligerentAllianceRow({ alliance, color, statLabel, statValue }: {
  alliance: ParticipantAlliance;
  color: string;
  statLabel: string;
  statValue: number;
}) {
  return (
    <Link
      to={`/alliance/${alliance.alliance_id}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0.35rem 0.4rem',
        marginBottom: '0.2rem',
        background: `${color}10`,
        borderRadius: '4px',
        borderLeft: `2px solid ${color}`,
        textDecoration: 'none',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = `${color}10`; }}
    >
      <img
        src={`https://images.evetech.net/alliances/${alliance.alliance_id}/logo?size=32`}
        alt=""
        loading="lazy"
        decoding="async"
        style={{ width: 20, height: 20, borderRadius: 2 }}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
      />
      <span style={{ flex: 1, fontSize: '0.7rem', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {alliance.alliance_name}
      </span>
      {alliance.corps_involved > 0 && (
        <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
          {alliance.corps_involved}C
        </span>
      )}
      <span style={{ fontSize: '0.75rem', fontWeight: 700, color, fontFamily: 'monospace' }}>
        {statValue}{statLabel}
      </span>
    </Link>
  );
}
