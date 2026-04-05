// Doctrine types

export interface DoctrineSlotItem {
  type_id: number;
  type_name?: string;
  quantity: number;
}

export interface DoctrineFitting {
  high: DoctrineSlotItem[];
  med: DoctrineSlotItem[];
  low: DoctrineSlotItem[];
  rig: DoctrineSlotItem[];
  drones: DoctrineSlotItem[];
}

export interface Doctrine {
  id: number;
  corporation_id: number;
  name: string;
  ship_type_id: number;
  ship_name: string | null;
  fitting_json: DoctrineFitting;
  is_active: boolean;
  base_payout: number | null;
  category?: DoctrineCategory;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface DoctrineCreate {
  corporation_id: number;
  name: string;
  ship_type_id: number;
  fitting: DoctrineFitting;
  base_payout?: number;
  created_by?: number;
  category?: DoctrineCategory;
}

export interface DoctrineImportEft {
  corporation_id: number;
  eft_text: string;
  base_payout?: number;
  created_by?: number;
  category?: DoctrineCategory;
}


export interface DoctrineImportFittingItem {
  type_id: number;
  flag: number;
  quantity: number;
}

export interface DoctrineImportFitting {
  name: string;
  ship_type_id: number;
  items: DoctrineImportFittingItem[];
  base_payout?: number;
  category?: DoctrineCategory;
  corporation_id: number;
  created_by?: number;
}

// SRP types

export interface SrpMatchResult {
  match_score: number;
  matched_slots: Record<string, number>;
  missing_items: number[];
  extra_items: number[];
  review_required: boolean;
}

export interface SrpRequest {
  id: number;
  corporation_id: number;
  character_id: number;
  character_name: string | null;
  killmail_id: number;
  killmail_hash: string;
  ship_type_id: number | null;
  ship_name: string | null;
  doctrine_id: number | null;
  doctrine_name: string | null;
  payout_amount: number;
  fitting_value: number;
  insurance_payout: number;
  status: 'pending' | 'approved' | 'rejected' | 'paid';
  match_result: SrpMatchResult | null;
  match_score: number;
  submitted_at: string;
  reviewed_by: number | null;
  reviewed_at: string | null;
  review_note: string | null;
  paid_at: string | null;
  compliance_score?: number;
  scoring_method?: 'fuzzy' | 'dogma';
}

export interface SrpSubmitRequest {
  corporation_id: number;
  character_id: number;
  character_name?: string;
  killmail_id: number;
  killmail_hash: string;
  doctrine_id?: number;
}

export interface SrpReviewRequest {
  status: 'approved' | 'rejected';
  reviewed_by: number;
  review_note?: string;
}

export interface SrpConfig {
  corporation_id: number;
  pricing_mode: 'jita_buy' | 'jita_sell' | 'jita_split';
  default_insurance_level: string;
  auto_approve_threshold: number;
  max_payout: number | null;
}


// Doctrine Stats types

export interface DoctrineStats {
  offense: { total_dps: number; weapon_dps: number; drone_dps: number };
  defense: { total_ehp: number; tank_type: string; shield_ehp: number; armor_ehp: number };
  capacitor: { stable: boolean; cap_amount?: number };
  navigation: { max_velocity: number; align_time: number };
  targeting: { max_range: number; scan_resolution: number };
}

export interface DoctrineReadiness {
  doctrine_id: number;
  character_id: number;
  all_v_stats: DoctrineStats;
  character_stats: DoctrineStats;
  dps_ratio: number;
  ehp_ratio: number;
  missing_skills: Array<{ skill_id: number; skill_name: string; required_level: number; trained_level: number }>;
  can_fly: boolean;
}

export interface BomItem {
  type_id: number;
  type_name: string;
  quantity: number;
}

// Helpers

import { formatIsk } from './finance';

export { formatIsk };

export const SRP_STATUS_COLORS: Record<string, string> = {
  pending: '#d29922',
  approved: '#3fb950',
  rejected: '#f85149',
  paid: '#00d4ff',
};

export function getMatchScoreColor(score: number): string {
  if (score >= 0.9) return '#3fb950';
  if (score >= 0.7) return '#d29922';
  return '#f85149';
}


// --- Doctrine Extensions ---

export interface DoctrineCloneRequest {
  new_name: string;
  category?: string;
}

export interface DoctrineChangelogEntry {
  id: number;
  doctrine_id: number;
  actor_character_id: number;
  actor_name: string;
  action: 'created' | 'updated' | 'archived' | 'restored' | 'cloned';
  changes: Record<string, { old?: unknown; new?: unknown }>;
  created_at: string;
}

export interface DoctrineAutoPrice {
  doctrine_id: number;
  total_price: number;
  item_prices: Record<string, {
    name: string;
    quantity: number;
    unit_price: number;
    total: number;
  }>;
  price_source: string;
  priced_at: string;
}

export interface FleetReadiness {
  doctrine_id: number;
  corporation_id: number;
  total_pilots: number;
  can_fly: number;
  partial: number;
  cannot_fly: number;
  readiness_pct: number;
  pilots: FleetReadinessPilot[];
}

export interface FleetReadinessPilot {
  character_id: number;
  character_name: string;
  status: 'can_fly' | 'partial' | 'cannot_fly' | 'unknown';
  dps_ratio: number;
  ehp_ratio: number;
  missing_skills_count: number;
}

export interface SkillPlanExport {
  format: 'evemon' | 'text';
  content: string;
  skill_count: number;
}

export const DOCTRINE_CATEGORIES = [
  'general', 'fleet', 'small_gang', 'home_defense', 'capital', 'training', 'special'
] as const;

export type DoctrineCategory = typeof DOCTRINE_CATEGORIES[number];

export const CATEGORY_LABELS: Record<DoctrineCategory, string> = {
  general: 'General',
  fleet: 'Fleet',
  small_gang: 'Small Gang',
  home_defense: 'Home Defense',
  capital: 'Capital',
  training: 'Training',
  special: 'Special',
};

export const CATEGORY_COLORS: Record<DoctrineCategory, string> = {
  general: '#8b949e',
  fleet: '#58a6ff',
  small_gang: '#f0883e',
  home_defense: '#56d364',
  capital: '#bc8cff',
  training: '#d2a8ff',
  special: '#f85149',
};
