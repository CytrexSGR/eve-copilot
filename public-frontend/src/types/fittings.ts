// --- Core ---
export interface FittingItem {
  type_id: number;
  flag: number;
  quantity: number;
}

export interface ESIFitting {
  fitting_id: number;
  name: string;
  description: string;
  ship_type_id: number;
  items: FittingItem[];
}

export interface CustomFitting {
  id: number;
  creator_character_id: number;
  name: string;
  description: string;
  ship_type_id: number;
  ship_name: string;
  items: FittingItem[];
  charges: FittingChargeMap;
  tags: string[];
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface SaveFittingRequest {
  creator_character_id: number;
  name: string;
  description: string;
  ship_type_id: number;
  items: FittingItem[];
  charges: FittingChargeMap;
  tags: string[];
  is_public: boolean;
}

// --- SDE ---
export interface ShipSummary {
  type_id: number;
  type_name: string;
  name?: string; // alias - some endpoints use 'name' instead of 'type_name'
  group_name: string;
  hi_slots: number;
  med_slots: number;
  low_slots: number;
  rig_slots: number;
  power_output: number;
  cpu_output: number;
  turret_hardpoints: number;
  launcher_hardpoints: number;
  rig_size: number;
}

export interface ShipDetail extends ShipSummary {
  shield_hp: number;
  armor_hp: number;
  hull_hp: number;
  capacitor_capacity: number;
  capacitor_recharge: number;
  max_velocity: number;
  agility: number;
  signature_radius: number;
  description?: string;
  mass?: number;
  volume?: number;
}

export interface ModuleSummary {
  type_id: number;
  name: string;
  group_name: string;
  slot_type: string;
  power: number;
  cpu: number;
  meta_level: number;
  hardpoint_type: 'turret' | 'launcher' | null;
}

// --- Implants ---
export interface ActiveImplant {
  type_id: number;
  type_name: string;
  slot: number;
}

// --- Stats ---
export interface DamageBreakdown {
  em: number;
  thermal: number;
  kinetic: number;
  explosive: number;
}

export interface ResistProfile {
  em: number;
  thermal: number;
  kinetic: number;
  explosive: number;
}

export interface OffenseStats {
  weapon_dps: number;
  drone_dps: number;
  fighter_dps: number;
  fighter_details?: FighterDPSStats[];
  total_dps: number;
  volley_damage: number;
  damage_breakdown: DamageBreakdown;
  overheated_weapon_dps?: number;
  overheated_total_dps?: number;
  spool?: SpoolStats;
}

export interface DefenseStats {
  total_ehp: number;
  shield_ehp: number;
  armor_ehp: number;
  hull_ehp: number;
  shield_hp: number;
  armor_hp: number;
  hull_hp: number;
  shield_resists: ResistProfile;
  armor_resists: ResistProfile;
  hull_resists: ResistProfile;
  tank_type: string;
}

export interface CapacitorStats {
  capacity: number;
  recharge_time: number;
  peak_recharge_rate: number;
  usage_rate: number;
  stable: boolean;
  stable_percent: number;
  lasts_seconds: number;
}

export interface NavigationStats {
  max_velocity: number;
  align_time: number;
  warp_speed: number;
  warp_time_5au: number;
  warp_time_20au: number;
  agility: number;
  signature_radius: number;
  mass: number;
  cargo_capacity: number;
}

export interface TargetingStats {
  max_range: number;
  scan_resolution: number;
  max_locked_targets: number;
  sensor_strength: number;
  sensor_type: string;
  lock_time: number;
  drone_control_range: number;
  scanability: number;
}

export interface SlotUsage {
  hi_used: number;
  hi_total: number;
  med_used: number;
  med_total: number;
  low_used: number;
  low_total: number;
  rig_used: number;
  rig_total: number;
}

export interface ResourceUsage {
  pg_used: number;
  pg_total: number;
  cpu_used: number;
  cpu_total: number;
  calibration_total: number;
  calibration_used: number;
  turret_hardpoints_total: number;
  turret_hardpoints_used: number;
  launcher_hardpoints_total: number;
  launcher_hardpoints_used: number;
  drone_bay_total: number;
  drone_bay_used: number;
  drone_bandwidth_total: number;
  drone_bandwidth_used: number;
}

export interface RepairStats {
  shield_rep: number;
  armor_rep: number;
  hull_rep: number;
  shield_passive_regen: number;
  shield_rep_ehp: number;
  armor_rep_ehp: number;
  sustained_tank_ehp: number;
  overheated_shield_rep?: number;
  overheated_armor_rep?: number;
  sustained_shield_rep?: number;
  sustained_armor_rep?: number;
}

export interface AppliedDPS {
  target_profile: string;
  turret_applied_dps: number;
  missile_applied_dps: number;
  drone_applied_dps: number;
  total_applied_dps: number;
  turret_hit_chance: number;
  missile_damage_factor: number;
  spool_applied?: SpoolStats;
}

export interface FittingViolation {
  resource: string;  // "cpu", "pg", "calibration", "maxGroupFitted", "maxTypeFitted"
  used: number;
  total: number;
  type_name?: string;
  group_name?: string;
}

export interface ModuleDetail {
  type_id: number;
  type_name: string;
  slot_type: string;  // "high", "mid", "low", "rig", "drone"
  flag: number;
  quantity: number;
  cpu: number;
  pg: number;
  cap_need: number;       // GJ per cycle
  cycle_time_ms: number;
  cap_per_sec: number;    // GJ/s
  charge_type_id?: number | null;
  charge_name?: string | null;
  hardpoint_type?: string | null;  // "turret", "launcher"
}

export interface SkillRequirement {
  skill_id: number;
  skill_name: string;
  required_level: number;
  trained_level: number | null;
  rank: number;
  sp_required: number;
  required_by: string[];
}

export interface FittingStats {
  ship: ShipSummary;
  slots: SlotUsage;
  resources: ResourceUsage;
  offense: OffenseStats;
  defense: DefenseStats;
  capacitor: CapacitorStats;
  navigation: NavigationStats;
  targeting: TargetingStats;
  repairs: RepairStats;
  applied_dps?: AppliedDPS;
  violations?: FittingViolation[];
  module_details?: ModuleDetail[];
  required_skills?: SkillRequirement[];
  skill_source?: string;
  character_id?: number;
  active_implants?: ActiveImplant[];
  mode?: string;
  active_boosts?: Array<{ buff_id: number; name: string; value: number }>;
  projected_effects_summary?: Array<{ effect_type: string; strength: number; count: number; stacking_penalized: boolean; cap_drain_per_s?: number; hp_per_s?: number }>;
  activatable_flags?: number[];
}

// --- Constants ---
export const SLOT_RANGES = {
  high: { start: 27, end: 34 },
  mid:  { start: 19, end: 26 },
  low:  { start: 11, end: 18 },
  rig:  { start: 92, end: 99 },
} as const;

export type SlotType = keyof typeof SLOT_RANGES;

export const SLOT_COLORS: Record<SlotType, string> = {
  high: '#f85149',
  mid:  '#00d4ff',
  low:  '#3fb950',
  rig:  '#d29922',
};

export const DAMAGE_COLORS: Record<string, string> = {
  em: '#00d4ff',
  thermal: '#ff4444',
  kinetic: '#888888',
  explosive: '#ff8800',
};

export const TANK_COLORS: Record<string, string> = {
  shield: '#00d4ff',
  armor: '#ff8800',
  hull: '#8b949e',
};

export const SHIP_CLASSES = [
  'Frigate', 'Destroyer', 'Cruiser', 'Battlecruiser', 'Battleship',
  'Carrier', 'Dreadnought', 'Force Auxiliary', 'Titan', 'Supercarrier',
  'Industrial', 'Mining Barge', 'Hauler',
] as const;

export const FITTING_TAGS = ['PvP', 'PvE', 'Fleet', 'Solo', 'Industry', 'Exploration', 'Abyssal'] as const;

export function getShipRenderUrl(typeId: number, size = 256): string {
  return `https://images.evetech.net/types/${typeId}/render?size=${size}`;
}

export function getTypeIconUrl(typeId: number, size = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`;
}

// --- Groups ---
export interface GroupSummary {
  group_id: number;
  group_name: string;
  count: number;
}

// --- Market Tree ---
export interface MarketGroupNode {
  market_group_id: number;
  name: string;
  has_types: boolean;
  child_count: number;
  icon_id: number | null;
}

// Market group root IDs
export const MARKET_ROOTS = {
  ships: 4,
  modules: 9,
  charges: 11,
  drones: 157,
} as const;

export type BrowserTab = 'hulls' | 'modules' | 'charges' | 'drones';

// --- Charges ---
export interface ChargeSummary {
  type_id: number;
  name: string;
  group_name: string;
  em: number;
  thermal: number;
  kinetic: number;
  explosive: number;
  meta_level: number;
}

// --- Editor State ---
export interface FittingChargeMap {
  [flag: number]: number;  // slot flag → charge type_id
}

export interface DroneEntry {
  type_id: number;
  count: number;
}

export type ModuleState = 'offline' | 'online' | 'active' | 'overheated';

export interface FighterInput {
  type_id: number;
  quantity: number;
}

export interface FleetBoostInput {
  buff_id: number;
  value: number;
}

export interface ProjectedEffectInput {
  effect_type: 'web' | 'paint' | 'neut' | 'remote_shield' | 'remote_armor';
  strength: number;
  count: number;
}

export type PickerMode =
  | { kind: 'module'; slotType: SlotType; flag: number }
  | { kind: 'charge'; flag: number; weaponTypeId: number }
  | { kind: 'drone' };

// --- Dogma v4 Response Models ---
export interface SpoolStats {
  min_dps: number;
  max_dps: number;
  avg_dps: number;
  cycles_to_max: number;
  time_to_max_s: number;
}

export interface FighterDPSStats {
  type_name: string;
  type_id: number;
  squadron_size: number;
  squadrons: number;
  dps_per_squadron: number;
  total_dps: number;
  damage_type: string;
}

export interface T3DMode {
  type_id: number;
  name: string;
}

export interface BoostPreset {
  buff_id: number;
  value: number;
  name: string;
}

export interface BuffDefinition {
  buff_id: number;
  name: string;
  attributes: number[];
  operation: string;
}

export const CARRIER_GROUPS = [547, 659, 1538];
