/**
 * Corporation Detail Types
 *
 * Type definitions for Corporation Intelligence endpoints.
 */

// ============================================================================
// Basic Info (Header)
// ============================================================================

export interface CorporationBasicInfo {
  /** Corporation ID from EVE Online */
  corporation_id: number;
  /** Corporation name */
  corporation_name: string;
  /** Corporation ticker/abbreviation (e.g., "CORP") */
  ticker: string | null;
  /** Alliance ID if corporation is in an alliance */
  alliance_id: number | null;
  /** Alliance name if corporation is in an alliance */
  alliance_name: string | null;
  /** Total kills in the period */
  kills: number;
  /** Total deaths in the period */
  deaths: number;
  /** Kill balance (kills - deaths) */
  kill_balance: number;
  /** Total ISK value destroyed by corporation */
  isk_destroyed: number;
  /** Total ISK value lost by corporation */
  isk_lost: number;
  /** Net ISK balance (isk_destroyed - isk_lost) */
  net_isk: number;
  /** ISK efficiency percentage (0-100) */
  isk_efficiency: number;
  /** Kill efficiency percentage (0-100) */
  kill_efficiency: number;
  /** Peak activity hour in UTC (0-23) */
  peak_hour: number;
  /** Activity trend percentage compared to previous period */
  trend_pct: number;
}

// ============================================================================
// Complete Overview (Details Tab)
// ============================================================================

export interface CorporationComplete {
  corporation_id: number;
  corporation_name: string;
  ticker: string | null;
  alliance_id: number | null;
  alliance_name: string | null;
  ceo_id: number | null;
  ceo_name: string | null;
  member_count: number | null;
  date_founded: string | null;
  kills: number;
  deaths: number;
  efficiency: string;
  isk_killed: string;
  isk_lost: string;
  ship_classes: ShipClassDist[];
  regions: RegionDist[];
}

export interface ShipClassDist {
  /** Ship class name (e.g., "Frigate", "Cruiser", "Battleship") */
  ship_class: string;
  /** Number of ships of this class */
  count: number;
  /** Percentage of total (0-100) */
  percentage: number;
}

export interface RegionDist {
  region_id: number;
  region_name: string;
  activity: number;
  percentage: number;
}

// ============================================================================
// Hunting Tab
// ============================================================================

export interface HuntingOverview {
  kills: number;
  deaths: number;
  active_days: number;
  unique_pilots: number;
  unique_systems: number;
  efficiency: number;
  avg_kill_value: number;
  peak_activity_hour: number | null;
  primary_region: string | null;
  primary_system: string | null;
  threat_level: 'low' | 'medium' | 'high';
  threat_score: number;
}

export interface TopPilot {
  character_id: number;
  character_name: string | null;
  kills: number;
  isk_destroyed: string;
  has_capital_kills: boolean;
}

export interface Doctrine {
  ship_name: string;
  ship_group: string;
  count: number;
  percentage: number;
}

export interface HotZone {
  system_id: number;
  system_name: string;
  region_id: number;
  region_name: string;
  activity: number;
  kills: number;
  deaths: number;
  efficiency: number;
  is_gatecamp: boolean;
}

export interface TimezoneActivity {
  hour: number;
  activity: number;
  kills: number;
  deaths: number;
}

// ============================================================================
// Offensive Tab
// ============================================================================

export interface OffensiveStats {
  summary: OffensiveSummary;
  engagement_profile: EngagementProfile;
  solo_killers: SoloKiller[];
  doctrine_profile: DoctrineShip[];
  ship_losses_inflicted: ShipClassDist[];
  victim_analysis: VictimAnalysis;
  kill_heatmap: KillHeatmapSystem[];
  hunting_regions: RegionActivity[];
  kill_timeline: TimelineDay[];
  capital_threat: CapitalThreat | null;
  top_victims: TopVictim[];
  high_value_kills: HighValueKill[];
  // NEW Phase 2 Features
  hunting_hours: HuntingHours;
  damage_dealt: DamageProfile[];
  ewar_usage: EWarStat[];
  hot_systems: HotSystem[];
  effective_doctrines: EffectiveDoctrine[];
  kill_velocity: KillVelocity[];
}

