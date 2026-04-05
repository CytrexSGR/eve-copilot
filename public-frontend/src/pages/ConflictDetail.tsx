import { useState, useEffect } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { warApi } from '../services/api';
import type { Conflict } from '../types/reports';
import { formatISK } from '../utils/security';

const TIME_STATUS_COLORS: Record<string, { color: string; icon: string }> = {
  '10m': { color: '#ff4444', icon: '🔴' },
  '1h': { color: '#ffcc00', icon: '🟡' },
  '12h': { color: '#00ff88', icon: '🟢' },
  '24h': { color: '#00d4ff', icon: '🔵' },
  '7d': { color: '#888888', icon: '⚫' },
};

const TREND_CONFIG: Record<string, { color: string; icon: string }> = {
  escalating: { color: '#ff4444', icon: '↗' },
  stable: { color: 'rgba(255,255,255,0.5)', icon: '→' },
  cooling: { color: '#00ff88', icon: '↘' },
};

const STATUS_LEVEL_COLORS: Record<string, string> = {
  gank: '#ff4444',
  brawl: '#ff8800',
  battle: '#ffcc00',
  hellcamp: '#00ffff',
};

export function ConflictDetail() {
  const { conflictId } = useParams<{ conflictId: string }>();
  const location = useLocation();
  const [conflict, setConflict] = useState<Conflict | null>(location.state?.conflict || null);
  const [loading, setLoading] = useState(!conflict);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (conflict) return;

    const fetchConflict = async () => {
      try {
        setLoading(true);
        const response = await warApi.getConflicts(10080);
        const found = response.conflicts.find(c => c.conflict_id === conflictId);
        if (found) {
          setConflict(found);
        } else {
          setError('Conflict not found');
        }
      } catch {
        setError('Failed to load conflict');
      } finally {
        setLoading(false);
      }
    };

    fetchConflict();
  }, [conflictId, conflict]);

  if (loading) {
    return (
      <div style={{ padding: '2rem' }}>
        <div className="skeleton" style={{ height: '400px', borderRadius: '12px' }} />
      </div>
    );
  }

  if (error || !conflict) {
    return (
      <div style={{ padding: '2rem' }}>
        <Link to="/battle-report#battlefield" style={{ color: '#00d4ff', textDecoration: 'none', marginBottom: '1rem', display: 'inline-block' }}>
          ← Back to Battlefield
        </Link>
        <div style={{ padding: '3rem', textAlign: 'center', color: '#ff4444', background: 'rgba(255,68,68,0.1)', borderRadius: '12px' }}>
          {error || 'Conflict not found'}
        </div>
      </div>
    );
  }

  const { coalition_a, coalition_b, regions, total_kills, total_isk, capital_kills, time_status, trend, battles, high_value_kills } = conflict;
  const timeConfig = TIME_STATUS_COLORS[time_status] || TIME_STATUS_COLORS['7d'];
  const trendConfig = TREND_CONFIG[trend] || TREND_CONFIG['stable'];

  const sectionStyle = {
    background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
    borderRadius: '12px',
    border: '1px solid rgba(100, 150, 255, 0.1)',
    padding: '1.5rem',
    marginBottom: '1.5rem',
  };

  return (
    <div style={{ padding: '2rem' }}>
      <Link to="/battle-report#battlefield" style={{ color: '#00d4ff', textDecoration: 'none', marginBottom: '1.5rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
        ← Back to Battlefield
      </Link>

      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem 0.625rem',
            background: `${timeConfig.color}22`, border: `1px solid ${timeConfig.color}44`,
            borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700, color: timeConfig.color,
          }}>
            {timeConfig.icon} {time_status}
          </span>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem 0.625rem',
            background: `${trendConfig.color}22`, borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700, color: trendConfig.color,
          }}>
            {trendConfig.icon} {trend}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '2rem', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
              <span style={{ color: '#00d4ff' }}>[{coalition_a.leader_ticker}]</span> {coalition_a.leader_name}
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#00d4ff', marginBottom: '0.25rem' }}>{coalition_a.efficiency.toFixed(1)}%</div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>efficiency</div>
          </div>
          <div style={{ fontSize: '2rem', color: 'rgba(255,255,255,0.2)' }}>⚔️</div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
              <span style={{ color: '#ff8800' }}>[{coalition_b.leader_ticker}]</span> {coalition_b.leader_name}
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ff8800', marginBottom: '0.25rem' }}>{coalition_b.efficiency.toFixed(1)}%</div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>efficiency</div>
          </div>
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', background: 'rgba(255,255,255,0.1)' }}>
            <div style={{ width: `${coalition_a.efficiency}%`, background: 'linear-gradient(90deg, #00d4ff, #00ff88)' }} />
            <div style={{ width: `${coalition_b.efficiency}%`, background: 'linear-gradient(90deg, #ff8800, #ff4444)' }} />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem' }}>Kills</span>
            <span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>{coalition_a.kills}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
            <span style={{ color: '#ff8800', fontWeight: 700, fontFamily: 'monospace' }}>{coalition_b.kills}</span>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem' }}>Kills</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem' }}>ISK Destroyed</span>
            <span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>{formatISK(coalition_a.isk_destroyed)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
            <span style={{ color: '#ff8800', fontWeight: 700, fontFamily: 'monospace' }}>{formatISK(coalition_b.isk_destroyed)}</span>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem' }}>ISK Destroyed</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', fontSize: '0.85rem' }}>
          <span><span style={{ color: 'rgba(255,255,255,0.5)' }}>Regions: </span><span style={{ color: '#fff' }}>{regions.join(', ')}</span></span>
          <span><span style={{ color: 'rgba(255,255,255,0.5)' }}>Total: </span><span style={{ color: '#ff4444', fontWeight: 700 }}>{total_kills}</span><span style={{ color: 'rgba(255,255,255,0.5)' }}> kills</span></span>
          <span style={{ color: '#ffcc00', fontWeight: 700 }}>{formatISK(total_isk)}</span>
          {capital_kills > 0 && <span><span style={{ color: '#a855f7', fontWeight: 700 }}>{capital_kills}</span><span style={{ color: 'rgba(255,255,255,0.5)' }}> caps</span></span>}
        </div>
      </div>

      {battles.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1.1rem' }}>📍</span>
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00d4ff' }}>Active Battles ({battles.length})</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {battles.map(battle => {
              const statusColor = STATUS_LEVEL_COLORS[battle.status_level] || '#888';
              return (
                <Link key={battle.battle_id} to={`/battle/${battle.battle_id}`} style={{
                  display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.875rem 1rem',
                  background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)',
                  textDecoration: 'none', transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,212,255,0.1)'; e.currentTarget.style.borderColor = 'rgba(0,212,255,0.2)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.3)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)'; }}>
                  <span style={{ padding: '0.25rem 0.5rem', background: `${statusColor}22`, border: `1px solid ${statusColor}44`, borderRadius: '4px', fontSize: '0.65rem', fontWeight: 700, color: statusColor, textTransform: 'uppercase' }}>{battle.status_level}</span>
                  <div style={{ flex: 1 }}><span style={{ fontWeight: 600, color: '#fff' }}>{battle.system_name}</span><span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.85rem' }}> ({battle.region_name})</span></div>
                  <span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>{battle.total_kills} kills</span>
                  <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', fontFamily: 'monospace' }}>{battle.minutes_ago < 60 ? `${battle.minutes_ago}m ago` : `${Math.floor(battle.minutes_ago / 60)}h ago`}</span>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>→</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {high_value_kills.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1.1rem' }}>💀</span>
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ffcc00' }}>High-Value Kills</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {high_value_kills.map(kill => (
              <a key={kill.killmail_id} href={`https://zkillboard.com/kill/${kill.killmail_id}/`} target="_blank" rel="noopener noreferrer" style={{
                display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.875rem 1rem',
                background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)',
                textDecoration: 'none', transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,68,68,0.1)'; e.currentTarget.style.borderColor = 'rgba(255,68,68,0.2)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.3)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)'; }}>
                <img src={`https://images.evetech.net/types/${kill.ship_type_id}/render?size=64`} alt={kill.ship_name} style={{ width: 44, height: 44, borderRadius: 4, border: '1px solid rgba(255,68,68,0.3)' }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                <div style={{ flex: 1 }}><span style={{ fontWeight: 600, color: '#fff', fontSize: '0.95rem' }}>{kill.ship_name}</span><div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)' }}><span style={{ color: '#ff4444' }}>[{kill.victim_alliance_ticker}]</span> killed by <span style={{ color: '#00ff88' }}>[{kill.attacker_alliance_ticker}]</span></div></div>
                <span style={{ color: '#ffcc00', fontWeight: 700, fontFamily: 'monospace', fontSize: '1rem' }}>{formatISK(kill.value)}</span>
                <span style={{ color: 'rgba(255,255,255,0.3)' }}>↗</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
