// Power Bloc Intelligence Types

// ==================== Tab Response Types ====================

// HUNTING
export interface PBHotZone {
  system_id: number;
  system_name: string;
  region_name: string;
  kills: number;
  deaths: number;
  total_activity: number;
}

export interface PBStrikeWindow {
  activity_by_hour: Array<{ hour: number; activity: number; our_deaths: number; our_kills: number }>;
  peak_hours: string;
  weak_hours: string;
  peak_start: number;
  peak_end: number;
  weak_start: number;
  weak_end: number;
  last_24h: { kills: number; capital_deployments: number };
}

export interface PBPriorityTarget {
  character_id: number;
  character_name: string;
  whale_score: number;
  deaths: number;
  kills: number;
  efficiency: number;
  isk_per_death: number;
  total_isk_lost: number;
  last_active: string | null;
}

export interface PBCounterDoctrine {
  their_meta: Array<{ ship: string; type_id: number; ship_class: string; pct: number; count: number }>;
  damage_profile: Record<string, number>;
  primary_damage_type: string;
  tank_recommendation: string;
}

export interface PBGatecampAlert {
  system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  kills: number;
  pod_kills: number;
  total_isk: number;
  duration_seconds: number;
  severity: string;
}

export interface PBEnemyDamageProfile {
  alliance_id: number;
  alliance_name?: string;
  ticker?: string;
  kills: number;
  top_ships: Array<{ ship: string; ship_class: string; count: number }>;
}

export interface PBSystemDanger {
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_deaths: number;
  pod_deaths: number;
  isk_lost: number;
  danger_level: string;
}

export interface PBHuntingResponse {
  coalition_name: string;
  member_count: number;
  hot_zones: PBHotZone[];
  strike_window: PBStrikeWindow;
  priority_targets: PBPriorityTarget[];
  counter_doctrine: PBCounterDoctrine;
  gatecamp_alerts: PBGatecampAlert[];
  enemy_damage_profiles: PBEnemyDamageProfile[];
  system_dangers: PBSystemDanger[];
}

// DETAILS
export interface PBDetailsResponse {
  coalition_name: string;
  member_count: number;
  danger_zones: Array<{ system_id: number; system_name: string; region_name: string; deaths: number; isk_lost: number }>;
  top_enemies: Array<{ alliance_id: number; alliance_name: string; ticker: string; kills: number; isk_destroyed: number }>;
  coalition_allies: Array<{ alliance_id: number; alliance_name: string; ticker: string }>;
  ships_killed: Array<{ type_id: number; ship_name: string; ship_class: string; count: number; isk: number }>;
  ships_lost: Array<{ type_id: number; ship_name: string; ship_class: string; count: number; isk: number }>;
  hunting_grounds: Array<{ region_name: string; kills: number; isk: number }>;
  hourly_activity: { hours: Array<{ hour: number; kills: number; deaths: number }>; peak_start: number; safe_start: number };
  economics: { isk_destroyed: number; isk_lost: number; efficiency: number; cost_per_kill: number; cost_per_death: number };
  recommendations: Array<{ priority: number; category: string; text: string }>;
  participation_trends: { daily: Array<{ day: string | null; kills: number; deaths: number; active_pilots: number }>; trend: { kills: string } };
  burnout_index: { daily: Array<{ day: string | null; kills_per_pilot: number; active_pilots: number }>; summary: { avg_kills_per_pilot: number; status: string } };
  attrition: { summary: { first_half_pilots: number; second_half_pilots: number; retained: number; retention_rate: number; status: string } };
  alliance_heatmap: Array<{ alliance_id: number; name: string; ticker: string; hours: number[] }>;
}

