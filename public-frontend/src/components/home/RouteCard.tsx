import { DANGER_THRESHOLDS, DANGER_COLORS } from '../../constants';

interface RouteSystem {
  system_name: string;
  is_gate_camp: boolean;
}

interface TradeRoute {
  origin_system: string;
  destination_system: string;
  jumps: number;
  danger_score: number;
  total_kills?: number;
  total_isk_destroyed?: number;
  systems?: RouteSystem[];
}

interface RouteCardProps {
  route: TradeRoute;
}

function formatCompactISK(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e12) return (value / 1e12).toFixed(1) + 'T';
  if (abs >= 1e9) return (value / 1e9).toFixed(1) + 'B';
  if (abs >= 1e6) return (value / 1e6).toFixed(0) + 'M';
  return value.toFixed(0);
}

export function RouteCard({ route }: RouteCardProps) {
  const dangerLevel = getDangerLevel(route.danger_score);
  const dangerColor = DANGER_COLORS[dangerLevel];
  const gateCampSystems = route.systems?.filter((s) => s.is_gate_camp) || [];

  return (
    <div style={{
      padding: '0.3rem 0.5rem',
      background: `${dangerColor}08`,
      borderRadius: '4px',
      borderLeft: `2px solid ${dangerColor}`,
    }}>
      {/* Line 1: Route + Badge + Stats */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.4rem',
      }}>
        <span style={{
          fontSize: '0.7rem', fontWeight: 600, color: '#fff',
          whiteSpace: 'nowrap',
        }}>
          {route.origin_system}
        </span>
        <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)' }}>→</span>
        <span style={{
          fontSize: '0.7rem', fontWeight: 600, color: '#fff',
          whiteSpace: 'nowrap',
        }}>
          {route.destination_system}
        </span>

        <span style={{
          fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)',
          fontFamily: 'monospace',
        }}>
          {route.jumps}j
        </span>

        <span style={{
          padding: '1px 5px',
          background: `${dangerColor}22`,
          border: `1px solid ${dangerColor}44`,
          borderRadius: '3px',
          fontWeight: 700,
          fontSize: '0.5rem',
          color: dangerColor,
          textTransform: 'uppercase',
        }}>
          {dangerLevel}
        </span>

        <div style={{ flex: 1 }} />

        <span style={{ fontSize: '0.55rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 600 }}>
          {route.total_kills || 0}
        </span>
        <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
          {formatCompactISK(route.total_isk_destroyed || 0)}
        </span>
      </div>

      {/* Line 2: Gate camps */}
      {gateCampSystems.length > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
          marginTop: '0.15rem',
          paddingLeft: '0.1rem',
        }}>
          <span style={{ fontSize: '0.5rem', color: '#ff8800', fontWeight: 600 }}>
            CAMP
          </span>
          <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
            {gateCampSystems.map((s) => s.system_name).join(', ')}
          </span>
        </div>
      )}
    </div>
  );
}

function getDangerLevel(score: number): keyof typeof DANGER_COLORS {
  if (score >= DANGER_THRESHOLDS.CRITICAL) return 'CRITICAL';
  if (score >= DANGER_THRESHOLDS.HIGH) return 'HIGH';
  if (score >= DANGER_THRESHOLDS.MODERATE) return 'MODERATE';
  return 'SAFE';
}
