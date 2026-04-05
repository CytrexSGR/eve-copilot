import { Link } from 'react-router-dom';
import type { Conflict } from '../../types/reports';
import { formatISK } from '../../utils/security';

const TIME_STATUS_CONFIG: Record<string, { color: string; bg: string; pulse: boolean }> = {
  '10m': { color: '#ff0000', bg: 'rgba(255,0,0,0.15)', pulse: true },
  '1h': { color: '#ff4444', bg: 'rgba(255,68,68,0.12)', pulse: true },
  '12h': { color: '#ffcc00', bg: 'rgba(255,204,0,0.1)', pulse: false },
  '24h': { color: '#00d4ff', bg: 'rgba(0,212,255,0.08)', pulse: false },
  '7d': { color: '#888888', bg: 'rgba(136,136,136,0.08)', pulse: false },
};

const TREND_CONFIG: Record<string, { color: string; icon: string }> = {
  escalating: { color: '#ff0000', icon: '↗' },
  stable: { color: 'rgba(255,255,255,0.4)', icon: '→' },
  cooling: { color: '#00ff88', icon: '↘' },
};

const TIME_STATUS_ORDER: Record<string, number> = {
  '10m': 0,
  '1h': 1,
  '12h': 2,
  '24h': 3,
  '7d': 4,
};

interface ConflictDashboardProps {
  conflicts: Conflict[];
  loading?: boolean;
  error?: string | null;
}