export interface OffensiveSummary {
  /** Total kills by corporation in the period */
  total_kills: number;
  /** Total ISK value destroyed (formatted string, e.g., "123.4B ISK") */
  isk_destroyed: string;
  /** Average ISK value per kill (formatted string) */
  avg_kill_value: string;
  /** Highest single kill ISK value (raw number) */
  max_kill_value: number;
  /** Kill/Death ratio */
  kd_ratio: number;
  /** Percentage of kills that were solo (0-100) */
  solo_kill_pct: number;
  /** Number of capital ships killed */
  capital_kills: number;
  /** Offensive efficiency percentage (0-100) */
  efficiency: number;
}

export interface EngagementProfile {
  /** Solo kills (≤3 attackers) with count and percentage */
  solo: { kills: number; percentage: number };
  /** Small gang kills (4-10 attackers) with count and percentage */
  small: { kills: number; percentage: number };
  /** Medium fleet kills (11-30 attackers) with count and percentage */
  medium: { kills: number; percentage: number };
  /** Large fleet kills (31-100 attackers) with count and percentage */
  large: { kills: number; percentage: number };
  /** Blob kills (>100 attackers) with count and percentage */
  blob: { kills: number; percentage: number };
}

export interface SoloKiller {
  /** Character ID */
  character_id: number;
  /** Character name */
  character_name: string | null;
  /** Number of solo kills (≤3 attackers on killmail) */
  solo_kills: number;
  /** Average ISK value per solo kill */
  avg_solo_kill_value: number;
  /** Most-used ship for solo kills */
  primary_ship: string | null;
}

export interface DoctrineShip {
  /** Ship type name (e.g., "Muninn", "Cerberus") */
  ship_name: string;
  /** Ship class (e.g., "Heavy Assault Cruiser", "Battleship") */
  ship_class: string;
  /** Number of times this ship was used */
  count: number;
  /** Percentage of total ship usage (0-100) */
  percentage: number;
}

export interface VictimAnalysis {
  /** Total kills by corporation */
  total_kills: number;
  /** Number of PvP kills (combat ship on attacker side) */
  pvp_kills: number;
  /** Number of PvE kills (no combat ships on attacker side) */
  pve_kills: number;
  /** Number of gank kills (solo or small gang) */
  gank_kills: number;
  /** Average ISK value per victim */
  avg_victim_value: number;
  /** Number of capital ships killed */
  capital_kills: number;
}

export interface KillHeatmapSystem {
  /** Solar system ID */
  system_id: number;
  /** Solar system name */
  system_name: string;
  /** Region name */
  region_name: string;
  /** Total kills in this system */
  kills: number;
  /** Average kills per day in this system */
  kills_per_day: number;
  /** Whether this system shows gatecamp activity (>60% solo kills) */
  is_gatecamp: boolean;
}

export interface RegionActivity {
  /** EVE Online region ID */
  region_id: number;
  /** Region name */
  region_name: string;
  /** Number of kills in this region (optional, used in offensive context) */
  kills?: number;
  /** Number of deaths in this region (optional, used in defensive context) */
  deaths?: number;
  /** Percentage of total activity in this region (0-100) */
  percentage: number;
  /** Number of unique systems with activity in this region */
  unique_systems: number;
}

export interface TimelineDay {
  /** Date in YYYY-MM-DD format */
  day: string;
  /** Number of kills on this day (optional, used in offensive context) */
  kills?: number;
  /** Number of deaths on this day (optional, used in defensive context) */
  deaths?: number;
  /** Number of active pilots on this day (optional, available in some timelines) */
  active_pilots?: number;
}

export interface TimelineResponse {
  corporation_id: number;
  period_days: number;
  timeline: TimelineDay[];
  summary: {
    total_kills: number;
    total_deaths: number;
    efficiency: number;
    avg_daily_kills: number;
    avg_daily_deaths: number;
  };
}

