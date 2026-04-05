export interface JumpShip {
  name: string;
  base_range: number;
  fuel_type: string;
  fuel_per_ly: number;
  skill_type: string;
}

export interface JumpRange {
  ship_name: string;
  base_range: number;
  jdc_level: number;
  jf_level: number;
  effective_range: number;
  fuel_type: string;
  fuel_per_ly: number;
}

export interface SystemInfo {
  system_id: number;
  system_name: string;
  region_name: string;
  constellation_name?: string;
  security: number;
  x: number;
  y: number;
  z: number;
}

export interface RouteWaypoint {
  system: SystemInfo;
  distance_ly: number;
  fuel_required: number;
  cumulative_fuel: number;
  is_cyno_system: boolean;
  has_station: boolean;
  jammed: boolean;
}

export interface JumpRoute {
  origin: SystemInfo;
  destination: SystemInfo;
  ship_name: string;
  effective_range: number;
  waypoints: RouteWaypoint[];
  total_jumps: number;
  total_distance: number;
  total_fuel: number;
  total_time_minutes: number;
  route_possible: boolean;
  error_message?: string;
}

export interface FatigueResult {
  distance_ly: number;
  current_fatigue_minutes: number;
  new_fatigue_minutes: number;
  blue_timer_minutes: number;
  red_timer_minutes: number;
  fatigue_capped: boolean;
  time_until_jump: number;
  time_until_fatigue_clear: number;
}

export interface CynoAltPlan {
  route_type: string;
  origin: SystemInfo;
  destination: SystemInfo;
  ship: JumpRange;
  effective_range: number;
  total_distance: number;
  total_jumps: number;
  total_fuel: number;
  total_fatigue_minutes: number;
  fatigue_clear_time: number;
  cyno_positions: CynoPosition[];
  warnings: string[];
  cyno_alt_checklist: string[];
}

export interface CynoPosition {
  waypoint: number;
  system_id: number;
  system_name: string;
  region: string;
  security: number;
  distance_ly: number;
  fuel_required: number;
  jammed: boolean;
  has_station: boolean;
  recommendation: string;
}

export const SYSTEM_PRESETS = [
  { name: 'Jita', region: 'The Forge', type: 'trade' as const },
  { name: 'Amarr', region: 'Domain', type: 'trade' as const },
  { name: 'Dodixie', region: 'Sinq Laison', type: 'trade' as const },
  { name: 'Rens', region: 'Heimatar', type: 'trade' as const },
  { name: 'Hek', region: 'Metropolis', type: 'trade' as const },
  { name: '1DQ1-A', region: 'Delve', type: 'staging' as const },
  { name: 'R1O-GN', region: 'Tribute', type: 'staging' as const },
  { name: 'K-6K16', region: 'Geminate', type: 'staging' as const },
  { name: 'GE-8JV', region: 'Catch', type: 'staging' as const },
  { name: 'HED-GP', region: 'Catch', type: 'staging' as const },
  { name: 'Amamake', region: 'Heimatar', type: 'lowsec' as const },
  { name: 'Tama', region: 'The Citadel', type: 'lowsec' as const },
];
