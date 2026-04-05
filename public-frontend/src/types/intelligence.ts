export interface IntelligenceAlliance {
  id: number;
  name: string;
  ticker: string;
  has_reports: boolean;
}

export interface ReportContent {
  content?: string;
  full_content?: string;
  file: string;
  modified: string;
}

export interface LLMAnalysis {
  briefing?: string;
  fitting?: string;
  patterns?: string;
  forecast?: string;
  full_content?: string;
  file: string;
  modified: string;
}

export interface IntelligenceReports {
  overview: ReportContent | null;
  combat_intel: ReportContent | null;
  llm_analysis: LLMAnalysis | null;
}

export interface IntelligenceMetadata {
  model?: string;
  total_tokens?: number;
  duration_seconds?: number;
}

export interface AllianceIntelligence {
  alliance: IntelligenceAlliance;
  generated_at: string | null;
  reports: IntelligenceReports;
  metadata: IntelligenceMetadata;
}

// New Structured Intelligence Types
export interface DoctrineStats {
  doctrine_name: string;
  is_known_doctrine: boolean;
  ship_type_id: number;
  ship_name: string;
  sightings: number;
  percentage_of_total: number;
  avg_dps: number;
  dps_range: [number, number];
  tank_type: string;
  weapon_type: string;
  engagement_range: string;
  trend: 'rising' | 'stable' | 'declining';
  first_seen: string;
  last_seen: string;
}

export interface FleetStats {
  total_fleets_observed: number;
  avg_fleet_size: number;
  max_fleet_size: number;
  composition_breakdown: {
    dps: number;
    logi: number;
    support: number;
    capital: number;
  };
  coordination_score: number;
}

export interface CombatProfile {
  aggression_score: number;
  efficiency_rating: number;
  avg_engagement_duration: number;
  target_preferences: string[];
  avoidance_patterns: string[];
}

export interface RegionActivity {
  region_id: number;
  region_name: string;
  kills: number;
  percentage: number;
}

export interface TrendAnalysis {
  activity_7d: number;
  activity_30d: number;
  activity_trend: 'rising' | 'stable' | 'declining';
  new_doctrines: string[];
  abandoned_doctrines: string[];
  escalation_signals: string[];
}

export interface PeriodStats {
  ships_destroyed: number;
  ships_lost: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
}

export interface CounterRecommendation {
  target_doctrine: string;
  counter_doctrine: string;
  counter_type: string;
  effectiveness_score: number;
  ship_recommendations: string[];
  damage_types: string[];
  engagement_advice: string;
}

export interface StructuredIntelligence {
  alliance_id: number;
  alliance_name: string;
  period_days: number;
  generated_at: string;
  observed_doctrines: DoctrineStats[];
  primary_doctrine: DoctrineStats | null;
  doctrine_diversity_score: number;
  fleet_stats: FleetStats;
  typical_fleet_size: number;
  logi_ratio: number;
  support_ratio: number;
  capital_usage: string;
  combat_profile: CombatProfile;
  preferred_engagement_range: string;
  primary_damage_types: string[];
  peak_activity_hours: number[];
  preferred_regions: RegionActivity[];
  trends: TrendAnalysis;
  period_stats?: PeriodStats;
  counter_recommendations: CounterRecommendation[];
}

// Intelligence Dashboard Types

export interface CombatSummary {
  kills: number;
  deaths: number;
  efficiency: number;
  isk_destroyed: number;
  isk_lost: number;
  isk_balance: number;
  trend: 'rising' | 'stable' | 'declining';
}

export interface WarEconomics {
  isk_lost: number;
  isk_destroyed: number;
  isk_balance: number;
  cost_per_kill: number;
}

export interface ExpensiveLoss {
  ship_type_id: number;
  ship_type_name: string;
  ship_class: string;
  count: number;
  total_isk: number;
  avg_isk: number;
  trend: 'rising' | 'stable' | 'declining';
}

export interface ProductionNeed {
  ship_type_id: number;
  ship_type_name: string;
  ship_class: string;
  losses_period: number;
  losses_per_day: number;
  weekly_replacement: number;
  estimated_cost: number;
  priority: 'critical' | 'high' | 'medium' | 'mass' | 'low';
}

export interface LossHourAnalysis {
  hourly_losses: number[];
  peak_danger_start: number;
  peak_danger_end: number;
  safe_start: number;
  safe_end: number;
}

export interface DamageTaken {
  damage_type: string;
  percentage: number;
  total_damage: number;
}

export interface EwarThreat {
  ewar_type: string;
  kills_affected: number;
  percentage: number;
}

export interface AttackerAlliance {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  total_attacks: number;
  kills_against_us: number;
  efficiency_vs_us: number;
}