export interface CapitalThreat {
  /** Total number of capital ships killed */
  capital_kills: number;
  /** Percentage of total kills that were capitals (0-100) */
  capital_kill_pct: number;
  /** Number of Carriers killed */
  carrier_kills: number;
  /** Number of Dreadnoughts killed */
  dread_kills: number;
  /** Number of Supercarriers and Titans killed */
  super_titan_kills: number;
  /** Average ISK value per capital kill */
  avg_capital_kill_value: number;
}

export interface TopVictim {
  /** Victim corporation ID */
  corporation_id: number;
  /** Victim corporation name */
  corporation_name: string | null;
  /** Number of their ships we killed */
  kills_on_them: number;
  /** Total ISK value destroyed (formatted string) */
  isk_destroyed: string;
}

export interface HighValueKill {
  /** zkillboard killmail ID */
  killmail_id: number;
  /** Killmail timestamp in ISO format */
  killmail_time: string;
  /** Total ISK value of the kill */
  isk_value: number;
  /** Victim's character ID */
  victim_character_id: number | null;
  /** Victim's character name */
  victim_name: string | null;
  /** Ship type ID from EVE SDE */
  ship_type_id: number;
  /** Ship type name */
  ship_name: string | null;
  /** Solar system name where kill occurred */
  system_name: string | null;
}

// NEW: Offensive Intelligence Features (Phase 2)

export interface HuntingHours {
  peak_start: number;      // 0-23 UTC hour
  peak_end: number;        // 0-23 UTC hour
  safe_start: number;      // 0-23 UTC hour
  safe_end: number;        // 0-23 UTC hour
  hourly_activity: number[]; // 24-element array of kill counts
}

export interface DamageProfile {
  /** Damage type (EM, Thermal, Kinetic, Explosive, Mixed) */
  damage_type: string;
  /** Number of kills using this damage type */
  count: number;
  /** Percentage of total kills (0-100) */
  percentage: number;
}

export interface EWarStat {
  /** EWAR type (Bubble, Neut, ECM, Damp, Web, Scram, Disruptor, Other) */
  ewar_type: string;
  /** Number of kills where this EWAR was used */
  count: number;
  /** Percentage of total kills with EWAR (0-100) */
  percentage: number;
}

export interface HotSystem {
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  kills: number;
  deaths: number;
  kill_score: number;      // 0-100 percentage
  is_gatecamp: boolean;    // >60% solo kills
  avg_kill_value: number;
}

export interface EffectiveDoctrine {
  ship_class: string;
  kills: number;
  deaths: number;
  kd_ratio: number;        // K/D ≥2.0
  isk_efficiency: number;  // ISK percentage
}

export interface KillVelocity {
  ship_class: string;
  recent_kills: number;
  previous_kills: number;
  recent_isk: number;
  previous_isk: number;
  velocity_pct: number;
  status: 'ESCALATING' | 'STEADY' | 'DECLINING';
}

// ============================================================================
// Defensive Tab
// ============================================================================

export interface DefensiveStats {
  summary: DefensiveSummary;
  threat_profile: ThreatProfile;
  death_prone_pilots: DeathPronePilot[];
  ship_losses: ShipClassDist[];
  doctrine_weakness: DoctrineShip[];
  loss_analysis: LossAnalysis;
  death_heatmap: DeathZone[];
  loss_regions: RegionActivity[];
  death_timeline: TimelineDay[];
  capital_losses: CapitalLosses | null;
  top_threats: TopThreat[];
  high_value_losses: HighValueLoss[];
  // NEW Phase 3 Features
  safe_danger_hours: SafeDangerHours;
  damage_taken: DamageProfile[];
  ewar_threats: EWarStat[];
  danger_systems: DangerSystem[];
}

