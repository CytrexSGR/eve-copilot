// Alliance Intelligence Types

export interface AllianceInfo {
  name: string;
  ticker: string;
}

export interface AllianceHeader {
  net_isk: number;
  efficiency: number;
  isk_efficiency: number;
  kill_efficiency: number;
  kills: number;
  deaths: number;
  kd_ratio: number;
  active_pilots: number;
  peak_hour: number;
  trend_pct: number;
}

export interface HourlyKills {
  hour: number;
  kills: number;
  isk: number;
}

export interface DailyActivity {
  day: string;
  kills: number;
  deaths: number;
  isk_destroyed: number;
  isk_lost: number;
}

export interface ShipEntry {
  type_id: number;
  count: number;
  ship_name: string;
  ship_class: string;
  isk_lost?: number;
}

export interface ZoneEntry {
  system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  kills?: number;
  deaths?: number;
  activity_level?: string;
}

export interface EnemyEntry {
  alliance_id: number;
  alliance_name: string;
  kills: number;
  isk: number;
}

export interface EnemyVulnerability {
  alliance_id: number;
  alliance_name: string;
  losses_to_us: number;
  weak_hours: number[];
}

export interface ActiveWar {
  war_id: number;
  enemy_alliance_id: number;
  enemy_alliance_name: string;
  first_kill_at: string | null;
  last_kill_at: string | null;
  duration_days: number;
  total_kills: number;
  total_isk_destroyed: number;
}

export interface CoalitionMember {
  alliance_id: number;
  alliance_name: string;
  joint_kills: number;
  joint_isk: number;
}

export interface HourlyActivity {
  hours: Array<{ hour: number; deaths: number; isk_lost: number }>;
  peak_danger_start: number;
  peak_danger_end: number;
  safe_start: number;
  safe_end: number;
}

export interface WeeklyPattern {
  days: Array<{
    day: string;
    day_index: number;
    kills: number;
    deaths: number;
    isk_destroyed: number;
    isk_lost: number;
  }>;
  best_day: string | null;
  worst_day: string | null;
}

export interface SecurityPreference {
  highsec: number;
  lowsec: number;
  nullsec: number;
  wormhole: number;
  highsec_pct?: number;
  lowsec_pct?: number;
  nullsec_pct?: number;
  wormhole_pct?: number;
}

export interface Economics {
  isk_destroyed: number;
  isk_lost: number;
  isk_balance: number;
  cost_per_kill: number;
  cost_per_death: number;
}

export interface ExpensiveLoss {
  killmail_id: number;
  ship_type_id: number;
  ship_name: string;
  isk_value: number;
  system_name: string;
  killed_at: string;
}

export interface ProductionNeed {
  type_id: number;
  type_name: string;
  weekly_losses: number;
  estimated_cost: number;
}

export interface ShipEffectiveness {
  ship_class: string;
  deaths: number;
  isk_lost: number;
  verdict: 'bleeding' | 'moderate' | 'acceptable';
}

export interface DamageTaken {
  damage_type: string;
  percentage: number;
}

export interface EwarThreat {
  ewar_type: string;
  count: number;
  percentage: number;
}

export interface EquipmentIntel {
  weapons: Array<{ type_id: number; type_name: string; count: number }>;
  tank: Array<{ type_id: number; type_name: string; count: number }>;
  cargo: Array<{ type_id: number; type_name: string; count: number; total_value: number }>;
}

export interface SovSystem {
  solar_system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  structure_type_id: number;
  vulnerability_occupancy_level: number | null;
  vulnerable_start_time: string | null;
  vulnerable_end_time: string | null;
}

export interface SovRegion {
  region_name: string;
  system_count: number;
  avg_adm: number;
}

export interface Sovereignty {
  systems: SovSystem[];
  count: number;
  regions: SovRegion[];
  error?: string;
}

export interface BattleEntry {
  battle_id: number;
  started_at: string | null;
  last_kill_at: string | null;
  total_kills: number;
  total_isk_destroyed: number;
  capital_kills: number;
  system_name: string;
  region_name: string;
  alliance_kills: number;
  alliance_losses: number;
  alliance_isk_destroyed: number;
  alliance_isk_lost: number;
}

export interface Recommendation {
  priority: number;
  category: 'avoid' | 'attack' | 'fit' | 'doctrine';
  text: string;
}