export interface ShipEffectiveness {
  ship_class: string;
  kills: number;
  deaths: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
  isk_balance: number;
  verdict: 'profitable' | 'break_even' | 'bleeding';
}

export interface EnemyVulnerability {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  weak_systems: string[];
  weak_hours: [number, number];
  losses_to_us: number;
}

export interface Recommendation {
  priority: number;
  category: 'avoid' | 'attack' | 'fit' | 'doctrine';
  text: string;
}

export interface SystemHotspot {
  system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  losses: number;
  isk_lost: number;
  activity_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface IntelligenceDashboard {
  alliance_id: number;
  alliance_name: string;
  alliance_ticker: string;
  period_days: number;
  generated_at: string;
  combat_summary: CombatSummary;
  economics: WarEconomics;
  expensive_losses: ExpensiveLoss[];
  production_needs: ProductionNeed[];
  total_weekly_production_cost: number;
  danger_zones: SystemHotspot[];
  loss_timing: LossHourAnalysis;
  damage_taken: DamageTaken[];
  ewar_threats: EwarThreat[];
  top_attackers: AttackerAlliance[];
  ship_effectiveness: ShipEffectiveness[];
  enemy_vulnerabilities: EnemyVulnerability[];
  recommendations: Recommendation[];
}

// ==================== Fast Intelligence Types ====================
// Pre-aggregated data with ~50ms response time

export interface FastIntelSummary {
  alliance_id: number;
  period_days: number;
  kills: number;
  deaths: number;
  isk_destroyed: number | string;
  isk_lost: number | string;
  efficiency: number | string;
  kd_ratio: number;
}

export interface FastEconomics {
  isk_destroyed: number | string;
  isk_lost: number | string;
  isk_balance: number | string;
  cost_per_kill: number;
  cost_per_death: number;
  profitable: boolean;
}

export interface FastDangerZone {
  system_id: number;
  deaths: number;
  system_name: string;
  region_id: number;
  region_name: string;
  activity_level?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface FastShipLost {
  type_id: number;
  count: number;
  isk_lost: number | string;
  ship_name: string;
  ship_class: string;
}

export interface FastEnemy {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  kills: number;
  isk_destroyed: number | string;
}

export interface FastHourlyActivity {
  kills_by_hour: number[];
  deaths_by_hour: number[];
  peak_danger_start: number;
  peak_danger_end: number;
  safe_start: number;
  safe_end: number;
}

export interface FastExpensiveLoss {
  killmail_id: number;
  type_id: number;
  ship_name: string;
  ship_class: string;
  isk_lost: number | string;
  time: string | null;
  system_name: string;
}

export interface FastShipEffectiveness {
  ship_class: string;
  deaths: number;
  isk_lost: number | string;
  verdict: 'bleeding' | 'moderate' | 'acceptable';
}

export interface FastProductionNeed {
  ship_type_id: number;
  ship_name: string;
  ship_class: string;
  losses_period: number;
  losses_per_day: number;
  weekly_replacement: number;
  estimated_cost: number;
  priority: 'critical' | 'high' | 'medium' | 'low';
}

export interface FastDamageTaken {
  damage_type: string;
  percentage: number;
}

export interface FastEwarThreat {
  ewar_type: string;
  ship_class: string;
  kills_affected: number;
  percentage: number;
}

export interface FastEnemyVulnerability {
  alliance_id: number;
  alliance_name: string;
  losses_to_us: number;
  weak_systems: string[];
  weak_hours: [number, number];
}

export interface FastRecommendation {
  priority: number;
  category: 'avoid' | 'attack' | 'fit' | 'doctrine';
  text: string;
}

export interface FastIntelDashboard {
  alliance_id: number;
  period_days: number;
  generated_at: string;
  summary: FastIntelSummary;
  economics: FastEconomics;
  danger_zones: FastDangerZone[];
  ships_lost: FastShipLost[];
  top_enemies: FastEnemy[];
  hourly_activity: FastHourlyActivity;
  expensive_losses: FastExpensiveLoss[];
  ship_effectiveness: FastShipEffectiveness[];
  production_needs: FastProductionNeed[];
  total_weekly_production_cost: number;
  damage_taken: FastDamageTaken[];
  ewar_threats: FastEwarThreat[];
  enemy_vulnerabilities: FastEnemyVulnerability[];
  recommendations: FastRecommendation[];
  equipment_intel?: EquipmentIntel;
}

export interface FastAllianceSummary {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  kills: number;
  deaths: number;
  isk_destroyed: number | string;
  isk_lost: number | string;
  efficiency: number;
}

// ==================== Equipment Intelligence Types ====================
// Comprehensive item-based analysis for alliance Intel officers

export interface WeaponLost {
  type_id: number;
  weapon_name: string;
  weapon_group: string;
  total_lost: number;
  kills_with_weapon: number;
  avg_price: number;
  total_isk_lost: number;
}

export interface WeaponsIntel {
  weapons: WeaponLost[];
  damage_profile: Record<string, number>;
  primary_damage_type: string;
  secondary_damage_type: string;
  weapon_class_distribution: Record<string, number>;
  primary_weapon_class: string;
  counter_tank_advice: string;
  total_weapons_lost: number;
}

export interface TankModule {
  type_id: number;
  module_name: string;
  module_group: string;
  total_lost: number;
  kills_with_module: number;
  avg_price: number;
  total_isk_lost: number;
}

export interface TankProfile {
  top_modules: TankModule[];
  shield_percent: number;
  armor_percent: number;
  active_percent: number;
  passive_percent: number;
  doctrine: string;
  resist_breakdown: Record<string, number>;
  resist_gap: string;
  resist_gap_value: number;
  resist_gap_severity: number;
  counter_damage_advice: string;
  total_tank_modules: number;
}

export interface StrategicBreakdown {
  count: number;
  isk: number;
  percentage: number;
  items: string[];
}

export interface LogisticsInsight {
  type: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

export interface CargoItem {
  type_id: number;
  item_name: string;
  item_group: string;
  item_category: string;
  total_lost: number;
  kills_with_item: number;
  avg_price: number;
  total_isk_lost: number;
}

export interface CargoIntel {
  cargo: CargoItem[];
  strategic_breakdown: Record<string, StrategicBreakdown>;
  primary_logistics_focus: string;
  total_cargo_isk: number;
  logistics_insights: LogisticsInsight[];
}

export interface EquipmentIntel {
  alliance_id: number;
  analysis_period_days: number;
  weapons_lost: WeaponsIntel;
  tank_profile: TankProfile;
  cargo_intel: CargoIntel;
  strategic_summary: string[];
}

// ==================== Killmail Intelligence Types ====================
// Threat composition, capital radar, logi scores, hunting, pilot risk

// === Threat Intelligence (Defensive Tab) ===
export interface ThreatEntity {
  attacker_alliance_id: number;
  alliance_name: string;
  kills_on_us: number;
  isk_destroyed: number;
  ship_diversity: number;
  ship_types_used: number[];
  damage_profile?: DamageProfile;
}

export interface DamageProfile {
  em: number;
  thermal: number;
  kinetic: number;
  explosive: number;
}

export interface CapitalSighting {
  solar_system_id: number;
  system_name: string;
  capital_alliance_id: number;
  alliance_name: string;
  capital_class: string;
  appearances: number;
  first_seen: string;
  last_seen: string;
}

export interface ThreatComposition {
  entity_type: string;
  entity_id: number;
  days: number;
  threats: ThreatEntity[];
  capital_sightings: CapitalSighting[];
  total_threats: number;
}

export interface CapitalRadar {
  entity_type: string;
  entity_id: number;
  days: number;
  capital_systems: CapitalSighting[];
  escalation_stats: {
    avg_escalation_seconds?: number;
    min_escalation_seconds?: number;
    escalation_count?: number;
  };
  total_capital_systems: number;
}

export interface LogiScoreEntry {
  alliance_id: number;
  alliance_name: string;
  logi_score: number;
  logi_pilots: number;
  avg_fleet_size: number;
  kills_on_us: number;
}

// === Hunting Intelligence ===
export interface HuntingSystem {
  solar_system_id: number;
  system_name: string;
  region_id: number;
  region_name: string;
  score: number;
  adm_military: number;
  player_deaths: number;
  avg_kill_value: number;
  has_capital_umbrella: boolean;
  victim_alliances: number[];
}

export interface HuntingScores {
  systems: HuntingSystem[];
  total_systems_analyzed: number;
  days: number;
  region_id?: number;
}

// === Pilot Risk Intelligence ===
export interface PilotRiskEntry {
  character_id: number;
  kills: number;
  deaths: number;
  isk_killed: number;
  isk_lost: number;
  efficiency: number;
  solo_deaths: number;
  avg_loss_value: number;
  performance_category: 'NORMAL' | 'TRAINABLE' | 'LIABILITY';
  awox_count: number;
}

export interface PilotRiskSummary {
  total_analyzed: number;
  normal: number;
  trainable: number;
  liability: number;
  at_risk_awox: number;
}

export interface PilotRiskData {
  corporation_id: number;
  days: number;
  pilots: PilotRiskEntry[];
  summary: PilotRiskSummary;
}

export interface CorpHealth {
  corporation_id: number;
  days: number;
  member_count: number;
  active_pilots: number;
  activity_rate: number;
  isk_killed: number;
  isk_lost: number;
  isk_efficiency: number;
  member_trend: { date: string; count: number }[];
}