export interface DefensiveSummary {
  /** Total deaths in the period */
  total_deaths: number;
  /** Total ISK value lost (formatted string, e.g., "123.4B ISK") */
  isk_lost: string;
  /** Average ISK value per loss (formatted string) */
  avg_loss_value: string;
  /** Highest single loss ISK value (raw number) */
  max_loss_value: number;
  /** Total kills in the period (for K/D calculation) */
  total_kills: number;
  /** Defensive efficiency percentage (0-100) */
  efficiency: number;
  /** Kill/Death ratio from defensive perspective */
  kd_ratio: number;
  /** Percentage of deaths that were solo ganks (0-100) - vulnerability indicator */
  solo_death_pct: number;
  /** Number of capital ships lost */
  capital_losses: number;
}

export interface ThreatProfile {
  /** Solo gank deaths (≤3 attackers) - vulnerability indicator */
  solo_ganked: { deaths: number; percentage: number };
  /** Small gang deaths (4-10 attackers) */
  small: { deaths: number; percentage: number };
  /** Medium fleet deaths (11-30 attackers) */
  medium: { deaths: number; percentage: number };
  /** Large fleet deaths (31-100 attackers) */
  large: { deaths: number; percentage: number };
  /** Blob deaths (>100 attackers) */
  blob: { deaths: number; percentage: number };
}

export interface DeathPronePilot {
  /** Character ID */
  character_id: number;
  /** Character name */
  character_name: string | null;
  /** Total deaths by this pilot */
  deaths: number;
  /** Total kills by this pilot */
  kills: number;
  /** Death rate percentage - deaths/(kills+deaths) * 100 */
  death_pct: number;
  /** Average ISK value lost per death */
  avg_loss_value: number;
  /** Last ship type lost by this pilot */
  last_ship_lost: string | null;
}

export interface LossAnalysis {
  /** Total deaths in period */
  total_deaths: number;
  /** Deaths in PvP situations (combat ships on killmail) */
  pvp_deaths: number;
  /** Deaths in PvE situations (no combat ships on killmail) */
  pve_deaths: number;
  /** Deaths while solo (≤3 attackers on killmail) */
  solo_deaths: number;
  /** Average number of attackers per death */
  avg_attacker_count: number;
  /** Average ISK value lost per death */
  avg_death_value: number;
  /** Number of capital ships lost */
  capital_losses: number;
}

export interface DeathZone {
  /** Solar system ID */
  system_id: number;
  /** Solar system name */
  system_name: string;
  /** Region name */
  region_name: string;
  /** Total deaths in this system */
  deaths: number;
  /** Average deaths per day in this system */
  deaths_per_day: number;
  /** Whether this system is a gatecamp (>60% solo deaths) */
  is_camp: boolean;
}

export interface CapitalLosses {
  /** Total number of capital ships lost */
  capital_losses: number;
  /** Percentage of total deaths that were capitals (0-100) */
  capital_loss_pct: number;
  /** Number of Carriers lost */
  carrier_losses: number;
  /** Number of Dreadnoughts lost */
  dread_losses: number;
  /** Number of Force Auxiliaries lost */
  fax_losses: number;
  /** Number of Supercarriers and Titans lost */
  super_titan_losses: number;
  /** Average ISK value per capital loss */
  avg_capital_loss_value: number;
}

export interface TopThreat {
  /** Enemy corporation ID */
  corporation_id: number;
  /** Enemy corporation name */
  corporation_name: string | null;
  /** Number of our ships killed by this enemy corporation */
  kills_by_them: number;
  /** Total ISK value destroyed by this enemy (formatted string) */
  isk_destroyed_by_them: string;
  /** Timestamp of their last kill against us (ISO format) */
  last_kill_time: string | null;
}

export interface HighValueLoss {
  /** zkillboard killmail ID */
  killmail_id: number;
  /** Killmail timestamp in ISO format */
  killmail_time: string;
  /** Total ISK value of the loss */
  isk_value: number;
  /** Our pilot's character ID */
  victim_character_id: number | null;
  /** Our pilot's character name */
  victim_name: string | null;
  /** Ship type ID from EVE SDE */
  ship_type_id: number;
  /** Ship type name */
  ship_name: string | null;
  /** Solar system name where loss occurred */
  system_name: string | null;
}

// NEW: Defensive Intelligence Features (Phase 3)

