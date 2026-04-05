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

interface ActiveCombatZonesProps {
  systems: HotSystem[];
  onSystemClick?: (systemId: number) => void;
}

const THREAT_CONFIG = {
  critical: { color: '#ff0000', bg: 'rgba(255,0,0,0.2)', pulse: true, label: 'CRITICAL' },
  hot: { color: '#ff6600', bg: 'rgba(255,102,0,0.15)', pulse: true, label: 'HOT' },
  active: { color: '#ffcc00', bg: 'rgba(255,204,0,0.1)', pulse: false, label: 'ACTIVE' },
  low: { color: '#888888', bg: 'rgba(136,136,136,0.1)', pulse: false, label: 'LOW' },
};

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

function getSecurityColor(sec: number): string {
  if (sec >= 0.5) return '#00ff88';
  if (sec > 0) return '#ffcc00';
  return '#ff4444';
}

export function ActiveCombatZones({ systems, onSystemClick }: ActiveCombatZonesProps) {
  const criticalCount = systems.filter(s => s.threat_level === 'critical').length;
  const hotCount = systems.filter(s => s.threat_level === 'hot').length;

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
      {/* CSS for pulse animation - must be first child to not affect flex layout */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
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
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: criticalCount > 0 ? '#ff0000' : hotCount > 0 ? '#ff6600' : '#ffcc00',
            animation: (criticalCount > 0 || hotCount > 0) ? 'pulse 1.5s infinite' : 'none',
          }} />
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase' }}>
            Active Engagements
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.6rem' }}>
          {criticalCount > 0 && (
            <span style={{ color: '#ff0000' }}>{criticalCount} crit</span>
          )}
          {hotCount > 0 && (
            <span style={{ color: '#ff6600' }}>{hotCount} hot</span>
          )}
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>{systems.length} sys</span>
        </div>
      </div>

      {/* Systems List - compact, scrollable */}
      <div style={{
        padding: '0.25rem',
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
      }}>
        {systems.length === 0 ? (
          <div style={{
            padding: '0.75rem',
            textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            fontSize: '0.7rem',
          }}>
            No active combat zones detected
          </div>
        ) : (
          systems.map((sys, idx) => {
            const config = THREAT_CONFIG[sys.threat_level];
            const timeAgo = sys.last_kill_minutes_ago !== null
              ? sys.last_kill_minutes_ago < 1 ? '<1m'
              : sys.last_kill_minutes_ago < 60 ? `${sys.last_kill_minutes_ago}m`
              : `${Math.floor(sys.last_kill_minutes_ago / 60)}h`
              : null;

            return (
              <div
                key={sys.solar_system_id}
                onClick={() => onSystemClick?.(sys.solar_system_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.49rem',
                  padding: '0.44rem 0.49rem',
                  marginBottom: idx < systems.length - 1 ? '0.2rem' : 0,
                  background: config.bg,
                  borderRadius: '4px',
                  borderLeft: `2px solid ${config.color}`,
                  cursor: onSystemClick ? 'pointer' : 'default',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = config.bg; }}
              >
                {/* Threat Badge */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px',
                  minWidth: '62px',
                }}>
                  {config.pulse && (
                    <span style={{
                      width: '5px',
                      height: '5px',
                      borderRadius: '50%',
                      background: config.color,
                      animation: 'pulse 1.5s infinite',
                    }} />
                  )}
                  <span style={{ fontSize: '0.69rem', fontWeight: 700, color: config.color }}>
                    {config.label}
                  </span>
                </div>

                {/* SOV Owner Logo */}
                {sys.sov_alliance_id ? (
                  <img
                    src={`https://images.evetech.net/alliances/${sys.sov_alliance_id}/logo?size=32`}
                    alt=""
                    style={{ width: 22, height: 22, borderRadius: '2px', background: 'rgba(0,0,0,0.3)' }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                ) : (
                  <div style={{
                    width: 22,
                    height: 22,
                    borderRadius: '2px',
                    background: 'rgba(255,255,255,0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.55rem',
                    color: 'rgba(255,255,255,0.3)',
                  }}>
                    {sys.security_status >= 0.45 ? 'HS' : sys.security_status > 0 ? 'LS' : 'NS'}
                  </div>
                )}

                {/* System Info - Inline */}
                <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: '0.39rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.7rem', color: '#fff', whiteSpace: 'nowrap' }}>
                    {sys.system_name}
                  </span>
                  <span style={{ fontSize: '0.74rem', color: getSecurityColor(sys.security_status), fontFamily: 'monospace' }}>
                    {sys.security_status.toFixed(1)}
                  </span>
                  <span style={{ fontSize: '0.69rem', color: 'rgba(255,255,255,0.35)', lineHeight: 1.1 }}>
                    {sys.region_name}
                  </span>
                  {sys.sov_alliance_ticker && (
                    <span style={{ fontSize: '0.69rem', color: '#00d4ff' }}>[{sys.sov_alliance_ticker}]</span>
                  )}
                </div>

                {/* Stats - Inline */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.49rem' }}>
                  {/* Kills */}
                  <span style={{ fontSize: '0.98rem', fontWeight: 700, fontFamily: 'monospace', color: config.color }}>
                    {sys.kill_count}
                  </span>

                  {/* ISK + Caps stacked */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.1 }}>
                    <span style={{ fontSize: '0.69rem', color: '#ffcc00', fontFamily: 'monospace' }}>
                      {formatISK(sys.total_value)}
                    </span>
                    {sys.capital_kills > 0 && (
                      <span style={{ fontSize: '0.57rem', color: '#a855f7', fontWeight: 600 }}>
                        {sys.capital_kills}cap
                      </span>
                    )}
                  </div>

                  {/* Time ago */}
                  {timeAgo && (
                    <span style={{
                      fontSize: '0.59rem',
                      color: sys.last_kill_minutes_ago !== null && sys.last_kill_minutes_ago <= 5 ? '#ff6666' : 'rgba(255,255,255,0.3)',
                      fontFamily: 'monospace',
                    }}>
                      {timeAgo}
                    </span>
                  )}

                  {/* LIVE indicator */}
                  {sys.last_kill_minutes_ago !== null && sys.last_kill_minutes_ago <= 5 && (
                    <span style={{
                      fontSize: '0.59rem',
                      padding: '1px 4px',
                      borderRadius: '2px',
                      background: 'rgba(255,0,0,0.4)',
                      color: '#ff6666',
                      fontWeight: 700,
                      animation: 'pulse 1.5s infinite',
                    }}>
                      LIVE
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