export interface AllianceComplete {
  alliance_id: number;
  period_days: number;
  generated_at: string;
  alliance_info: AllianceInfo;
  header: AllianceHeader;
  combat: {
    summary: {
      alliance_id: number;
      period_days: number;
      kills: number;
      deaths: number;
      isk_destroyed: number;
      isk_lost: number;
      efficiency: number;
      kd_ratio: number;
    };
    kills_activity: {
      hourly_kills: HourlyKills[];
      daily_activity: DailyActivity[];
    };
    ships_killed: ShipEntry[];
    ships_lost: ShipEntry[];
    ship_effectiveness: ShipEffectiveness[];
  };
  geography: {
    danger_zones: ZoneEntry[];
    activity_zones: ZoneEntry[];
    security_preference: SecurityPreference;
  };
  temporal: {
    hourly_activity: HourlyActivity;
    weekly_pattern: WeeklyPattern;
  };
  enemies: {
    top_enemies: EnemyEntry[];
    enemy_vulnerabilities: EnemyVulnerability[];
    active_wars: ActiveWar[];
  };
  coalition: {
    detected_allies: CoalitionMember[];
  };
  economics: {
    summary: Economics;
    expensive_losses: ExpensiveLoss[];
    production_needs: ProductionNeed[];
    total_weekly_production_cost: number;
  };
  equipment: EquipmentIntel;
  threats: {
    damage_taken: DamageTaken[];
    ewar_threats: EwarThreat[];
  };
  sovereignty: Sovereignty;
  battles: {
    recent: BattleEntry[];
  };
  recommendations: Recommendation[];
}

// ============================================================================
// Alliance Offensive/Defensive/Capitals Tabs
// ============================================================================

// Import reusable types from corporation.ts
import type {
  OffensiveSummary,
  DefensiveSummary,
  CapitalSummary,
  ThreatProfile,
  EngagementProfile,
  SoloKiller,
  DoctrineShip,
  ShipClassDist,
  VictimAnalysis,
  HotZone,
  RegionActivity,
  TimelineDay,
  CapitalThreat,
  TopVictim,
  DeathPronePilot,
  LossAnalysis,
  DeathZone,
  CapitalLosses,
  TopThreat,
  FleetComposition,
  ShipDetail,
  CapitalTimelineDay,
  GeographicHotspot,
  TopKiller,
  TopLoser,
} from './corporation';

export interface AllianceOffensiveStats {
  alliance_id: number;
  alliance_name: string;
  period_days: number;
  summary: OffensiveSummary;
  engagement_profile: EngagementProfile;  // Object, not array
  solo_killers: SoloKiller[];
  doctrine_profile: DoctrineShip[];
  ship_losses_inflicted: ShipClassDist[];  // Was ShipLoss
  victim_analysis: VictimAnalysis;
  kill_heatmap: HotZone[];  // Was KillZone
  hunting_regions: RegionActivity[];
  kill_timeline: TimelineDay[];
  capital_threat?: CapitalThreat;
  top_victims: TopVictim[];
  high_value_kills?: any[];
  hunting_hours?: any;
  damage_dealt?: any[];
  ewar_usage?: any[];
  hot_systems?: any[];
  effective_doctrines?: any[];
  kill_velocity?: any[];
}

export interface AllianceDefensiveStats {
  alliance_id: number;
  alliance_name: string;
  period_days: number;
  summary: DefensiveSummary;
  threat_profile: ThreatProfile;  // Object, not array
  death_prone_pilots: DeathPronePilot[];
  ship_losses: ShipClassDist[];  // Was ShipLoss
  doctrine_weakness: DoctrineShip[];
  loss_analysis: LossAnalysis;
  death_heatmap: DeathZone[];
  loss_regions: RegionActivity[];
  death_timeline: TimelineDay[];
  capital_losses?: CapitalLosses;
  top_threats: TopThreat[];
  high_value_losses?: any[];
  safe_danger_hours?: any;
  damage_taken?: any[];
  ewar_threats?: any[];
  danger_systems?: any[];
}

export interface AllianceCapitalIntel {
  alliance_id: number;
  alliance_name: string;
  period_days: number;
  summary: CapitalSummary;
  fleet_composition: FleetComposition[];
  ship_details: ShipDetail[];
  capital_timeline: CapitalTimelineDay[];
  geographic_hotspots: GeographicHotspot[];
  top_killers: TopKiller[];
  top_losers: TopLoser[];
  capital_engagements?: any[];
  recent_activity?: any[];
}