export interface SafeDangerHours {
  safe_start: number;       // 0-23 UTC hour
  safe_end: number;         // 0-23 UTC hour
  danger_start: number;     // 0-23 UTC hour
  danger_end: number;       // 0-23 UTC hour
  hourly_deaths: number[];  // 24-element array of death counts
}

export interface DangerSystem {
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  deaths: number;
  deaths_per_day: number;
  kills: number;
  danger_score: number;     // 0-100 percentage
  is_gatecamp: boolean;     // >60% solo deaths
}

// ============================================================================
// Pilots Tab
// ============================================================================

export interface PilotRanking {
  character_id: number;
  character_name: string | null;
  kills: number;
  deaths: number;
  isk_killed: string;
  isk_lost: string;
  efficiency: number;
}

export interface ActivePilotsTimelinePoint {
  day: string;
  active_pilots: number;
  new_pilots?: number;
  cumulative?: number;
}

export interface MemberCountPoint {
  date: string;
  member_count: number;
  alliance_id?: number;
}

export interface PilotIntel {
  fleet_overview: FleetOverview;
  pilots: PilotDetail[];
  timeline: Record<number, TimelinePoint[]>;
  active_pilots_timeline?: ActivePilotsTimelinePoint[];
  member_count_history?: MemberCountPoint[];
}

export interface FleetOverview {
  /** Total number of pilots in corporation */
  total_pilots: number;
  /** Number of pilots active in last 7 days */
  active_7d: number;
  /** Average engagements (kills+deaths) per pilot over the period */
  avg_activity: number;
  /** Average daily unique active pilots */
  avg_daily_active: number;
  /** Average morale score (0-100) across all pilots */
  avg_morale: number;
  /** Average fleet participation percentage */
  avg_participation: number;
  /** Number of elite pilots (high morale + high efficiency) */
  elite_count: number;
  /** Member count change over the period (newest - oldest snapshot) */
  member_count_change?: number;
  /** Member count change percentage */
  member_count_change_pct?: number;
}

export interface PilotDetail {
  /** Character ID */
  character_id: number;
  /** Character name */
  character_name: string | null;
  /** Total kills by this pilot */
  kills: number;
  /** Total deaths by this pilot */
  deaths: number;
  /** Total ISK value destroyed by this pilot */
  isk_killed: number;
  /** Total ISK value lost by this pilot */
  isk_lost: number;
  /** Number of days with activity in the period */
  active_days: number;
  /** Timestamp of last activity (ISO format) */
  last_active: string | null;
  /** ISK efficiency percentage (0-100) */
  efficiency: number;
  /** Kill/Death ratio */
  kd_ratio: number;
  /** Number of solo kills (≤3 attackers on killmail) */
  solo_kills: number;
  /** Number of fleet kills (>3 attackers on killmail) */
  fleet_kills: number;
  /** Fleet participation percentage (0-100) */
  fleet_participation_pct: number;
  /** Average fleet size when this pilot participates */
  avg_fleet_size: number;
  /** Whether this pilot has used capital ships */
  capital_usage: boolean;
  /** Number of solo deaths (≤3 attackers on killmail) */
  solo_deaths: number;
  /** Average ISK value per loss */
  avg_loss_value: number;
  /** Number of expensive losses (>threshold) */
  expensive_losses: number;
  /** Primary ship class used by this pilot */
  primary_ship_class: string;
  /** Number of different ship types used (diversity indicator) */
  ship_diversity: number;
  /** Primary region where this pilot operates */
  primary_region: string;
  /** Number of different systems visited (roaming indicator) */
  system_diversity: number;
  /** Activity level in last 7 days */
  activity_7d: number;
  /** Activity level in previous 7 days (for trend calculation) */
  activity_prev_7d: number;
  /** Morale score (0-100) based on activity, efficiency, and trend */
  morale_score: number;
}

export interface TimelinePoint {
  day: string;
  kills: number;
}

// ============================================================================
// Capitals Tab
// ============================================================================

