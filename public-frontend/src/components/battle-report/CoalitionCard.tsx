import { Link } from 'react-router-dom';

interface Coalition {
  name: string;
  leader_alliance_id: number;
  leader_name: string;
  member_count: number;
  members: Array<{ alliance_id: number; name: string; activity: number }>;
  total_kills: number;
  total_losses: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
  total_activity: number;
  kills_series?: number[];
  deaths_series?: number[];
  isk_series?: number[];
  esi_members?: number;
  active_pilots?: number;
}

interface CoalitionCardProps {
  coalition: Coalition;
}

function DualLineSparkline({
  kills,
  deaths,
  width = 100,
  height = 28
}: {
  kills: number[];
  deaths: number[];
  width?: number;
  height?: number;
}) {
  if (!kills?.length && !deaths?.length) {
    return <div style={{ width, height, background: 'rgba(255,255,255,0.03)', borderRadius: '4px' }} />;
  }

  const allValues = [...(kills || []), ...(deaths || [])];
  const max = Math.max(...allValues) || 1;
  const dataLen = Math.max(kills?.length || 0, deaths?.length || 0);

  const getPoints = (data: number[] | undefined) => {
    if (!data || data.length < 2) return '';
    return data.map((v, i) => {
      const x = (i / (dataLen - 1)) * width;
      const y = height - (v / max) * (height - 6) - 3;
      return `${x},${y}`;
    }).join(' ');
  };

  const killsPoints = getPoints(kills);
  const deathsPoints = getPoints(deaths);

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <defs>
        <linearGradient id="grad-kills" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#00ff88" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#00ff88" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="grad-deaths" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ff4444" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#ff4444" stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* Kills area and line */}
      {killsPoints && (
        <>
          <polygon points={`0,${height} ${killsPoints} ${width},${height}`} fill="url(#grad-kills)" />
          <polyline points={killsPoints} fill="none" stroke="#00ff88" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </>
      )}
      {/* Deaths area and line */}
      {deathsPoints && (
        <>
          <polygon points={`0,${height} ${deathsPoints} ${width},${height}`} fill="url(#grad-deaths)" />
          <polyline points={deathsPoints} fill="none" stroke="#ff4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
        </>
      )}
    </svg>
  );
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

export function CoalitionCard({ coalition }: CoalitionCardProps) {
  const effColor = coalition.efficiency >= 55 ? '#00ff88' : coalition.efficiency >= 45 ? '#ffcc00' : '#ff4444';
  const activeRate = coalition.esi_members && coalition.active_pilots
    ? Math.round((coalition.active_pilots / coalition.esi_members) * 100)
    : null;

  // K/D ratio
  const kdRatio = coalition.total_losses > 0
    ? (coalition.total_kills / coalition.total_losses).toFixed(1)
    : coalition.total_kills > 0 ? '∞' : '0';

  return (
    <Link
      to={`/powerbloc/${coalition.leader_alliance_id}`}
      style={{
        display: 'block',
        padding: '0.4rem 0.5rem',
        background: `${effColor}10`,
        borderRadius: '4px',
        borderLeft: `2px solid ${effColor}`,
        transition: 'all 0.15s ease',
        textDecoration: 'none',
        color: 'inherit',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = `${effColor}10`; }}
    >
      {/* Header Row - Compact */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <img
          src={`https://images.evetech.net/alliances/${coalition.leader_alliance_id}/logo?size=64`}
          alt=""
          style={{ width: 24, height: 24, borderRadius: '3px', background: 'rgba(0,0,0,0.3)' }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <h3 style={{ fontSize: '0.75rem', fontWeight: 700, margin: 0, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {coalition.leader_name}
            </h3>
            {coalition.member_count > 1 && (
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)' }}>+{coalition.member_count - 1}</span>
            )}
          </div>
          <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)' }}>
            {coalition.esi_members?.toLocaleString() || '?'} pilots
            {activeRate !== null && <span style={{ color: activeRate >= 20 ? '#00ff88' : '#ffcc00', marginLeft: '0.3rem' }}>{activeRate}%</span>}
          </div>
        </div>
        {/* Efficiency Badge */}
        <span style={{ fontSize: '0.8rem', fontWeight: 800, color: effColor, fontFamily: 'monospace' }}>
          {coalition.efficiency.toFixed(0)}%
        </span>
      </div>

      {/* Stats Row - Compact K/D + Sparkline */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.3rem', padding: '0.25rem 0.3rem', background: 'rgba(255,255,255,0.03)', borderRadius: '3px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem', fontSize: '0.7rem' }}>
          <span style={{ color: '#00ff88', fontWeight: 700, fontFamily: 'monospace' }}>{coalition.total_kills.toLocaleString()}</span>
          <span style={{ color: 'rgba(255,255,255,0.2)' }}>/</span>
          <span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>{coalition.total_losses.toLocaleString()}</span>
          <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.6rem' }}>({kdRatio})</span>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <DualLineSparkline kills={coalition.kills_series || []} deaths={coalition.deaths_series || []} width={60} height={18} />
        </div>
      </div>

      {/* ISK Row - Even more compact */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.2rem', fontSize: '0.6rem' }}>
        <span style={{ color: 'rgba(255,255,255,0.35)' }}>ISK:</span>
        <span style={{ color: '#00ff88', fontFamily: 'monospace' }}>+{formatISK(coalition.isk_destroyed)}</span>
        <span style={{ color: 'rgba(255,255,255,0.2)' }}>/</span>
        <span style={{ color: '#ff4444', fontFamily: 'monospace' }}>-{formatISK(coalition.isk_lost)}</span>
      </div>
    </Link>
  );
}
