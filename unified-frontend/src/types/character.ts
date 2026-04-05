export interface Character {
  character_id: number
  character_name: string
  token_valid: boolean
  scopes_count: number
}

export interface CharactersResponse {
  authenticated_characters: number
  characters: Character[]
}

export interface WalletResponse {
  character_id: number
  balance: number
}

export interface SkillsResponse {
  character_id: number
  total_sp: number
  unallocated_sp: number
  skills: Skill[]
}

export interface Skill {
  skill_id: number
  skill_name: string
  trained_skill_level: number
  skillpoints_in_skill: number
}

export interface SkillUnlock {
  type_id: number
  type_name: string
  group_name: string
  category_name: string
  required_level: number
}

export interface SkillQueueItem {
  skill_id: number
  skill_name: string
  skill_description: string
  finished_level: number
  queue_position: number
  start_date: string
  finish_date: string
  level_start_sp: number
  level_end_sp: number
  training_start_sp: number
  sp_remaining: number
  training_progress: number
  unlocks_at_level: SkillUnlock[]
}

export interface SkillQueueResponse {
  character_id: number
  queue: SkillQueueItem[]
}

export interface CharacterInfo {
  character_id: number
  name: string
  corporation_id: number
  alliance_id?: number
  security_status: number
  birthday: string
}

export interface PortraitResponse {
  character_id: number
  portrait_url_64: string
  portrait_url_128: string
  portrait_url_256: string
  portrait_url_512: string
}

export interface LocationResponse {
  character_id: number
  solar_system_id: number
  solar_system_name: string
  station_id?: number
  station_name?: string
  structure_id?: number
}

export interface ShipResponse {
  character_id: number
  ship_type_id: number
  ship_type_name: string
  ship_item_id: number
  ship_name: string
}

export interface IndustryJob {
  job_id: number
  activity_id: number
  blueprint_id: number
  blueprint_type_id: number
  blueprint_type_name?: string
  product_type_id?: number
  product_type_name?: string
  status: string
  runs: number
  licensed_runs?: number
  start_date?: string
  end_date?: string
  duration: number
  station_id?: number
  station_name?: string
  cost?: number
  installer_id?: number
}

export interface IndustryResponse {
  character_id: number
  total_jobs: number
  active_jobs: number
  jobs: IndustryJob[]
}

export interface CharacterLocation {
  solar_system_id: number
  solar_system_name?: string
  station_id?: number
  station_name?: string
  structure_id?: number
}

export interface CharacterShip {
  ship_type_id: number
  ship_name: string
  ship_item_id: number
}

// Asset types
export interface Asset {
  item_id: number
  type_id: number
  type_name: string
  group_id: number
  group_name: string
  category_id: number
  category_name: string
  location_id: number
  location_name: string
  quantity: number
  is_singleton: boolean
  location_flag: string | null
  location_type: string | null
}

export interface AssetListResponse {
  character_id: number
  total_items: number
  assets: Asset[]
}

// Grouped assets by location (frontend-only type for UI grouping)
export interface AssetLocation {
  location_id: number
  location_name: string
  location_type: string
  assets: Asset[]
  total_items: number
}

// Valued asset types (with market prices)
export interface ValuedAsset {
  item_id: number
  type_id: number
  type_name: string
  group_id: number
  group_name: string
  category_id: number
  category_name: string
  location_id: number
  location_name: string
  quantity: number
  is_singleton: boolean
  location_flag: string | null
  location_type: string | null
  // Valuation fields
  unit_price: number
  total_value: number
  volume: number
  total_volume: number
}

export interface LocationSummary {
  location_id: number
  location_name: string
  location_type: string | null
  total_value: number
  total_volume: number
  item_count: number
  type_count: number
}

export interface ValuedAssetListResponse {
  character_id: number
  total_value: number
  total_volume: number
  total_items: number
  total_types: number
  location_summaries: LocationSummary[]
  assets: ValuedAsset[]
}

// Corporation info
export interface CorporationInfo {
  corporation_id: number
  name: string
  ticker: string
  member_count?: number
  alliance_id?: number
}

// Aggregated character data for dashboard
export interface CharacterSummary {
  character_id: number
  character_name: string
  portrait_url: string
  wallet_balance: number
  total_sp: number
  unallocated_sp: number
  current_skill?: SkillQueueItem
  skills_in_queue: number
  location?: CharacterLocation
  ship?: CharacterShip
  active_industry_jobs?: number
  corporation_id?: number
  corporation_name?: string
  corporation_ticker?: string
  alliance_id?: number
  alliance_name?: string
}
