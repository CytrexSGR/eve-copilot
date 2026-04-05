interface TradeRoute {
  origin_system: string;
  destination_system: string;
  jumps: number;
  danger_score: number;
  total_kills: number;
  total_isk_destroyed: number;
  systems: Array<{
    system_id: number;
    system_name: string;
    security_status: number;
    danger_score: number;
    kills_24h: number;
    isk_destroyed_24h: number;
    is_gate_camp: boolean;
    battle_id?: number;
  }>;
}

interface TradeRouteThreatsProps {
  routes: TradeRoute[];
  onRouteClick?: (origin: string, destination: string) => void;
  onSystemClick?: (systemId: number, battleId?: number) => void;
}

const DANGER_CONFIG = {
  high: { color: '#ff4444', bg: 'rgba(255,68,68,0.2)', label: 'DANGER' },
  medium: { color: '#ffaa00', bg: 'rgba(255,170,0,0.15)', label: 'CAUTION' },
  low: { color: '#00ff88', bg: 'rgba(0,255,136,0.1)', label: 'CLEAR' },
};

function calculateRouteDanger(route: TradeRoute): number {
  // Backend danger_score is avg across all systems - useless for long routes
  // Calculate actual danger based on:
  // 1. Max system danger (most dangerous point)
  // 2. Total kills normalized by route length
  // 3. Gate camps are extra dangerous

  const maxSystemDanger = Math.max(...(route.systems?.map(s => s.danger_score) || [0]));
  const killsPerJump = route.total_kills / Math.max(1, route.jumps);
  const gateCamps = route.systems?.filter(s => s.is_gate_camp).length || 0;

  // Score components:
  // - Max system danger contributes 40%
  // - Kills per jump (scaled) contributes 40%
  // - Gate camps add flat bonus
  const killScore = Math.min(100, killsPerJump * 10); // 10 kills/jump = 100
  const gateCampBonus = gateCamps * 15;

  return Math.min(100, (maxSystemDanger * 0.4) + (killScore * 0.4) + gateCampBonus);
}

function getDangerLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 40) return 'high';
  if (score >= 20) return 'medium';
  return 'low';
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

export function TradeRouteThreats({ routes, onRouteClick, onSystemClick: _onSystemClick }: TradeRouteThreatsProps) {
  // Calculate actual danger scores for all routes
  const routesWithDanger = routes.map(r => ({
    ...r,
    calculatedDanger: calculateRouteDanger(r)
  }));

  const dangerousCount = routesWithDanger.filter(r => r.calculatedDanger >= 40).length;
  const cautionCount = routesWithDanger.filter(r => r.calculatedDanger >= 20 && r.calculatedDanger < 40).length;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      {/* Header - Compact */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>🚚</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ffcc00', textTransform: 'uppercase' }}>
            Trade Route Threats
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.6rem' }}>
          {dangerousCount > 0 && (
            <span style={{ color: '#ff4444' }}>{dangerousCount} danger</span>
          )}
          {cautionCount > 0 && (
            <span style={{ color: '#ffaa00' }}>{cautionCount} caution</span>
          )}
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>{routesWithDanger.length} routes</span>
        </div>
      </div>

      {/* Routes Grid - Horizontal */}
      <div style={{
        padding: '0.4rem',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '0.4rem',
      }}>
        {routesWithDanger.length === 0 ? (
          <div style={{
            padding: '0.75rem',
            textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            fontSize: '0.7rem',
          }}>
            No trade route data available
          </div>
        ) : (
          routesWithDanger.map((route, idx) => {
            const level = getDangerLevel(route.calculatedDanger);
            const config = DANGER_CONFIG[level];
            const gateCamps = route.systems?.filter(s => s.is_gate_camp).length || 0;

            return (
              <div
                key={idx}
                onClick={() => onRouteClick?.(route.origin_system, route.destination_system)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.49rem',
                  padding: '0.44rem 0.49rem',
                  marginBottom: idx < routesWithDanger.length - 1 ? '0.2rem' : 0,
                  background: config.bg,
                  borderRadius: '4px',
                  borderLeft: `2px solid ${config.color}`,
                  cursor: onRouteClick ? 'pointer' : 'default',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = config.bg; }}
              >
                {/* Danger Badge */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px',
                  minWidth: '62px',
                }}>
                  <span style={{
                    width: '5px',
                    height: '5px',
                    borderRadius: '50%',
                    background: config.color,
                  }} />
                  <span style={{ fontSize: '0.69rem', fontWeight: 700, color: config.color }}>
                    {config.label}
                  </span>
                </div>

                {/* Route Info - Inline */}
                <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: '0.39rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.7rem', color: '#fff', whiteSpace: 'nowrap' }}>
                    {route.origin_system}
                  </span>
                  <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.35)' }}>→</span>
                  <span style={{ fontWeight: 700, fontSize: '0.7rem', color: '#fff', whiteSpace: 'nowrap' }}>
                    {route.destination_system}
                  </span>
                  <span style={{ fontSize: '0.69rem', color: 'rgba(255,255,255,0.35)' }}>
                    {route.jumps}j
                  </span>
                </div>

                {/* Stats - Inline */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.49rem' }}>
                  {/* Kills */}
                  <span style={{ fontSize: '0.98rem', fontWeight: 700, fontFamily: 'monospace', color: config.color }}>
                    {route.total_kills}
                  </span>

                  {/* ISK + Gate camps stacked */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.1 }}>
                    <span style={{ fontSize: '0.69rem', color: '#ffcc00', fontFamily: 'monospace' }}>
                      {formatISK(route.total_isk_destroyed)}
                    </span>
                    {gateCamps > 0 && (
                      <span style={{ fontSize: '0.57rem', color: '#ff4444', fontWeight: 600 }}>
                        {gateCamps}gc
                      </span>
                    )}
                  </div>

                  {/* Danger score bar */}
                  <div style={{
                    width: '30px',
                    height: '4px',
                    background: 'rgba(255,255,255,0.1)',
                    borderRadius: '2px',
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${Math.min(100, route.calculatedDanger)}%`,
                      height: '100%',
                      background: config.color,
                      borderRadius: '2px',
                    }} />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
