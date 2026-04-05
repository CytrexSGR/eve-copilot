// Fitting system type definitions

export interface FittingItem {
  type_id: number
  flag: number
  quantity: number
}

export interface ESIFitting {
  fitting_id?: number
  name: string
  description: string
  ship_type_id: number
  items: FittingItem[]
}

export interface CustomFitting {
  id: number
  creator_character_id: number
  name: string
  description: string
  ship_type_id: number
  ship_name: string
  items: FittingItem[]
  tags: string[]
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface ShipSummary {
  type_id: number
  type_name: string
  group_id: number
  group_name: string
  hi_slots: number
  med_slots: number
  low_slots: number
  rig_slots: number
  power_output: number
  cpu_output: number
}

export interface ShipDetail extends ShipSummary {
  capacitor_capacity: number
  capacitor_recharge: number
  max_velocity: number
  agility: number
  signature_radius: number
  shield_hp: number
  armor_hp: number
  hull_hp: number
}

export interface ModuleSummary {
  type_id: number
  type_name: string
  group_id: number
  group_name: string
  slot_type: string
  cpu: number
  power: number
  meta_level: number
}

export interface SlotUsage {
  hi_total: number
  hi_used: number
  med_total: number
  med_used: number
  low_total: number
  low_used: number
  rig_total: number
  rig_used: number
}

export interface ResourceUsage {
  pg_total: number
  pg_used: number
  cpu_total: number
  cpu_used: number
}

export interface DamageBreakdown {
  em: number
  thermal: number
  kinetic: number
  explosive: number
}

export interface ResistProfile {
  em: number
  thermal: number
  kinetic: number
  explosive: number
}

export interface OffenseStats {
  total_dps: number
  damage_breakdown: DamageBreakdown
}

export interface DefenseStats {
  total_ehp: number
  shield_ehp: number
  armor_ehp: number
  hull_ehp: number
  shield_resists: ResistProfile
  armor_resists: ResistProfile
  hull_resists: ResistProfile
  tank_type: string
}

export interface NavigationStats {
  max_velocity: number
  agility: number
  signature_radius: number
}

export interface FittingStats {
  ship: {
    type_id: number
    name: string
    group_name: string
  }
  slots: SlotUsage
  resources: ResourceUsage
  offense: OffenseStats
  defense: DefenseStats
  navigation: NavigationStats
}

export type SlotType = 'high' | 'mid' | 'low' | 'rig'

export type ShipClass =
  | 'all'
  | 'Frigate'
  | 'Destroyer'
  | 'Cruiser'
  | 'Battlecruiser'
  | 'Battleship'
  | 'Capital'

// Slot flag ranges
export const SLOT_RANGES: Record<SlotType, [number, number]> = {
  high: [27, 34],
  mid: [19, 26],
  low: [11, 18],
  rig: [92, 99],
}

// EVE image URLs
export const getShipRenderUrl = (typeId: number, size = 256) =>
  `https://images.evetech.net/types/${typeId}/render?size=${size}`

export const getModuleIconUrl = (typeId: number, size = 32) =>
  `https://images.evetech.net/types/${typeId}/icon?size=${size}`

// Damage type colors
export const DAMAGE_COLORS = {
  em: '#00d4ff',
  thermal: '#ff4444',
  kinetic: '#888888',
  explosive: '#ff8800',
} as const

// Tank type colors
export const TANK_COLORS = {
  shield: '#00d4ff',
  armor: '#ff8800',
  hull: '#8b949e',
} as const
