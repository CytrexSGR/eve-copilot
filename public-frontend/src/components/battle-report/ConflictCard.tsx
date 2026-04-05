import { Link } from 'react-router-dom';

interface Conflict {
  alliance_1_id: number;
  alliance_1_name: string;
  alliance_1_kills: number;
  alliance_1_losses: number;
  alliance_1_efficiency: number;
  alliance_2_id: number;
  alliance_2_name: string;
  alliance_2_kills: number;
  alliance_2_losses: number;
  alliance_2_efficiency: number;
  primary_regions: string[];
  duration_days: number;
  total_isk_destroyed?: number;
  active_systems?: Array<{ system_name: string }>;
}

interface ConflictCardProps {
  conflict: Conflict;
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

export function ConflictCard({ conflict }: ConflictCardProps) {
  // Determine winner color for border
  const winnerColor = conflict.alliance_1_efficiency > conflict.alliance_2_efficiency ? '#00d4ff' : '#ff4444';
  const totalKills = conflict.alliance_1_kills + conflict.alliance_2_kills;

  return (
    <div
      style={{
        padding: '0.4rem 0.5rem',
        background: `${winnerColor}10`,
        borderRadius: '4px',
        borderLeft: `2px solid ${winnerColor}`,
        transition: 'all 0.15s ease'
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = `${winnerColor}10`; }}
    >
      {/* Header Row - Logos + Names */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        {/* Alliance Logos */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
          <img
            src={`https://images.evetech.net/alliances/${conflict.alliance_1_id}/logo?size=64`}
            alt=""
            style={{ width: 24, height: 24, borderRadius: '3px', border: '1px solid #00d4ff', background: 'rgba(0,0,0,0.3)' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.25)' }}>⚔</span>
          <img
            src={`https://images.evetech.net/alliances/${conflict.alliance_2_id}/logo?size=64`}
            alt=""
            style={{ width: 24, height: 24, borderRadius: '3px', border: '1px solid #ff4444', background: 'rgba(0,0,0,0.3)' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
        </div>

        {/* Names */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}>
            <Link
              to={`/alliance/${conflict.alliance_1_id}`}
              style={{ color: '#00d4ff', fontWeight: 700, textDecoration: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
            >{conflict.alliance_1_name}</Link>
            <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: '0.55rem' }}>vs</span>
            <Link
              to={`/alliance/${conflict.alliance_2_id}`}
              style={{ color: '#ff4444', fontWeight: 700, textDecoration: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
            >{conflict.alliance_2_name}</Link>
          </div>
          <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)' }}>
            {conflict.primary_regions[0]}
            <span style={{ marginLeft: '0.3rem' }}>{conflict.duration_days}d</span>
          </div>
        </div>

        {/* Total Kills Badge */}
        <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#ff8800', fontFamily: 'monospace' }}>
          {totalKills.toLocaleString()}
        </span>
      </div>

      {/* Stats Row - K/D + Efficiency Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.3rem', padding: '0.25rem 0.3rem', background: 'rgba(255,255,255,0.03)', borderRadius: '3px' }}>
        {/* Alliance 1 Stats */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'baseline', gap: '0.2rem', fontSize: '0.65rem' }}>
          <span style={{ color: '#00ff88', fontWeight: 700, fontFamily: 'monospace' }}>{conflict.alliance_1_kills.toLocaleString()}</span>
          <span style={{ color: 'rgba(255,255,255,0.2)' }}>/</span>
          <span style={{ color: '#ff4444', fontFamily: 'monospace' }}>{conflict.alliance_1_losses.toLocaleString()}</span>
        </div>

        {/* Efficiency Bar */}
        <div style={{ width: '60px' }}>
          <div style={{ display: 'flex', height: '5px', borderRadius: '2px', overflow: 'hidden', background: 'rgba(255,255,255,0.1)' }}>
            <div style={{ width: `${conflict.alliance_1_efficiency}%`, background: '#00d4ff' }} />
            <div style={{ width: `${conflict.alliance_2_efficiency}%`, background: '#ff4444' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.5rem', marginTop: '1px' }}>
            <span style={{ color: '#00d4ff', fontWeight: 700 }}>{conflict.alliance_1_efficiency.toFixed(0)}%</span>
            <span style={{ color: '#ff4444', fontWeight: 700 }}>{conflict.alliance_2_efficiency.toFixed(0)}%</span>
          </div>
        </div>

        {/* Alliance 2 Stats */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'baseline', justifyContent: 'flex-end', gap: '0.2rem', fontSize: '0.65rem' }}>
          <span style={{ color: '#00ff88', fontWeight: 700, fontFamily: 'monospace' }}>{conflict.alliance_2_kills.toLocaleString()}</span>
          <span style={{ color: 'rgba(255,255,255,0.2)' }}>/</span>
          <span style={{ color: '#ff4444', fontFamily: 'monospace' }}>{conflict.alliance_2_losses.toLocaleString()}</span>
        </div>
      </div>

      {/* ISK + Systems Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.2rem', fontSize: '0.6rem' }}>
        {conflict.total_isk_destroyed && (
          <>
            <span style={{ color: 'rgba(255,255,255,0.35)' }}>ISK:</span>
            <span style={{ color: '#ffcc00', fontFamily: 'monospace' }}>{formatISK(conflict.total_isk_destroyed)}</span>
          </>
        )}
        {conflict.active_systems && conflict.active_systems.length > 0 && (
          <span style={{ marginLeft: 'auto', color: 'rgba(255,255,255,0.3)' }}>
            {conflict.active_systems.slice(0, 2).map(s => s.system_name).join(', ')}
          </span>
        )}
      </div>
    </div>
  );
}