export interface CapitalIntel {
  summary: CapitalSummary;
  fleet_composition: FleetComposition[];
  ship_details: ShipDetail[];
  capital_timeline: CapitalTimelineDay[];
  geographic_hotspots: GeographicHotspot[];
  top_killers: TopKiller[];
  top_losers: TopLoser[];
  capital_engagements: CapitalEngagement[];
  recent_activity: CapitalActivity[];
}

export interface CapitalSummary {
  /** Number of enemy capital ships destroyed */
  capital_kills: number;
  /** Number of own capital ships lost */
  capital_losses: number;
  /** Total ISK value of capitals destroyed (formatted string) */
  isk_destroyed: string;
  /** Total ISK value of capitals lost (formatted string) */
  isk_lost: string;
  /** Number of unique pilots who used capital ships */
  unique_pilots: number;
  /** Capital K/D ratio */
  kd_ratio: number;
  /** Capital efficiency percentage (0-100) */
  efficiency: number;
}

export interface FleetComposition {
  /** Capital type (Carrier, Dreadnought, Force Auxiliary, Supercarrier, Titan) */
  capital_type: string;
  /** Total capital activity (kills + losses) */
  total_activity: number;
  /** Number of enemy capitals of this type killed */
  kills: number;
  /** Number of own capitals of this type lost */
  losses: number;
  /** Percentage of total capital kills (0-100) */
  kills_pct: number;
  /** Percentage of total capital losses (0-100) */
  losses_pct: number;
  /** @deprecated Use kills_pct/losses_pct instead. Kept for backwards compatibility */
  percentage?: number;
}

export interface ShipDetail {
  /** Ship type name (e.g., "Archon", "Revelation") */
  ship_name: string;
  /** Capital type (Carrier, Dreadnought, Force Auxiliary, etc.) */
  capital_type: string;
  /** Total capital activity (kills + losses) */
  total_activity: number;
  /** Number of this ship type killed */
  kills: number;
  /** Number of this ship type lost */
  losses: number;
  /** Average ISK value for this ship type */
  avg_value: number;
}

export interface CapitalTimelineDay {
  day: string;
  kills: number;
  losses: number;
}

export interface GeographicHotspot {
  /** Solar system ID */
  system_id: number;
  /** Solar system name */
  system_name: string;
  /** Region name */
  region_name: string;
  /** Total capital activity in this system (kills + losses) */
  activity: number;
  /** Capital kills in this system */
  kills: number;
  /** Capital losses in this system */
  losses: number;
}

export interface TopKiller {
  /** Character ID */
  character_id: number;
  /** Character name */
  character_name: string | null;
  /** Number of capital ships killed by this pilot */
  capital_kills: number;
  /** Total ISK value of capitals destroyed (formatted string) */
  isk_destroyed: string;
  /** Most-used capital ship by this pilot */
  primary_ship: string | null;
}

export interface TopLoser {
  /** Character ID */
  character_id: number;
  /** Character name */
  character_name: string | null;
  /** Number of capital ships lost by this pilot */
  capital_losses: number;
  /** Total ISK value of capitals lost (formatted string) */
  isk_lost: string;
  /** Last capital ship type lost by this pilot */
  last_ship_lost: string | null;
}

export interface CapitalEngagement {
  engagement_size: string;
  total: number;
  kills: number;
  losses: number;
}

export interface CapitalActivity {
  /** zkillboard killmail ID */
  killmail_id: number;
  /** Killmail timestamp in ISO format */
  killmail_time: string;
  /** ISK value of the capital ship */
  isk_value: number;
  /** Whether this was a kill or a loss */
  activity_type: 'kill' | 'loss';
  /** Ship type name */
  ship_name: string;
  /** Capital type (Carrier, Dreadnought, etc.) */
  capital_type: string;
  /** Solar system name where activity occurred */
  system_name: string | null;
  /** Pilot name (our pilot if loss, enemy pilot if kill) */
  pilot_name: string | null;
  /** Character ID for pilot portrait */
  character_id: number | null;
}

// ============================================================================
// Geography Tab
// ============================================================================

export interface Geography {
  regions: GeographyRegion[];
  top_systems: GeographySystem[];
  home_systems: HomeSystem[];
  total_regions: number;
}

