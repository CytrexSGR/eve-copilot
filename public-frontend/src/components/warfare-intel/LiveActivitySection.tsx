// src/components/warfare-intel/LiveActivitySection.tsx
import { Link } from 'react-router-dom';
import type { ActiveBattle } from '../../types/battle';

interface LiveActivitySectionProps {
  battles: ActiveBattle[];
  recentKills: Array<{ killmail_id: number; ship_name: string; value: number }>;
  loading?: boolean;
}

function formatIsk(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toString();
}

function getBattleStatus(battle: ActiveBattle): { color: string; label: string } {
  const minutesAgo = battle.duration_minutes;
  if (minutesAgo <= 5) return { color: '#ff4444', label: 'NOW' };
  if (minutesAgo <= 30) return { color: '#ffaa00', label: `${minutesAgo}m` };
  return { color: '#00ff88', label: `${minutesAgo}m` };
}

export function LiveActivitySection({ battles, recentKills, loading }: LiveActivitySectionProps) {
  const sectionStyle = {
    background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
    borderRadius: '12px',
    border: '1px solid rgba(100, 150, 255, 0.1)',
    padding: '1.5rem',
    marginBottom: '1.5rem'
  };

  if (loading) {
    return (
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.25rem' }}>⚔️</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ff4444' }}>
            Live Activity
          </h3>
        </div>
        <div style={{ color: 'rgba(255,255,255,0.4)', padding: '2rem', textAlign: 'center' }}>
          Loading battles...
        </div>
      </div>
    );
  }

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>⚔️</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ff4444' }}>
            Live Activity
          </h3>
        </div>
        <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)' }}>
          {battles.length} battle{battles.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Battles List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
        {battles.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.4)', padding: '1rem', textAlign: 'center' }}>
            No active battles in selected timeframe
          </div>
        ) : (
          battles.slice(0, 5).map(battle => {
            const status = getBattleStatus(battle);
            return (
              <Link
                key={battle.battle_id}
                to={`/battle/${battle.battle_id}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.75rem 1rem',
                  background: 'rgba(0,0,0,0.3)',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.05)',
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: status.color,
                    boxShadow: `0 0 8px ${status.color}`
                  }} />
                  <div>
                    <div style={{ fontWeight: 600, color: '#fff' }}>
                      {battle.system_name}
                      <span style={{ color: 'rgba(255,255,255,0.4)', fontWeight: 400, marginLeft: '0.5rem' }}>
                        ({battle.region_name})
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>
                      {battle.intensity === 'extreme' && '🔥 '}{battle.status_level || 'battle'}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                  <span style={{ fontSize: '0.8rem', color: status.color, fontWeight: 600 }}>
                    {status.label}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#fff' }}>
                    {battle.total_kills} kills
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#00d4ff' }}>
                    {formatIsk(battle.total_isk_destroyed)}
                  </span>
                </div>
              </Link>
            );
          })
        )}
      </div>

      {/* Kill Ticker */}
      {recentKills.length > 0 && (
        <div style={{
          padding: '0.75rem 1rem',
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '6px',
          fontSize: '0.8rem',
          color: 'rgba(255,255,255,0.6)'
        }}>
          <span style={{ color: 'rgba(255,255,255,0.4)', marginRight: '0.5rem' }}>Recent:</span>
          {recentKills.slice(0, 5).map((kill, i) => (
            <span key={kill.killmail_id}>
              {i > 0 && ' → '}
              <span style={{ color: kill.value > 1e9 ? '#ff4444' : '#fff' }}>
                {kill.ship_name}
              </span>
              {kill.value > 1e9 && (
                <span style={{ color: '#ff4444', marginLeft: '0.25rem' }}>
                  ({formatIsk(kill.value)})
                </span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