// OFFENSIVE
export interface PBOffensiveResponse {
  coalition_name: string;
  member_count: number;
  strike_window: { best_hours: number[]; avoid_hours: number[]; kills_by_hour: number[]; best_label: string; avoid_label: string };
  enemy_weak_hours: { weak_hours: number[]; activity_by_hour: number[]; label: string };
  priority_targets: Array<{ alliance_id: number; alliance_name: string; ticker: string; kills: number; isk: number }>;
  hunting_grounds: Array<{ region_name: string; kills: number; isk: number }>;
  low_adm_targets: Array<{ system_id: number; system_name: string; alliance_id: number; alliance_name: string; adm: number }>;
  active_wars: Array<{ war_id: number; aggressor_id: number; aggressor_name: string; defender_id: number; defender_name: string; is_coalition_aggressor: boolean; started: string | null }>;
  strategies: string[];
}

// DEFENSIVE
export interface PBDefensiveResponse {
  summary: {
    total_deaths: number; isk_lost: number; avg_loss_value: number; max_loss_value: number;
    total_kills: number; efficiency: number; kd_ratio: number; solo_death_pct: number; capital_losses: number;
  };
  threat_profile: {
    solo_ganked: { deaths: number; percentage: number };
    small: { deaths: number; percentage: number };
    medium: { deaths: number; percentage: number };
    large: { deaths: number; percentage: number };
    blob: { deaths: number; percentage: number };
  };
  death_prone_pilots: Array<{
    character_id: number; character_name: string; deaths: number; kills: number;
    death_pct: number; avg_loss_value: number; last_ship_lost: string | null;
  }>;
  ship_losses: Array<{ ship_class: string; count: number; percentage: number }>;
  doctrine_weakness: Array<{ ship_name: string; ship_group: string; count: number; percentage: number }>;
  loss_analysis: {
    total_deaths: number; pvp_deaths: number; pve_deaths: number;
    solo_deaths: number; avg_attacker_count: number; avg_death_value: number; capital_losses: number;
  };
  death_heatmap: Array<{
    system_id: number; system_name: string; region_name: string;
    deaths: number; deaths_per_day: number; is_camp: boolean;
  }>;
  loss_regions: Array<{
    region_id: number; region_name: string; deaths: number; percentage: number; unique_systems: number;
  }>;
  death_timeline: Array<{ day: string; deaths: number; active_pilots: number }>;
  capital_losses: {
    capital_losses: number; capital_loss_pct: number; carrier_losses: number;
    dread_losses: number; fax_losses: number; super_titan_losses: number; avg_capital_loss_value: number;
  } | null;
  top_threats: Array<{
    corporation_id: number; corporation_name: string; kills_by_them: number;
    isk_destroyed_by_them: number; last_kill_time: string | null;
  }>;
  high_value_losses: Array<{
    killmail_id: number; killmail_time: string; isk_value: number;
    victim_character_id: number; victim_name: string; ship_type_id: number; ship_name: string; system_name: string;
  }>;
  safe_danger_hours: {
    safe_start: number; safe_end: number; danger_start: number; danger_end: number; hourly_deaths: number[];
  };
  damage_taken: Array<{ damage_type: string; count: number; percentage: number }>;
  ewar_threats: Array<{ ewar_type: string; count: number; percentage: number }>;
  danger_systems: Array<{
    system_id: number; system_name: string; region_name: string; security: number;
    deaths: number; deaths_per_day: number; kills: number; danger_score: number; is_gatecamp: boolean;
  }>;
}

// CAPITALS
export interface PBCapitalsResponse {
  coalition_name: string;
  member_count: number;
  summary: { total_deployments: number; total_losses: number; total_isk_lost: number; unique_ships: number };
  ships_used: Array<{ type_id: number; ship_name: string; ship_class: string; group_id: number; deployments: number; alliances: Array<{ alliance_id: number; alliance_name: string; count: number }> }>;
  capital_losses: Array<{ type_id: number; ship_name: string; ship_class: string; losses: number; isk_lost: number }>;
  race_distribution: Array<{ race: string; count: number; pct: number }>;
  activity_trend: Array<{ day: string; deployments: number }>;
  top_corps: Array<{ corporation_id: number; corporation_name: string; deployments: number }>;
  regions: Array<{ region_name: string; deployments: number }>;
}