export interface GeographyRegion {
  region_id: number;
  region_name: string;
  activity: number;
  kills: number;
  deaths: number;
  efficiency: number;
}

export interface GeographySystem {
  system_id: number;
  system_name: string;
  region_name: string;
  activity: number;
  kills: number;
  deaths: number;
}

export interface HomeSystem {
  system_id: number;
  system_name: string;
  region_name: string;
  kills: number;
  deaths: number;
  activity: number;
  owned_by_alliance: boolean;
}

// ============================================================================
// Activity Tab
// ============================================================================

export interface ActivityTimelineDay {
  day: string;
  kills: number;
  deaths: number;
  total_activity: number;
  efficiency: number;
}

export interface ActivityTimeline {
  days: ActivityTimelineDay[];
  trend: 'increasing' | 'decreasing' | 'stable';
  avg_daily_activity: number;
}

// ============================================================================
// Overview Tab - Summary Extracts
// ============================================================================

export interface OffensiveOverview {
  /** Offensive efficiency percentage (0-100) */
  efficiency: number;
  /** Activity trend direction */
  trend: 'increasing' | 'decreasing' | 'stable';
  /** Total ISK value destroyed (raw number from API) */
  isk_destroyed: number;
  /** ISK trend indicator (e.g., "↗ +15%" or "↘ -20%" or "→ stable") */
  isk_trend: string;
  /** Top enemy corporation target */
  top_target: {
    /** Enemy corporation name */
    name: string;
    /** Number of kills against this enemy */
    kills: number;
  };
  /** Primary doctrine ship name */
  primary_doctrine: string;
  /** Kill/death timeline for sparkline visualization */
  timeline: {
    /** Date in YYYY-MM-DD format */
    day: string;
    /** Kills on this day */
    kills: number;
    /** Deaths on this day */
    deaths: number;
  }[];
}

export interface DefensiveOverview {
  /** Kill/Death ratio from defensive perspective */
  kd_ratio: number;
  /** Defensive efficiency percentage (0-100) */
  efficiency: number;
  /** Total deaths in period */
  deaths: number;
  /** Total ISK value lost (raw number from API) */
  isk_lost: number;
  /** ISK loss trend indicator */
  isk_trend: string;
  /** Death trend direction */
  trend: 'increasing' | 'decreasing' | 'stable';
  /** Top enemy corporation threat */
  top_threat: {
    /** Enemy corporation name */
    name: string;
    /** Number of our ships they killed */
    kills: number;
  };
  /** Most frequently lost ship type */
  most_lost_ship: string;
  /** Death timeline for sparkline visualization */
  timeline: {
    /** Date in YYYY-MM-DD format */
    day: string;
    /** Deaths on this day */
    deaths: number;
  }[];
}

export interface CapitalSummary {
  /** Number of capital ship kills */
  kills: number;
  /** Number of capital ship losses */
  losses: number;
  /** Capital efficiency percentage (0-100) */
  efficiency: number;
  /** Capital activity trend direction */
  trend: 'increasing' | 'decreasing' | 'stable';
  /** Most frequently encountered capital type */
  top_capital_type: string;
  /** Primary capital ship used by corporation */
  primary_capital: string;
  /** Capital kill/loss timeline for sparkline visualization */
  timeline: {
    /** Date in YYYY-MM-DD format */
    day: string;
    /** Capital kills on this day */
    kills: number;
    /** Capital losses on this day */
    losses: number;
  }[];
}

export interface PilotSummary {
  /** Total number of pilots in corporation */
  total_pilots: number;
  /** Average morale score across all pilots (0-100) */
  avg_morale: number;
  /** Number of elite pilots (high morale + efficiency) */
  elite_pilots: number;
  /** Number of struggling pilots (low morale or high death rate) */
  struggling_pilots: number;
  /** Pilot activity trend direction */
  trend: 'increasing' | 'decreasing' | 'stable';
  /** Top performing pilot name */
  top_pilot: string;
  /** Active pilot timeline for sparkline visualization */
  timeline: {
    /** Date in YYYY-MM-DD format */
    day: string;
    /** Number of active pilots on this day */
    active_pilots: number;
  }[];
}

