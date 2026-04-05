// Re-export domain types for backwards compatibility
export * from './battle';
export * from './economy';

// Pilot Intelligence Battle Report Types

// ==================== Alliance Wars Types ====================

export interface CoalitionMember {
  alliance_id: number;
  name: string;
  activity: number;
}

export interface Coalition {
  name: string;
  leader_alliance_id: number;
  leader_name: string;
  member_count: number;
  members: CoalitionMember[];
  total_kills: number;
  total_losses: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
  total_activity: number;
}

export interface UnaffiliatedAlliance {
  alliance_id: number;
  name: string;
  kills: number;
  losses: number;
  isk_lost: number;
  activity: number;
}

export interface AllianceWars {
  period: string;
  global: {
    active_conflicts: number;
    total_alliances_involved: number;
    total_kills: number;
    total_isk_destroyed: number;
  };
  coalitions?: Coalition[];
  unaffiliated_alliances?: UnaffiliatedAlliance[];
  conflicts: Array<{
    alliance_1_id: number;
    alliance_1_name: string;
    alliance_2_id: number;
    alliance_2_name: string;
    alliance_1_kills: number;
    alliance_1_losses: number;
    alliance_1_isk_destroyed: number;
    alliance_1_isk_lost: number;
    alliance_1_efficiency: number;
    alliance_2_kills: number;
    alliance_2_losses: number;
    alliance_2_isk_destroyed: number;
    alliance_2_isk_lost: number;
    alliance_2_efficiency: number;
    duration_days: number;
    primary_regions: string[];
    active_systems: Array<{
      system_id: number;
      system_name: string;
      kills: number;
      security?: number;
      region_name?: string;
    }>;
    winner: string | null;
    // War Intelligence Fields
    alliance_1_ship_classes?: import('./battle').ShipClasses;
    alliance_2_ship_classes?: import('./battle').ShipClasses;
    hourly_activity?: Record<number, number>;
    peak_hours?: number[];
    avg_kill_value?: number;
    alliance_1_biggest_loss?: import('./battle').BiggestLoss;
    alliance_2_biggest_loss?: import('./battle').BiggestLoss;
  }>;
  strategic_hotspots?: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    kills_24h: number;
    strategic_value: number;
  }>;
}

export interface AllianceWarsAnalysis {
  summary: string;
  insights: string[];
  trends?: string[];
  generated_at: string;
  error?: string;
}

// ==================== Power Assessment Types ====================

export interface PowerAssessmentEntry {
  name: string;
  alliance_id?: number;
  pilots: number;
  kills: number;
  losses: number;
  efficiency: number;
  net_isk: number;
  isk_destroyed?: number;
  isk_lost?: number;
  isk_per_pilot?: number;
  trend_24h?: number | null;  // Change vs previous 24h
  history_7d?: number[];      // 7-day net ISK history for sparkline
}

export interface PowerAssessment {
  isk_efficiency?: PowerAssessmentEntry[];
  gaining_power: PowerAssessmentEntry[];
  losing_power: PowerAssessmentEntry[];
  contested?: string[];
}

export interface StrategicBriefing {
  briefing: string;
  highlights: string[];
  alerts: string[];
  power_assessment?: PowerAssessment;
  generated_at: string;
  error?: string;
}

// ==================== Alliance Doctrine Fingerprints ====================

export interface ShipUsage {
  type_id: number;
  type_name: string;
  ship_class: string;
  uses: number;
  percentage: number;
}

export interface AllianceFingerprint {
  alliance_id: number;
  alliance_name: string;
  total_uses: number;
  unique_ships: number;
  primary_doctrine: string;
  coalition_id: number | null;
  coalition_leader_name: string | null;
  ship_fingerprint: ShipUsage[];
  data_period_days: number;
  last_updated: string;
}

export interface FingerprintListResponse {
  fingerprints: AllianceFingerprint[];
  total: number;
}

export interface FingerprintCoalitionMember {
  alliance_id: number;
  alliance_name: string;
  primary_doctrine: string;
  total_uses: number;
}

export interface CoalitionSummary {
  coalition_id: number;
  leader_name: string;
  member_count: number;
  total_ship_uses: number;
  primary_doctrines: string[];
  members: FingerprintCoalitionMember[];
}

export interface DoctrineDistribution {
  distribution: {
    doctrine: string;
    alliances: number;
    total_ships: number;
  }[];
}

export interface FleetCounterRecommendation {
  their_doctrine: string;
  their_count: number;
  their_dps: number;
  counter_doctrine: string;
  composition: {
    ship: string;
    role: string;
    count: number;
    dps_per_ship: number;
  }[];
  total_dps: number;
  dps_advantage: number;
  engagement_advice: string;
  positioning: string;
  confidence: number;
  notes: string;
}
