import { formatISKCompact } from '../../utils/format';

interface BattleInfo {
  battle_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_kills: number;
  total_isk_destroyed: number;
  started_at: string;
  last_kill_at: string;
  last_milestone: number;
  telegram_sent: boolean;
  duration_minutes: number;
  intensity: 'extreme' | 'high' | 'moderate' | 'low';
}

interface SystemDanger {
  system_id: number;
  danger_score: number;
  kills_24h: number;
  is_dangerous: boolean;
  sov_alliance_id?: number | null;
  sov_alliance_name?: string | null;
}

interface CapitalShip {
  ship_name: string;
  count: number;
  value: number;
}

interface BattleHeaderProps {
  battle: BattleInfo;
  systemDanger: SystemDanger | null;
  capitalShipsLost: CapitalShip[];
  onBack: () => void;
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}

export function BattleHeader({ battle, systemDanger, capitalShipsLost, onBack }: BattleHeaderProps) {
  const intensityColor =
    battle.intensity === 'extreme' ? 'var(--danger)' :
    battle.intensity === 'high' ? 'var(--warning)' :
    battle.intensity === 'moderate' ? 'var(--accent-blue)' :
    'var(--success)';

  const avgKillValue = battle.total_kills > 0 ? battle.total_isk_destroyed / battle.total_kills : 0;

  return (
    <>
      {/* Back Button */}
      <button
        onClick={onBack}
        style={{
          padding: '0.3rem 0.75rem',
          background: 'var(--bg-elevated)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-color)',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: 600,
          cursor: 'pointer',
          marginBottom: '0.5rem',
        }}
      >
        &larr; Back
      </button>

      {/* Battle Header - Compact with Timeline */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        marginBottom: '1rem',
        overflow: 'hidden',
      }}>
        {/* Main Header Row */}
        <div style={{
          padding: '0.75rem 1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          {/* Title + Location */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: '1.25rem', margin: 0, color: '#fff' }}>
              {battle.system_name}
            </h1>
            <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', alignItems: 'center' }}>
              <span>{battle.region_name}</span>
              <span style={{
                color: battle.security >= 0.5 ? '#00ff88' : battle.security > 0 ? '#ffcc00' : '#ff4444',
                fontWeight: 600
              }}>
                {battle.security.toFixed(1)}
              </span>
              {systemDanger?.is_dangerous && <span style={{ color: '#ff4444' }}>DANGER</span>}
              {battle.security < 0.5 && systemDanger?.sov_alliance_name && (
                <span style={{
                  padding: '0.15rem 0.4rem',
                  borderRadius: '3px',
                  background: 'rgba(168, 85, 247, 0.15)',
                  color: '#a855f7',
                  fontSize: '0.6rem',
                  fontWeight: 600,
                }}>
                  SOV: {systemDanger.sov_alliance_name}
                </span>
              )}
              {battle.security < 0 && !systemDanger?.sov_alliance_name && (
                <span style={{
                  padding: '0.15rem 0.4rem',
                  borderRadius: '3px',
                  background: 'rgba(139, 148, 158, 0.15)',
                  color: '#8b949e',
                  fontSize: '0.6rem',
                  fontWeight: 600,
                }}>
                  UNCLAIMED
                </span>
              )}
            </div>
            <div style={{
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              background: intensityColor,
              color: 'white',
              fontSize: '0.65rem',
              fontWeight: 700,
              textTransform: 'uppercase'
            }}>
              {battle.intensity}
            </div>
          </div>

          {/* Stats Row */}
          <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
              <span style={{ color: '#00d4ff', fontWeight: 700, fontSize: '1.5rem' }}>{battle.total_kills}</span>
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>kills</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
              <span style={{ color: '#ff4444', fontWeight: 700, fontSize: '1.5rem', fontFamily: 'monospace' }}>{formatISKCompact(battle.total_isk_destroyed)}</span>
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>ISK</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
              <span style={{ color: '#ffcc00', fontWeight: 700, fontSize: '1.25rem', fontFamily: 'monospace' }}>{formatISKCompact(avgKillValue)}</span>
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>avg</span>
            </div>
          </div>
        </div>

        {/* Timeline + Capitals Row */}
        <div style={{
          padding: '0.5rem 1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          background: 'rgba(0,0,0,0.2)',
        }}>
          {/* Timeline Info */}
          <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00ff88' }} />
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>Started</span>
              <span style={{ color: '#fff', fontSize: '0.75rem', fontWeight: 600 }}>{formatTime(battle.started_at)}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00d4ff' }} />
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>Last Kill</span>
              <span style={{ color: '#fff', fontSize: '0.75rem', fontWeight: 600 }}>{formatTime(battle.last_kill_at)}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#ffcc00' }} />
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>Duration</span>
              <span style={{ color: '#fff', fontSize: '0.75rem', fontWeight: 600 }}>
                {battle.duration_minutes < 60 ? `${battle.duration_minutes}m` : `${Math.floor(battle.duration_minutes / 60)}h ${battle.duration_minutes % 60}m`}
              </span>
            </div>
            {battle.last_milestone > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#ff8800' }} />
                <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>Milestone</span>
                <span style={{ color: '#ff8800', fontSize: '0.75rem', fontWeight: 600 }}>{battle.last_milestone} kills</span>
              </div>
            )}
            {battle.telegram_sent && (
              <span style={{
                padding: '0.15rem 0.4rem',
                borderRadius: '3px',
                background: 'rgba(168, 85, 247, 0.2)',
                color: '#a855f7',
                fontSize: '0.6rem',
                fontWeight: 600,
                textTransform: 'uppercase',
              }}>
                Alerted
              </span>
            )}
          </div>

          {/* Capital Ships Lost */}
          {capitalShipsLost.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ color: '#ff8800', fontSize: '0.7rem', fontWeight: 600 }}>CAPITALS:</span>
              <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                {capitalShipsLost.map((cap, idx) => (
                  <span key={idx} style={{
                    padding: '0.15rem 0.4rem',
                    borderRadius: '3px',
                    background: 'rgba(255, 136, 0, 0.15)',
                    color: '#ff8800',
                    fontSize: '0.65rem',
                    fontWeight: 500,
                    whiteSpace: 'nowrap'
                  }}>
                    {cap.count > 1 ? `${cap.count}x ` : ''}{cap.ship_name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