export function ConflictDashboard({ conflicts, loading, error }: ConflictDashboardProps) {
  // Sort by time_status (freshest first)
  const sortedConflicts = [...conflicts].sort((a, b) => {
    const orderA = TIME_STATUS_ORDER[a.time_status] ?? 5;
    const orderB = TIME_STATUS_ORDER[b.time_status] ?? 5;
    return orderA - orderB;
  });

  const escalatingCount = conflicts.filter(c => c.trend === 'escalating').length;
  // Reserved for future use: conflicts.filter(c => c.time_status === '10m' || c.time_status === '1h').length;
  const totalKills = conflicts.reduce((sum, c) => sum + c.total_kills, 0);
  const totalIsk = conflicts.reduce((sum, c) => sum + c.total_isk, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      height: '480px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* CSS for animations */}
      <style>{`
        @keyframes conflictPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.3); }
        }
        @keyframes borderGlow {
          0%, 100% { border-left-color: #ff4444; }
          50% { border-left-color: #ff0000; }
        }
      `}</style>

      {/* Header - Compact */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {escalatingCount > 0 && (
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: '#ff0000',
              animation: 'conflictPulse 1.5s infinite',
            }} />
          )}
          <span style={{ fontSize: '0.65rem' }}>⚔️</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase' }}>
            Coalition Wars
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.55rem' }}>
          {totalKills > 0 && (
            <span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>{totalKills.toLocaleString()}</span>
          )}
          {totalIsk > 0 && (
            <span style={{ color: '#ffcc00', fontFamily: 'monospace' }}>{formatISK(totalIsk)}</span>
          )}
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>{conflicts.length} active</span>
        </div>
      </div>

      {/* Conflicts List */}
      <div style={{
        padding: '0.25rem',
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
      }}>
        {loading && (
          <div style={{ padding: '0.5rem' }}>
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton" style={{ height: '48px', borderRadius: '4px', marginBottom: '0.2rem' }} />
            ))}
          </div>
        )}

        {error && !loading && (
          <div style={{
            padding: '0.75rem',
            textAlign: 'center',
            color: '#ff4444',
            fontSize: '0.7rem',
          }}>
            {error}
          </div>
        )}

        {!loading && !error && conflicts.length === 0 && (
          <div style={{
            padding: '1.5rem',
            textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            fontSize: '0.7rem',
          }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem', opacity: 0.5 }}>☮️</div>
            No active coalition conflicts
          </div>
        )}

        {!loading && !error && sortedConflicts.map((conflict, idx) => {
          const timeConfig = TIME_STATUS_CONFIG[conflict.time_status] || TIME_STATUS_CONFIG['7d'];
          const trendConfig = TREND_CONFIG[conflict.trend] || TREND_CONFIG['stable'];
          const isEscalating = conflict.trend === 'escalating';
          const isHot = conflict.time_status === '10m' || conflict.time_status === '1h';

          return (
            <Link
              key={conflict.conflict_id}
              to={`/conflicts/${conflict.conflict_id}`}
              state={{ conflict }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.2rem 0.4rem',
                marginBottom: idx < sortedConflicts.length - 1 ? '0.2rem' : 0,
                background: timeConfig.bg,
                borderRadius: '4px',
                borderLeft: `2px solid ${timeConfig.color}`,
                textDecoration: 'none',
                transition: 'all 0.15s ease',
                animation: isEscalating ? 'borderGlow 2s infinite' : 'none',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = timeConfig.bg; }}
            >
              {/* Time Badge + Trend */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                minWidth: '32px',
              }}>
                <span style={{
                  fontSize: '0.5rem',
                  fontWeight: 700,
                  color: timeConfig.color,
                  textTransform: 'uppercase',
                }}>
                  {conflict.time_status}
                </span>
                <span style={{
                  fontSize: '0.6rem',
                  color: trendConfig.color,
                  fontWeight: 700,
                }}>
                  {trendConfig.icon}
                </span>
              </div>

              {/* Alliance Logos - Compact */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1px' }}>
                <img
                  src={`https://images.evetech.net/alliances/${conflict.coalition_a.leader_id}/logo?size=32`}
                  alt=""
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: '2px',
                    border: '1px solid #00d4ff',
                    background: 'rgba(0,0,0,0.5)',
                  }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
                <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.25)' }}>⚔</span>
                <img
                  src={`https://images.evetech.net/alliances/${conflict.coalition_b.leader_id}/logo?size=32`}
                  alt=""
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: '2px',
                    border: '1px solid #ff8800',
                    background: 'rgba(0,0,0,0.5)',
                  }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              </div>

              {/* Coalition Names + Region */}
              <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  <span style={{ color: '#00d4ff' }}>[{conflict.coalition_a.leader_ticker}]</span>
                  <span style={{ color: '#fff' }}>vs</span>
                  <span style={{ color: '#ff8800' }}>[{conflict.coalition_b.leader_ticker}]</span>
                </div>
                <div style={{
                  fontSize: '0.55rem',
                  color: 'rgba(255,255,255,0.4)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {conflict.regions.slice(0, 2).join(', ')}{conflict.regions.length > 2 ? ` +${conflict.regions.length - 2}` : ''}
                </div>
              </div>

              {/* Efficiency Mini-Bar */}
              <div style={{ width: '40px' }}>
                <div style={{
                  display: 'flex',
                  height: '4px',
                  borderRadius: '2px',
                  overflow: 'hidden',
                  background: 'rgba(255,255,255,0.1)',
                }}>
                  <div style={{ width: `${conflict.coalition_a.efficiency}%`, background: '#00d4ff' }} />
                  <div style={{ width: `${conflict.coalition_b.efficiency}%`, background: '#ff8800' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.45rem', marginTop: '1px' }}>
                  <span style={{ color: '#00d4ff' }}>{conflict.coalition_a.efficiency.toFixed(0)}%</span>
                  <span style={{ color: '#ff8800' }}>{conflict.coalition_b.efficiency.toFixed(0)}%</span>
                </div>
              </div>

              {/* Stats */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                minWidth: '50px',
              }}>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  fontFamily: 'monospace',
                  color: isHot ? '#ff4444' : 'rgba(255,255,255,0.7)',
                }}>
                  {conflict.total_kills}
                </span>
                <span style={{
                  fontSize: '0.5rem',
                  color: '#ffcc00',
                  fontFamily: 'monospace',
                }}>
                  {formatISK(conflict.total_isk)}
                </span>
              </div>

              {/* Battles Count */}
              <div style={{
                padding: '0.15rem 0.3rem',
                background: 'rgba(0,212,255,0.2)',
                borderRadius: '3px',
                fontSize: '0.5rem',
                color: '#00d4ff',
                fontWeight: 700,
              }}>
                {conflict.battles.length}B
              </div>

              {/* Caps if any */}
              {conflict.capital_kills > 0 && (
                <div style={{
                  padding: '0.15rem 0.3rem',
                  background: 'rgba(168,85,247,0.2)',
                  borderRadius: '3px',
                  fontSize: '0.5rem',
                  color: '#a855f7',
                  fontWeight: 700,
                }}>
                  {conflict.capital_kills}C
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
