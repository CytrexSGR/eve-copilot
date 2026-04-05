import { Link } from 'react-router-dom';
import type { Coalition } from '../../types/reports';

interface PowerBlocsSectionProps {
  coalitions: Coalition[] | undefined;
}

function MiniSparkline({ kills, deaths, width = 50, height = 16 }: { kills: number[]; deaths: number[]; width?: number; height?: number }) {
  if (!kills?.length && !deaths?.length) return null;
  const allValues = [...(kills || []), ...(deaths || [])];
  const max = Math.max(...allValues) || 1;
  const dataLen = Math.max(kills?.length || 0, deaths?.length || 0);
  const getPoints = (data: number[] | undefined) => {
    if (!data || data.length < 2) return '';
    return data.map((v, i) => {
      const x = (i / (dataLen - 1)) * width;
      const y = height - (v / max) * (height - 4) - 2;
      return `${x},${y}`;
    }).join(' ');
  };
  return (
    <svg width={width} height={height} style={{ display: 'block', flexShrink: 0 }}>
      {getPoints(kills) && <polyline points={getPoints(kills)} fill="none" stroke="#00ff88" strokeWidth="1" />}
      {getPoints(deaths) && <polyline points={getPoints(deaths)} fill="none" stroke="#ff4444" strokeWidth="1" opacity="0.7" />}
    </svg>
  );
}

export function PowerBlocsSection({ coalitions }: PowerBlocsSectionProps) {
  if (!coalitions?.length) return null;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#a855f7' }} />
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase' }}>
          Power Blocs
        </span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          {coalitions.length} coalitions
        </span>
        <Link to="/battle-report#alliances" style={{
          marginLeft: 'auto', padding: '3px 8px',
          background: 'rgba(168,85,247,0.1)', color: '#a855f7',
          borderRadius: '3px', textDecoration: 'none',
          fontSize: '0.6rem', fontWeight: 600,
          border: '1px solid rgba(168,85,247,0.2)',
          textTransform: 'uppercase',
        }}>
          Full Intel
        </Link>
      </div>

      {/* Grid of compact coalition rows */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '0.3rem',
        padding: '0.4rem',
      }}>
        {coalitions.map((c) => {
          const effColor = c.efficiency >= 55 ? '#00ff88' : c.efficiency >= 45 ? '#ffcc00' : '#ff4444';
          return (
            <Link
              key={c.leader_alliance_id}
              to={`/powerbloc/${c.leader_alliance_id}`}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.4rem',
                padding: '0.35rem 0.5rem',
                background: `${effColor}08`,
                borderRadius: '4px', borderLeft: `2px solid ${effColor}`,
                textDecoration: 'none', color: 'inherit',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = `${effColor}08`; }}
            >
              <img
                src={`https://images.evetech.net/alliances/${c.leader_alliance_id}/logo?size=32`}
                alt="" width={20} height={20}
                style={{ borderRadius: '3px', background: 'rgba(0,0,0,0.3)' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{
                  fontSize: '0.7rem', fontWeight: 600, color: '#fff',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  maxWidth: '120px',
                }}>
                  {c.leader_name}
                </span>
                {c.member_count > 1 && (
                  <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.3)' }}>+{c.member_count - 1}</span>
                )}
              </div>
              <span style={{ fontSize: '0.6rem', color: '#00ff88', fontFamily: 'monospace', fontWeight: 600 }}>
                {c.total_kills.toLocaleString()}
              </span>
              <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.2)' }}>/</span>
              <span style={{ fontSize: '0.6rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 600 }}>
                {c.total_losses.toLocaleString()}
              </span>
              <MiniSparkline kills={[]} deaths={[]} />
              <span style={{
                fontSize: '0.65rem', fontWeight: 700, color: effColor,
                fontFamily: 'monospace', minWidth: '28px', textAlign: 'right',
              }}>
                {c.efficiency.toFixed(0)}%
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
