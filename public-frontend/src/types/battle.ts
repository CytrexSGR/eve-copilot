// Battle-related types for EVE Intel Public Frontend

// ==================== Core Battle Types ====================

export interface ActiveBattle {
  battle_id: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_kills: number;
  total_isk_destroyed: number;
  last_milestone: number;
  started_at: string;
  last_kill_at: string;
  duration_minutes: number;
  telegram_sent: boolean;
  intensity: 'extreme' | 'high' | 'moderate' | 'low';
  status_level?: 'gank' | 'brawl' | 'battle' | 'hellcamp';
  top_ships?: Array<{ ship_name: string; count: number }>;
}

export interface HotZone {
  system_id: number;
  system_name: string;
  region_name: string;
  constellation_name: string;
  security_status: number;
  kills: number;
  total_isk_destroyed: number;
  dominant_ship_type: string;
  flags: string[];
}

export interface DangerZone {
  system_name: string;
  region_name: string;
  security_status: number;
  industrials_killed: number;
  freighters_killed: number;
  total_value: number;
  warning_level: 'EXTREME' | 'HIGH' | 'MODERATE';
}

// ==================== Capital Kill Types ====================

export interface CapitalKill {
  killmail_id: number;
  ship_name: string;
  victim: number;
  isk_destroyed: number;
  system_name: string;
  region_name: string;
  security_status: number;
  time_utc: string;
}

export interface CapitalCategory {
  count: number;
  total_isk: number;
  kills: CapitalKill[];
}

export interface CapitalKills {
  titans: CapitalCategory;
  supercarriers: CapitalCategory;
  carriers: CapitalCategory;
  dreadnoughts: CapitalCategory;
  force_auxiliaries: CapitalCategory;
}

// ==================== High-Value Kill Types ====================

export interface HighValueKill {
  rank: number;
  killmail_id: number;
  isk_destroyed: number;
  ship_type: string;
  ship_type_id: number;
  ship_name: string;
  victim: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  is_gank: boolean;
  time_utc: string;
}

// ==================== Ship Types ====================

export interface ShipCategory {
  count: number;
  total_isk: number;
}

export interface ShipClasses {
  capital: number;
  battleship: number;
  cruiser: number;
  frigate: number;
  destroyer: number;
  industrial: number;
  other: number;
}

export interface BiggestLoss {
  ship_type_id: number | null;
  value: number;
}

// ==================== Timeline Types ====================

export interface TimelineHour {
  hour_utc: number;
  kills: number;
  isk_destroyed: number;
}

export interface TimelineBucket {
  minute: number;
  bucket_index: number;
  kills: number;
  isk_destroyed: number;
  capital_kills: number;
  ship_categories: string[];
  max_kill_value: number;
  has_capital: boolean;
}

export interface TacticalShift {
  minute: number;
  type: 'capital_entry' | 'kill_spike' | 'kill_drop' | 'high_value_kill' | 'logi_collapse';
  description: string;
  severity: 'low' | 'medium' | 'high';
}

export interface BattleTimelineResponse {
  battle_id: number;
  system_id: number;
  started_at: string;
  ended_at: string;
  buckets: TimelineBucket[];
  tactical_shifts: TacticalShift[];
  total_minutes: number;
  total_kills: number;
  bucket_size_seconds: number;
}

// ==================== Battle Report Types ====================

export interface BattleReport {
  period: string;
  global: {
    total_kills: number;
    total_isk_destroyed: number;
    peak_hour_utc: number;
    peak_kills_per_hour: number;
  };
  hot_zones: HotZone[];
  capital_kills: CapitalKills;
  high_value_kills: HighValueKill[];
  danger_zones: DangerZone[];
  ship_breakdown: Record<string, ShipCategory>;
  timeline: TimelineHour[];
  regions: unknown[];  // Kept for backwards compatibility
}

// ==================== Reshipment Tracking Types ====================

export interface Resshipper {
  character_id: number;
  character_name: string;
  alliance_id: number | null;
  alliance_name: string | null;
  deaths: number;
  ships_lost: string[];
  total_isk_lost: number;
}

export interface CorpReshipStats {
  corp_id: number;
  corp_name: string;
  reshippers: number;
  total_deaths: number;
  reship_ratio: number;
}

export interface AllianceReshipStats {
  alliance_id: number;
  alliance_name: string;
  total_reshippers: number;
  total_deaths: number;
  avg_deaths_per_resshipper: number;
  max_deaths: number;
  reship_ratio: number;
  corps: CorpReshipStats[];
}

export interface ReshipmentSummary {
  total_reshippers: number;
  total_one_death_pilots: number;
  overall_reship_ratio: number;
  avg_deaths_per_resshipper: number;
  max_deaths: number;
}

export interface BattleReshipmentResponse {
  reshippers: Resshipper[];
  by_alliance: AllianceReshipStats[];
  summary: ReshipmentSummary;
}

// ==================== Coalition Conflicts Types ====================

export interface ConflictCoalition {
  leader_id: number;
  leader_name: string;
  leader_ticker: string;
  member_count: number;
  kills: number;
  losses: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
}

export interface ConflictBattle {
  battle_id: number;
  system_name: string;
  region_name: string;
  status_level: 'gank' | 'brawl' | 'battle' | 'hellcamp';
  total_kills: number;
  total_isk: number;
  last_kill_at: string;
  minutes_ago: number;
}

export interface ConflictHighValueKill {
  killmail_id: number;
  ship_name: string;
  ship_type_id: number;
  value: number;
  victim_alliance_ticker: string;
  attacker_alliance_ticker: string;
}

export interface Conflict {
  conflict_id: string;
  coalition_a: ConflictCoalition;
  coalition_b: ConflictCoalition;
  regions: string[];
  total_kills: number;
  total_isk: number;
  capital_kills: number;
  last_kill_at: string | null;
  started_at: string | null;
  time_status: '10m' | '1h' | '12h' | '24h' | '7d';
  trend: 'escalating' | 'stable' | 'cooling';
  battles: ConflictBattle[];
  high_value_kills: ConflictHighValueKill[];
}

export interface ConflictsResponse {
  filter_minutes: number;
  conflicts: Conflict[];
  total_battles: number;
  total_kills: number;
}

// ==================== Timezone Heatmap Types ====================

export interface HourlyActivity {
  hour_utc: number;
  kills: number;
  isk_destroyed: number;
}

export interface HeatmapSummary {
  total_kills: number;
  total_isk_destroyed: number;
  peak_hour_utc: number | null;
  peak_kills: number;
  days_analyzed: number;
}

export interface TimezoneHeatmapResponse {
  hours: HourlyActivity[];
  peak_hours: number[];
  defensive_gaps: number[][];
  summary: HeatmapSummary;
}