export interface GeographySummary {
  /** Number of unique systems with activity */
  unique_systems: number;
  /** Number of unique regions with activity */
  unique_regions: number;
  /** Primary region name (most activity) */
  primary_region: string;
  /** Primary system name (most activity) */
  primary_system: string;
  /** Geographic expansion trend */
  trend: 'expanding' | 'contracting' | 'stable';
  /** Region diversity timeline for sparkline visualization */
  timeline: {
    /** Date in YYYY-MM-DD format */
    day: string;
    /** Number of unique regions with activity on this day */
    unique_regions: number;
  }[];
}

export interface ActivitySummary {
  /** Number of days with activity in the period */
  active_days: number;
  /** Average activity level per day (kills + deaths) */
  avg_daily_activity: number;
  /** Peak activity hour in UTC (0-23) */
  peak_hour: number;
  /** Overall activity trend direction */
  trend: 'increasing' | 'decreasing' | 'stable';
  /** Activity timeline for sparkline visualization */
  timeline: {
    /** Date in YYYY-MM-DD format */
    day: string;
    /** Total activity on this day (kills + deaths) */
    activity: number;
  }[];
}

export interface HuntingSummary {
  /** Threat level classification based on kill efficiency and activity */
  threat_level: 'low' | 'medium' | 'high';
  /** Operational tempo score (0-100) measuring sustained activity */
  operational_tempo: number;
  /** Primary hunting region name */
  hunted_region: string;
  /** Hunting activity trend direction */
  trend: 'escalating' | 'declining' | 'steady';
  /** Kill timeline for sparkline visualization */
  timeline: {
    /** Date in YYYY-MM-DD format */
    day: string;
    /** Kills on this day */
    kills: number;
  }[];
}

// ============================================================================
// Participation Trends (from Alliance)
// ============================================================================

export interface ParticipationDay {
  day: string;
  kills: number;
  deaths: number;
  active_pilots: number;
  isk_destroyed: number;
  isk_lost: number;
}

export interface ParticipationTrend {
  direction: 'rising' | 'falling' | 'stable' | 'insufficient_data' | 'error';
  kills_change_pct: number;
  pilots_change_pct: number;
}

export interface ParticipationTrendsResponse {
  corporation_id: number;
  period_days: number;
  daily: ParticipationDay[];
  trend: ParticipationTrend;
  error?: string;
}

// ============================================================================
// Burnout Index (from Alliance)
// ============================================================================

export interface BurnoutDay {
  day: string;
  kills: number;
  active_pilots: number;
  kills_per_pilot: number;
}

export interface BurnoutIndexResponse {
  corporation_id: number;
  period_days: number;
  daily: BurnoutDay[];
  summary: {
    avg_kills_per_pilot: number;
    kpp_trend_pct: number;
    pilot_trend_pct: number;
    burnout_risk: 'low' | 'moderate' | 'high' | 'critical' | 'unknown';
  };
  error?: string;
}

// ============================================================================
// Attrition Tracker (from Alliance)
// ============================================================================

export interface AttritionDestination {
  corporation_id: number;
  corporation_name: string;
  ticker: string;
  pilot_count: number;
  total_activity: number;
}

export interface AttritionTrackerResponse {
  corporation_id: number;
  period_days: number;
  summary: {
    old_active_pilots: number;
    current_active_pilots: number;
    departed_pilots: number;
    retention_rate: number;
    tracked_destinations: number;
  };
  destinations: AttritionDestination[];
  error?: string;
}

// Re-export DOTLAN geography types
export type { GeographyExtended, DotlanSystemActivity, LiveActivityData, SovCampaign, SovDefenseData, SovChange, TerritorialChangesData, AlliancePower, AlliancePowerData, HeatLevel, VulnerabilityLevel, ChangeDirection } from './geography-dotlan';
export { getHeatLevel, getHeatColor, getVulnerabilityColor, getChangeColor } from './geography-dotlan';