// WORMHOLE
export interface PBWormholeResponse {
  coalition_name: string;
  member_count: number;
  summary: { total_systems: number; total_isk_potential_m: number; class_breakdown: Record<string, number> };
  controlled_systems: Array<{
    system_id: number; system_name: string; wh_class: number | null;
    alliance_id: number; alliance_name: string;
    kills: number; losses: number; last_seen: string | null;
    effect_name: string | null;
    statics: Array<{ type: string; destination_class: string | null; max_mass: number | null; max_jump_mass: number | null; lifetime: number | null }>;
    isk_per_month_m: number;
  }>;
  visitors: Array<{ alliance_id: number; alliance_name: string; system_id: number; kills: number; losses: number; threat_level: string }>;
  sov_threats: Array<{
    alliance_id: number; alliance_name: string;
    total_wh_systems: number; total_kills: number; total_isk_destroyed: number;
    threat_breakdown: { critical: number; high: number; moderate: number; low: number };
    top_attackers: Array<Record<string, unknown>>;
    top_regions: Array<Record<string, unknown>>;
    timezone: { us: number; eu: number; au: number };
    top_wh_systems: Array<Record<string, unknown>>;
    attacker_doctrines: Array<Record<string, unknown>>;
  }>;
}

// CAPSULEERS
export interface PBCapsuleersResponse {
  coalition_name: string;
  member_count: number;
  summary: { active_pilots: number; total_kills: number; total_deaths: number; pod_deaths: number; pod_survival_rate: number; kd_ratio: number };
  alliance_rankings: Array<{ alliance_id: number; alliance_name: string; ticker: string; pilots: number; kills: number; deaths: number; efficiency: number; isk_lost: number }>;
  corp_rankings: Array<{ corporation_id: number; corporation_name: string; pilots: number; kills: number }>;
  top_pilots: Array<{ character_id: number; character_name: string; alliance_id: number; alliance_name: string; kills: number; deaths: number; efficiency: number; pod_deaths: number }>;
}

// ==================== Existing Types ====================

export interface PowerBlocMember {
  alliance_id: number;
  name: string;
  ticker: string;
  kills: number;
  losses: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
  activity: number;
}

export interface PowerBlocShip {
  ship_type_id: number;
  ship_name: string;
  ship_class: string;
  uses: number;
}

export interface PowerBlocEnemy {
  alliance_id: number;
  name: string;
  kills: number;
  isk_destroyed: number;
}

export interface PowerBlocRegion {
  region_name: string;
  kills: number;
  isk_destroyed: number;
}

export interface PowerBlocDailyActivity {
  day: string;
  kills: number;
  deaths: number;
  isk_destroyed: number;
  isk_lost: number;
}

export interface PowerBlocCapital {
  ship_class: string;
  pilots?: number;
  uses?: number;
  losses?: number;
  isk_lost?: number;
}

export interface PowerBlocComplete {
  leader_alliance_id: number;
  coalition_name: string;
  leader_name: string;
  member_count: number;
  total_pilots: number;
  active_pilots: number;
  minutes: number;
  timeframe: string;
  header: {
    kills: number;
    deaths: number;
    efficiency: number;
    isk_efficiency: number;
    kill_efficiency: number;
    net_isk: number;
    isk_destroyed: number;
    isk_lost: number;
    peak_hour: number;
  };
  members: PowerBlocMember[];
  combat: {
    top_ships: PowerBlocShip[];
    top_victims: PowerBlocEnemy[];
    top_enemies: PowerBlocEnemy[];
    active_regions: PowerBlocRegion[];
    daily_activity: PowerBlocDailyActivity[];
  };
  capitals: {
    used: PowerBlocCapital[];
    lost: PowerBlocCapital[];
  };
}
