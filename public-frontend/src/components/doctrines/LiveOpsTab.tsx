import { memo, useMemo } from 'react';
import type { LiveOpsData } from '../../services/api/fingerprints';

interface LiveOpsTabProps {
  timeFilter: number;
  activeDoctrines?: LiveOpsData['active_doctrines'];
  hotspots?: LiveOpsData['hotspots'];
  counterMatrix?: LiveOpsData['counter_matrix'];
  isLoading: boolean;
}

const THREAT_COLORS: Record<string, string> = {
  critical: '#ff2222',
  hot: '#ff8800',
  active: '#ffcc00',
  low: '#888888'
};

export const LiveOpsTab = memo(function LiveOpsTab({
  timeFilter,
  activeDoctrines = [],
  hotspots = [],
  counterMatrix = [],
  isLoading
}: LiveOpsTabProps) {

  // Derive counter recommendations from counter_matrix
  const counters = useMemo(() => {
    if (!counterMatrix.length) return [];

    // For each victim class, find the top attacker class (= best counter)
    const bestCounters = new Map<string, { attacker: string; kills: number }>();
    for (const entry of counterMatrix) {
      const existing = bestCounters.get(entry.victim_class);
      if (!existing || entry.kills > existing.kills) {
        bestCounters.set(entry.victim_class, { attacker: entry.attacker_class, kills: entry.kills });
      }
    }

    return Array.from(bestCounters.entries())
      .sort((a, b) => b[1].kills - a[1].kills)
      .slice(0, 5)
      .map(([victim, { attacker, kills }]) => ({
        targetDoctrine: victim,
        counterDoctrine: attacker,
        kills,
        counterType: kills >= 10 ? 'hard' as const : 'soft' as const,
      }));
  }, [counterMatrix]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* 3-Column Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem'
      }}>
        {/* Column 1: Active Doctrines */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: '1px solid rgba(255, 68, 68, 0.2)',
          padding: '1rem',
          minHeight: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>🎯</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ff4444' }}>
              Active Doctrines
            </h3>
            <span style={{
              marginLeft: 'auto',
              fontSize: '0.6rem',
              color: 'rgba(255,255,255,0.4)',
              padding: '0.2rem 0.4rem',
              background: 'rgba(255,68,68,0.1)',
              borderRadius: '4px'
            }}>
              {timeFilter >= 1440 ? `${Math.round(timeFilter / 1440)}D` : timeFilter >= 60 ? `${Math.round(timeFilter / 60)}H` : `${timeFilter}M`}
            </span>
          </div>

          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading doctrines...
            </div>
          ) : activeDoctrines.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No doctrine activity in this timeframe
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {activeDoctrines.map((doc, idx) => {
                const color = idx < 3 ? '#ff4444' : '#888888';
                return (
                  <div
                    key={`${doc.alliance_id}-${idx}`}
                    style={{
                      padding: '0.6rem 0.75rem',
                      background: `${color}08`,
                      borderRadius: '8px',
                      borderLeft: `3px solid ${color}`
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                      <span style={{
                        fontFamily: 'monospace',
                        fontSize: '0.7rem',
                        color,
                        fontWeight: 700,
                        minWidth: '1.5rem'
                      }}>
                        #{idx + 1}
                      </span>
                      <img
                        src={`https://images.evetech.net/alliances/${doc.alliance_id}/logo?size=32`}
                        alt=""
                        style={{ width: 20, height: 20, borderRadius: '3px' }}
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {doc.alliance_name}
                        </div>
                        <div style={{ fontSize: '0.6rem', color: '#a855f7', fontWeight: 500 }}>
                          {doc.ship_class}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.65rem', marginBottom: '0.25rem' }}>
                      <span>
                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>K/D </span>
                        <span style={{ color: '#00d4ff', fontFamily: 'monospace', fontWeight: 600 }}>
                          {doc.kd_ratio.toFixed(1)}:1
                        </span>
                      </span>
                      <span>
                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>K </span>
                        <span style={{ color: '#00ff88', fontFamily: 'monospace', fontWeight: 600 }}>
                          {doc.kills}
                        </span>
                      </span>
                      <span>
                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>L </span>
                        <span style={{ color: '#f85149', fontFamily: 'monospace', fontWeight: 600 }}>
                          {doc.losses}
                        </span>
                      </span>
                      <span>
                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Surv </span>
                        <span style={{ color: '#00ff88', fontFamily: 'monospace', fontWeight: 600 }}>
                          {doc.survival_rate.toFixed(0)}%
                        </span>
                      </span>
                    </div>
                    {doc.top_ships.length > 0 && (
                      <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
                        {doc.top_ships.join(', ')}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Column 2: Doctrine Hotspots */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: '1px solid rgba(255, 136, 0, 0.2)',
          padding: '1rem',
          minHeight: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>🔥</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ff8800' }}>
              Doctrine Hotspots
            </h3>
          </div>

          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading hotspots...
            </div>
          ) : hotspots.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No hotspot activity in this timeframe
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {hotspots.map((spot, idx) => {
                const color = THREAT_COLORS[spot.threat_level];
                return (
                  <div
                    key={spot.region_name}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0.5rem 0.75rem',
                      background: `${color}08`,
                      borderRadius: '6px',
                      borderLeft: `3px solid ${color}`,
                      gap: '0.75rem'
                    }}
                  >
                    <span style={{
                      fontFamily: 'monospace',
                      fontSize: '0.7rem',
                      color,
                      fontWeight: 700,
                      minWidth: '1.5rem'
                    }}>
                      #{idx + 1}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 600 }}>
                        {spot.region_name}
                      </div>
                      <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
                        {spot.fleet_count} fleets - {spot.dominant_ship_class}
                        {spot.total_kills > 0 && ` - ${spot.total_kills.toLocaleString()} kills`}
                        {spot.top_alliance_name && ` - ${spot.top_alliance_name}`}
                      </div>
                    </div>
                    <span style={{
                      fontSize: '0.6rem',
                      padding: '0.2rem 0.4rem',
                      background: `${color}22`,
                      color,
                      borderRadius: '4px',
                      fontWeight: 600,
                      textTransform: 'uppercase'
                    }}>
                      {spot.threat_level}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Column 3: Counter Recommendations */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: '1px solid rgba(0, 212, 255, 0.2)',
          padding: '1rem',
          minHeight: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>⚔️</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00d4ff' }}>
              Counter Recommendations
            </h3>
          </div>

          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading counters...
            </div>
          ) : counters.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No counter data available
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {counters.map((counter) => (
                <div
                  key={counter.targetDoctrine}
                  style={{
                    padding: '0.75rem',
                    background: 'rgba(0, 212, 255, 0.05)',
                    borderRadius: '8px',
                    borderLeft: '3px solid #00d4ff'
                  }}
                >
                  <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.25rem' }}>
                    Against <span style={{ color: '#ff4444', fontWeight: 600 }}>{counter.targetDoctrine}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.65rem', color: '#00d4ff' }}>→</span>
                    <span style={{ fontSize: '0.9rem', color: '#00ff88', fontWeight: 600 }}>
                      {counter.counterDoctrine}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.35rem' }}>
                    <span style={{
                      fontSize: '0.6rem',
                      padding: '0.15rem 0.4rem',
                      background: counter.counterType === 'hard' ? 'rgba(0,255,136,0.2)' : 'rgba(255,204,0,0.2)',
                      color: counter.counterType === 'hard' ? '#00ff88' : '#ffcc00',
                      borderRadius: '4px',
                      fontWeight: 600
                    }}>
                      {counter.counterType === 'hard' ? 'Hard Counter' : 'Soft Counter'}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#a855f7', fontFamily: 'monospace' }}>
                      {counter.kills} kills
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
