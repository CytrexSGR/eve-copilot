/** Character info from ESI public endpoint */
export interface CharacterInfo {
  character_id: number;
  name: string;
  corporation_id: number;
  alliance_id: number | null;
  birthday: string;
  security_status: number;
  title: string | null;
  description: string;
}

/** Wallet from /api/character/{id}/wallet */
export interface WalletBalance {
  balance: number;
  formatted: string;
}

/** Single skill entry */
export interface SkillEntry {
  skill_id: number;
  skill_name: string;
  level: number;
  trained_level: number;
  skillpoints: number;
  group_name: string;
}

/** Skills from /api/character/{id}/skills */
export interface SkillData {
  character_id: number;
  total_sp: number;
  unallocated_sp: number;
  skill_count: number;
  skills: SkillEntry[];
}

/** Single skill queue item */
export interface SkillQueueItem {
  skill_id: number;
  skill_name: string;
  skill_description: string;
  finish_date: string | null;
  start_date: string | null;
  finished_level: number;
  queue_position: number;
  level_start_sp: number;
  level_end_sp: number;
  training_start_sp: number;
  sp_remaining: number;
  training_progress: number;
}

/** Skill queue from /api/character/{id}/skillqueue */
export interface SkillQueue {
  character_id: number;
  queue_length: number;
  queue: SkillQueueItem[];
}

/** Location from /api/character/{id}/location */
export interface CharacterLocation {
  character_id: number;
  solar_system_id: number;
  solar_system_name: string;
  station_id: number | null;
  station_name: string | null;
  structure_id: number | null;
}

/** Ship from /api/character/{id}/ship */
export interface CharacterShip {
  character_id: number;
  ship_type_id: number;
  ship_type_name: string;
  ship_item_id: number;
  ship_name: string;
}

/** Industry job */
export interface IndustryJob {
  job_id: number;
  activity_id: number;
  blueprint_id: number;
  blueprint_type_id: number;
  blueprint_type_name: string;
  product_type_id: number | null;
  product_type_name: string;
  status: string;
  runs: number;
  licensed_runs: number;
  start_date: string | null;
  end_date: string | null;
  duration: number;
  station_id: number;
  station_name: string;
  cost: number;
}

/** Industry from /api/character/{id}/industry */
export interface IndustryData {
  character_id: number;
  total_jobs: number;
  active_jobs: number;
  jobs: IndustryJob[];
}

/** Asset location summary */
export interface LocationSummary {
  location_id: number;
  location_name: string;
  location_type: string | null;
  total_value: number;
  total_volume: number;
  item_count: number;
  type_count: number;
}

/** Single asset */
export interface AssetEntry {
  item_id: number;
  type_id: number;
  type_name: string;
  group_id: number;
  group_name: string;
  category_id: number;
  category_name: string;
  location_id: number;
  location_name: string;
  quantity: number;
  is_singleton: boolean;
  location_flag: string | null;
  location_type: string | null;
  unit_price: number;
  total_value: number;
  volume: number;
  total_volume: number;
}

/** Valued assets from /api/character/{id}/assets/valued */
export interface ValuedAssetData {
  character_id: number;
  total_value: number;
  total_volume: number;
  total_items: number;
  total_types: number;
  location_summaries: LocationSummary[];
  assets: AssetEntry[];
}

/** Batch character summary from /api/character/summary/all */
export interface CharacterSummary {
  character_id: number;
  character_name: string;
  info: CharacterInfo | null;
  wallet: WalletBalance | null;
  skills: SkillData | null;
  skillqueue: SkillQueue | null;
  location: CharacterLocation | null;
  ship: CharacterShip | null;
  industry: IndustryData | null;
}

export interface CharacterSummaryResponse {
  characters: CharacterSummary[];
  count: number;
}

/** Activity ID to human label mapping */
export const ACTIVITY_NAMES: Record<number, string> = {
  1: 'Manufacturing',
  3: 'TE Research',
  4: 'ME Research',
  5: 'Copying',
  8: 'Invention',
  9: 'Reactions',
  11: 'Reverse Engineering',
};

/** Activity ID to color mapping */
export const ACTIVITY_COLORS: Record<number, string> = {
  1: '#3fb950',   // Manufacturing — green
  3: '#00d4ff',   // TE Research — cyan
  4: '#00d4ff',   // ME Research — cyan
  5: '#a855f7',   // Copying — purple
  8: '#ffcc00',   // Invention — gold
  9: '#ff8800',   // Reactions — orange
  11: '#f85149',  // Reverse Engineering — red
};
