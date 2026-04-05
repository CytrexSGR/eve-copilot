// unified-frontend/src/types/capital.ts

// ==============================================================================
// Jump Planner Types
// ==============================================================================

export interface JumpShip {
  name: string
  base_range: number
  fuel_type: string
  fuel_per_ly: number
  skill_type: string
}

export interface JumpRange {
  ship_name: string
  base_range: number
  jdc_level: number
  jf_level: number | null
  effective_range: number
  fuel_type: string
  fuel_per_ly: number
}

export interface FatigueCalculation {
  distance_ly: number
  current_fatigue_minutes: number
  new_fatigue_minutes: number
  blue_timer_minutes: number
  red_timer_minutes: number
  fatigue_capped: boolean
  time_until_jump: string
  time_until_fatigue_clear: string
}

export interface SystemDistance {
  origin: { system_id: number; system_name: string; region_name: string }
  destination: { system_id: number; system_name: string; region_name: string }
  distance_ly: number
}

export interface CynoPosition {
  waypoint: number
  system_id: number
  system_name: string
  region: string
  security: number
  distance_ly: number
  fuel_required: number
  jammed: boolean
  has_station: boolean
  recommendation: string
}

export interface CynoAltRoute {
  route_type: 'direct' | 'multi-jump'
  origin: { system_id: number; system_name: string; region: string }
  destination: { system_id: number; system_name: string; region: string; jammed: boolean }
  ship: string
  effective_range: number
  total_distance: number
  total_jumps?: number
  total_fuel: number
  total_fatigue_minutes: number
  fatigue_clear_time?: string
  cyno_positions: CynoPosition[]
  warnings: string[]
  cyno_alt_checklist?: string[]
}

// ==============================================================================
// Structure Timer Types
// ==============================================================================

export type StructureCategory = 'tcu' | 'ihub' | 'poco' | 'pos' | 'ansiblex' | 'cyno_beacon' | 'cyno_jammer'
export type TimerType = 'armor' | 'hull' | 'anchoring' | 'unanchoring' | 'online'
export type Urgency = 'critical' | 'urgent' | 'upcoming' | 'planned'

export interface StructureTimer {
  id: number
  structure_id: number | null
  structure_name: string
  category: StructureCategory
  system_id: number
  system_name: string | null
  region_name: string | null
  owner_alliance_id: number | null
  owner_alliance_name: string | null
  timer_type: TimerType
  timer_end: string
  hours_until: number
  urgency: Urgency
  cyno_jammed: boolean
  is_active: boolean
  result: string | null
  source: string
  notes: string | null
}

export interface TimerSummary {
  critical: number
  urgent: number
  upcoming: number
  planned: number
  total: number
}

export interface TimersResponse {
  summary: TimerSummary
  timers: StructureTimer[]
}

export interface TimerCreateInput {
  structure_name: string
  category: StructureCategory
  system_id: number
  timer_type: TimerType
  timer_end: string
  structure_id?: number
  structure_type_id?: number
  owner_alliance_id?: number
  owner_alliance_name?: string
  owner_corporation_id?: number
  owner_corporation_name?: string
  reported_by?: string
  notes?: string
}

// ==============================================================================
// Cyno Jammer Types
// ==============================================================================

export interface CynoJammer {
  solar_system_id: number
  solar_system_name: string
  region_id: number
  region_name: string
  alliance_id: number | null
  alliance_name: string | null
  last_updated: string
}

export interface CynoJammerResponse {
  count: number
  jammers: CynoJammer[]
}
