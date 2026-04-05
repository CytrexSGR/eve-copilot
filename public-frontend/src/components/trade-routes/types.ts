export interface RouteSystem {
  system_id: number;
  system_name: string;
  security_status: number;
  danger_score: number;
  kills_24h: number;
  isk_destroyed_24h: number;
  is_gate_camp: boolean;
  battle_id?: number;
}

export interface SystemTooltipData {
  system: Omit<RouteSystem, 'system_id'>;
  x: number;
  y: number;
}

export const TIME_PERIODS = [
  { value: 10, label: '10m' },
  { value: 60, label: '1h' },
  { value: 360, label: '6h' },
  { value: 720, label: '12h' },
  { value: 1440, label: '24h' },
] as const;

export type TimePeriodValue = typeof TIME_PERIODS[number]['value'];

export function getDangerLevel(score: number) {
  if (score >= 7) return { label: 'CRITICAL', color: '#ff4444' };
  if (score >= 4) return { label: 'HIGH', color: '#ff8800' };
  if (score >= 2) return { label: 'MODERATE', color: '#ffcc00' };
  return { label: 'SAFE', color: '#00ff88' };
}
