// Types inlined to avoid Vite module resolution issues with .types.ts files
export type RoutePerspective = 'threat' | 'logistics';

export interface RouteSystemData {
  system_id: number;
  system_name: string;
  security_status: number;
  danger_score: number;
  kills: number;
  isk_destroyed: number;
  is_gate_camp: boolean;
  battle_id?: number;
}

export interface TradeRouteData {
  origin: string;
  destination: string;
  jumps: number;
  danger_score: number;
  total_kills: number;
  total_isk: number;
  gate_camps: number;
  systems: RouteSystemData[];
}

export interface TradeRouteStatusProps {
  route: TradeRouteData;
  perspective: RoutePerspective;
  compact?: boolean;
  onSystemClick?: (systemId: number, battleId?: number) => void;
}

const PERSPECTIVE_CONFIG: Record<RoutePerspective, {
  high: { color: string; label: string; bg: string };
  medium: { color: string; label: string; bg: string };
  low: { color: string; label: string; bg: string };
  metric: string;
  metricLabel: string;
}> = {
  threat: {
    high: { color: '#ff4444', label: 'DANGEROUS', bg: 'rgba(255,68,68,0.15)' },
    medium: { color: '#ffaa00', label: 'CAUTION', bg: 'rgba(255,170,0,0.15)' },
    low: { color: '#00ff88', label: 'CLEAR', bg: 'rgba(0,255,136,0.15)' },
    metric: 'kills',
    metricLabel: 'threats',
  },
  logistics: {
    high: { color: '#00ff88', label: 'HIGH DEMAND', bg: 'rgba(0,255,136,0.15)' },
    medium: { color: '#ffaa00', label: 'MODERATE', bg: 'rgba(255,170,0,0.15)' },
    low: { color: '#888888', label: 'LOW ACTIVITY', bg: 'rgba(136,136,136,0.15)' },
    metric: 'opportunity',
    metricLabel: 'demand signals',
  },
};

function getDangerLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 60) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

export function TradeRouteStatus({
  route,
  perspective,
  compact = false,
  onSystemClick
}: TradeRouteStatusProps) {
  const config = PERSPECTIVE_CONFIG[perspective];
  const level = getDangerLevel(route.danger_score);
  const style = config[level];

  const barColor = style.color;
  const barWidth = Math.min(100, route.danger_score);

  return (
    <div
      style={{
        padding: compact ? '0.5rem' : '0.75rem',
        background: 'rgba(0,0,0,0.4)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.08)',
        borderLeft: `3px solid ${barColor}`,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontWeight: 700, fontSize: compact ? '0.8rem' : '0.9rem' }}>
            {route.origin} → {route.destination}
          </span>
          <span style={{
            fontSize: '0.65rem',
            padding: '0.15rem 0.4rem',
            borderRadius: '3px',
            background: style.bg,
            color: style.color,
            fontWeight: 600,
          }}>
            {style.label}
          </span>
        </div>
        <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
          {route.jumps} jumps
        </span>
      </div>

      {/* Danger/Opportunity Bar */}
      <div style={{
        height: '4px',
        background: 'rgba(255,255,255,0.1)',
        borderRadius: '2px',
        marginBottom: '0.5rem',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${barWidth}%`,
          height: '100%',
          background: barColor,
          borderRadius: '2px',
          transition: 'width 0.3s ease',
        }} />
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
        <span>
          <span style={{ color: barColor, fontWeight: 600, fontFamily: 'monospace' }}>
            {route.total_kills}
          </span>
          <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>
            {config.metricLabel}
          </span>
        </span>
        <span>
          <span style={{ color: '#00d4ff', fontWeight: 600, fontFamily: 'monospace' }}>
            {formatISK(route.total_isk)}
          </span>
          <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>
            {perspective === 'threat' ? 'destroyed' : 'market size'}
          </span>
        </span>
        {route.gate_camps > 0 && (
          <span style={{ color: '#ff4444' }}>
            {route.gate_camps} gate camp{route.gate_camps > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Hotspot Systems (non-compact) */}
      {!compact && route.systems.filter(s => s.danger_score >= 40).length > 0 && (
        <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', marginBottom: '0.25rem' }}>
            {perspective === 'threat' ? 'DANGER ZONES' : 'HOTSPOTS'}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {route.systems
              .filter(s => s.danger_score >= 40)
              .slice(0, 3)
              .map(sys => (
                <span
                  key={sys.system_id}
                  onClick={() => onSystemClick?.(sys.system_id, sys.battle_id)}
                  style={{
                    fontSize: '0.7rem',
                    padding: '0.2rem 0.4rem',
                    background: sys.is_gate_camp ? 'rgba(255,68,68,0.2)' : 'rgba(255,255,255,0.05)',
                    borderRadius: '3px',
                    cursor: onSystemClick ? 'pointer' : 'default',
                  }}
                >
                  {sys.system_name}: {sys.kills}
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
