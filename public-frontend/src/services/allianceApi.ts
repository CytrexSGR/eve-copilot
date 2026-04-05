// Alliance Intelligence API Client

import type { AllianceComplete } from '../types/alliance';
import type { AllianceWormholeEmpire } from '../components/alliance/WormholeView';
import type { HotZone, StrikeWindow, PriorityTarget, CounterDoctrine } from '../types/hunting';

const API_BASE = import.meta.env.VITE_API_URL || '';

// SOV Threats Response Types
export interface SovThreatAttacker {
  alliance_id: number;
  alliance_name: string;
  wh_systems: number;
  kills: number;
  isk_destroyed: number;
}

export interface SovThreatRegion {
  region: string;
  kills: number;
  systems_hit: number;
  isk_destroyed: number;
}

export interface SovThreatWhSystem {
  system_id: number;
  system_name: string;
  kills: number;
  sov_systems_hit: number;
  isk_destroyed: number;
}

export interface SovThreatDoctrine {
  ship_class: string;
  uses: number;
}

export interface SovThreatsData {
  summary: {
    total_wh_systems: number;
    total_kills: number;
    total_isk_destroyed: number;
    overall_threat_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'NONE';
    threat_breakdown: {
      critical: number;
      high: number;
      moderate: number;
      low: number;
    };
  };
  top_attackers: SovThreatAttacker[];
  top_regions: SovThreatRegion[];
  timezone_distribution: {
    us_prime_pct: number;
    eu_prime_pct: number;
    au_prime_pct: number;
  };
  top_wh_systems: SovThreatWhSystem[];
  attacker_doctrines: SovThreatDoctrine[];
  period_days: number;
  updated_at: string | null;
}

export interface SovThreatsResponse {
  alliance_id: number;
  has_sovereignty: boolean;
  message?: string;
  data: SovThreatsData | null;
  error?: string;
}

// Capsuleer Types
export interface CapsuleerCorpStats {
  corp_id: number;
  corp_name: string;
  ticker: string;
  active_pilots: number;
  kills: number;
  deaths: number;
  efficiency: number;
  isk_destroyed: number;
  activity_share: number;
}

export interface CapsuleerPilotStats {
  character_id: number;
  character_name: string;
  corp_id: number;
  corp_name: string;
  ticker: string;
  kills: number;
  final_blows: number;
  deaths: number;
  efficiency: number;
  isk_destroyed: number;
  avg_damage: number;
  min_sp: number;
  ships_analyzed: number;
  modules_analyzed: number;
}

export interface CapsuleerSummary {
  total_pilots: number;
  active_pilots: number;
  total_kills: number;
  total_deaths: number;
  efficiency: number;
  pod_deaths: number;
  ship_deaths: number;
  pod_survival_rate: number;
}

export interface CapsuleersResponse {
  alliance_id: number;
  period_days: number;
  summary: CapsuleerSummary;
  corps: CapsuleerCorpStats[];
  top_pilots: CapsuleerPilotStats[];
  error?: string;
}

export interface CapsuleerTopShip {
  ship_type_id: number;
  ship_name: string;
  uses: number;
  percentage: number;
}

export interface CapsuleerActivity {
  peak_hour: number;
  peak_day: string;
  timezone: string;
  active_days: number;
}

export interface CapsuleerTopVictim {
  alliance_id: number;
  alliance_name: string;
  kills: number;
}

export interface CapsuleerDetailStats {
  kills: number;
  final_blows: number;
  deaths: number;
  efficiency: number;
  isk_destroyed: number;
  isk_lost: number;
  avg_damage: number;
  solo_kills: number;
}

export interface CapsuleerSkillBreakdown {
  [skillName: string]: {
    level: number;
    sp: number;
    multiplier: number;
  };
}

export interface CapsuleerSkillEstimate {
  min_sp: number;
  skill_breakdown: CapsuleerSkillBreakdown;
  ships_analyzed: number;
  modules_analyzed: number;
}

export interface CapsuleerDetailResponse {
  character_id: number;
  character_name: string;
  corp_id: number | null;
  corp_name: string;
  ticker: string;
  stats: CapsuleerDetailStats;
  top_ships: CapsuleerTopShip[];
  activity: CapsuleerActivity | null;
  top_victims: CapsuleerTopVictim[];
  skill_estimate: CapsuleerSkillEstimate | null;
  error?: string;
}

export const allianceApi = {
  /**
   * Get complete alliance intelligence data
   */
  async getComplete(allianceId: number, days: number = 7): Promise<AllianceComplete> {
    const response = await fetch(
      `${API_BASE}/api/intelligence/fast/${allianceId}/complete?days=${days}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch alliance data: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Get alliance wormhole empire data (controlled systems, visitors, economic potential)
   */
  async getWormholeIntel(allianceId: number, days: number = 30): Promise<AllianceWormholeEmpire> {
    const response = await fetch(
      `${API_BASE}/api/intelligence/fast/${allianceId}/wormhole-empire?days=${days}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch wormhole data: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Get alliance logo URL
   */
  getLogoUrl(allianceId: number, size: number = 64): string {
    return `https://images.evetech.net/alliances/${allianceId}/logo?size=${size}`;
  },

  /**
   * Get zKillboard URL for alliance
   */
  getZkillUrl(allianceId: number): string {
    return `https://zkillboard.com/alliance/${allianceId}/`;
  },

  /**
   * Get alliance SOV threats data (WH activity in sov space)
   */
  async getSovThreats(allianceId: number): Promise<SovThreatsResponse> {
    const response = await fetch(
      `${API_BASE}/api/intelligence/fast/${allianceId}/sov-threats`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch SOV threats data: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Get EVE Who URL for alliance
   */
  getEveWhoUrl(allianceId: number): string {
    return `https://evewho.com/alliance/${allianceId}`;
  },

  /**
   * Get Dotlan URL for alliance
   */
  getDotlanUrl(allianceName: string): string {
    return `https://evemaps.dotlan.net/alliance/${encodeURIComponent(allianceName)}`;
  },

  /**
   * Get capsuleer statistics for an alliance (corps + top pilots)
   */
  async getCapsuleers(allianceId: number, days: number = 30): Promise<CapsuleersResponse> {
    const response = await fetch(
      `${API_BASE}/api/intelligence/fast/${allianceId}/capsuleers?days=${days}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch capsuleer data: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Get detailed stats for a specific capsuleer
   */
  async getCapsuleerDetail(allianceId: number, characterId: number, days: number = 30): Promise<CapsuleerDetailResponse> {
    const response = await fetch(
      `${API_BASE}/api/intelligence/fast/${allianceId}/capsuleers/${characterId}?days=${days}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch capsuleer detail: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Get character portrait URL
   */
  getCharacterPortraitUrl(characterId: number, size: number = 64): string {
    return `https://images.evetech.net/characters/${characterId}/portrait?size=${size}`;
  },

  /**
   * Get corporation logo URL
   */
  getCorpLogoUrl(corpId: number, size: number = 64): string {
    return `https://images.evetech.net/corporations/${corpId}/logo?size=${size}`;
  },

  /**
   * Get zKillboard URL for character
   */
  getCharacterZkillUrl(characterId: number): string {
    return `https://zkillboard.com/character/${characterId}/`;
  }
};

// --- Insight Types ---
export interface CorpHeatmapEntry {
  corp_id: number;
  corp_name: string;
  ticker: string;
  hours: number[];
  total: number;
}

export interface CorpHeatmapResponse {
  alliance_id: number;
  period_days: number;
  corps: CorpHeatmapEntry[];
  error?: string;
}

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
  alliance_id: number;
  period_days: number;
  daily: ParticipationDay[];
  trend: ParticipationTrend;
  error?: string;
}

export interface GatecampAlert {
  system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  kills: number;
  pod_kills: number;
  total_isk: number;
  duration_seconds: number;
  severity: 'critical' | 'high' | 'medium';
  camp_type: 'gatecamp' | 'targeted_hunt' | 'hotspot';
  victim_alliances: number;
  attacker_alliance_ids: number[];
}

export interface EnemyDamageProfile {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  kills: number;
  top_ships: Array<{ ship: string; ship_class: string; count: number }>;
  damage_profile: { kinetic: number; thermal: number; em: number; explosive: number };
  primary_damage: string;
  tank_recommendation: string;
}

// --- Insight API Methods ---
export const getCorpActivityHeatmap = async (allianceId: number, days = 7): Promise<CorpHeatmapResponse> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/corp-activity-heatmap?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch corp activity heatmap');
  return response.json();
};

export const getParticipationTrends = async (allianceId: number, days = 14): Promise<ParticipationTrendsResponse> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/participation-trends?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch participation trends');
  return response.json();
};

export const getGatecampAlerts = async (allianceId: number, minutes = 60): Promise<GatecampAlert[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/hunting/gatecamp-alerts?minutes=${minutes}`);
  if (!response.ok) throw new Error('Failed to fetch gatecamp alerts');
  return response.json();
};

export const getEnemyDamageProfiles = async (allianceId: number, days = 30): Promise<EnemyDamageProfile[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/hunting/enemy-damage-profiles?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch enemy damage profiles');
  return response.json();
};

// --- Burnout Index ---
export interface BurnoutDay {
  day: string;
  kills: number;
  active_pilots: number;
  kills_per_pilot: number;
}

export interface BurnoutIndexResponse {
  alliance_id: number;
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

export const getBurnoutIndex = async (allianceId: number, days = 14): Promise<BurnoutIndexResponse> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/burnout-index?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch burnout index');
  return response.json();
};

// --- Attrition Tracker ---
export interface AttritionDestination {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  pilot_count: number;
  total_activity: number;
}

export interface AttritionTrackerResponse {
  alliance_id: number;
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

export const getAttritionTracker = async (allianceId: number, days = 30): Promise<AttritionTrackerResponse> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/attrition-tracker?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch attrition tracker');
  return response.json();
};

// --- Survival Trainer ---
export interface SurvivalPilot {
  character_id: number;
  character_name: string;
  corp_name: string;
  ticker: string;
  total_deaths: number;
  pod_deaths: number;
  ship_deaths: number;
  pod_isk_lost: number;
  ship_isk_lost: number;
  survival_rate: number;
  risk_level: 'good' | 'at_risk' | 'critical';
  training_tip: string;
}

export interface SurvivalTrainerResponse {
  alliance_id: number;
  period_days: number;
  summary: {
    alliance_survival_rate: number;
    pilots_analyzed: number;
    critical_pilots: number;
    at_risk_pilots: number;
    total_pod_isk_wasted: number;
  };
  pilots: SurvivalPilot[];
  error?: string;
}

export const getSurvivalTrainer = async (allianceId: number, days = 30): Promise<SurvivalTrainerResponse> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/survival-trainer?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch survival trainer');
  return response.json();
};

// --- System Danger Radar ---
export interface SystemDangerAttacker {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  kills: number;
}

export interface SystemDanger {
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_deaths: number;
  pod_deaths: number;
  isk_lost: number;
  unique_victims: number;
  active_days: number;
  deaths_per_day: number;
  danger_level: 'critical' | 'high' | 'medium' | 'low';
  peak_hour: number;
  hourly_deaths: number[];
  top_attackers: SystemDangerAttacker[];
}

export const getSystemDangerRadar = async (allianceId: number, days = 7): Promise<SystemDanger[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/hunting/system-danger-radar?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch system danger radar');
  return response.json();
};

// Hunting Command Center APIs
export const getHuntingHotZones = async (allianceId: number, days = 30): Promise<HotZone[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/hunting/hot-zones?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch hot zones');
  return response.json();
};

export const getHuntingStrikeWindow = async (allianceId: number, days = 30): Promise<StrikeWindow> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/hunting/strike-window?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch strike window');
  return response.json();
};

export const getHuntingPriorityTargets = async (allianceId: number, days = 30, limit = 20): Promise<PriorityTarget[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/hunting/priority-targets?days=${days}&limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch priority targets');
  return response.json();
};

export const getHuntingCounterDoctrine = async (allianceId: number, days = 30): Promise<CounterDoctrine> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/hunting/counter-doctrine?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch counter doctrine');
  return response.json();
};

// ========================================
// CORPORATIONS INTELLIGENCE (Corps Tab)
// ========================================

export interface CorpRanking {
  corp_id: number;
  corporation_name: string;
  kills: number;
  deaths: number;
  isk_killed: number;
  isk_lost: number;
  activity_share_pct: number;
  efficiency: number;
  active_pilots: number;
  deaths_per_pilot: number;
}

export interface CorpTrend {
  corp_id: number;
  corporation_name: string;
  day: string;
  efficiency: number;
  activity: number;
}

export interface CorpShipClass {
  corp_id: number;
  corporation_name: string;
  ship_class: string;
  count: number;
  percentage: number;
}

export interface CorpRegion {
  corp_id: number;
  corporation_name: string;
  region_count: number;
  top_regions: string[];
}

export const getCorpsRanking = async (allianceId: number, days = 30): Promise<CorpRanking[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/corps-ranking?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch corps ranking');
  return response.json();
};

export const getCorpsTrends = async (allianceId: number, days = 30): Promise<CorpTrend[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/corps-trends?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch corps trends');
  return response.json();
};

export const getCorpsShips = async (allianceId: number, days = 30): Promise<CorpShipClass[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/corps-ships?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch corps ships');
  return response.json();
};

export const getCorpsRegions = async (allianceId: number, days = 30): Promise<CorpRegion[]> => {
  const response = await fetch(`/api/intelligence/fast/${allianceId}/corps-regions?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch corps regions');
  return response.json();
};

// ============================================================================
// Alliance Offensive/Defensive/Capitals Tabs
// ============================================================================

export const getOffensiveStats = async (
  allianceId: number,
  days: number = 30
): Promise<import('../types/alliance').AllianceOffensiveStats> => {
  const response = await fetch(
    `/api/intelligence/fast/alliance/${allianceId}/offensive-stats?days=${days}`
  );
  if (!response.ok) throw new Error(`Failed to fetch alliance offensive stats: ${response.status}`);
  return response.json();
};

export const getDefensiveStats = async (
  allianceId: number,
  days: number = 30
): Promise<import('../types/alliance').AllianceDefensiveStats> => {
  const response = await fetch(
    `/api/intelligence/fast/alliance/${allianceId}/defensive-stats?days=${days}`
  );
  if (!response.ok) throw new Error(`Failed to fetch alliance defensive stats: ${response.status}`);
  return response.json();
};

export const getCapitalIntel = async (
  allianceId: number,
  days: number = 30
): Promise<import('../types/alliance').AllianceCapitalIntel> => {
  const response = await fetch(
    `/api/intelligence/fast/alliance/${allianceId}/capital-intel?days=${days}`
  );
  if (!response.ok) throw new Error(`Failed to fetch alliance capital intel: ${response.status}`);
  return response.json();
};
export const getGeography = async (
  allianceId: number,
  days: number = 30
): Promise<{
  regions: Array<{
    region_id: number;
    region_name: string;
    kills: number;
    deaths: number;
    activity: number;
    isk_destroyed: string;
    isk_lost: string;
    efficiency: number;
  }>;
  top_systems: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    kills: number;
    deaths: number;
    activity: number;
  }>;
  home_systems: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    kills: number;
    deaths: number;
    activity: number;
    owned_by_alliance: boolean;
  }>;
}> => {
  const response = await fetch(
    `/api/intelligence/fast/alliance/${allianceId}/geography?days=${days}`
  );
  if (!response.ok) throw new Error(`Failed to fetch alliance geography: ${response.status}`);
  return response.json();
};

/**
 * Get extended geography with DOTLAN integration
 */
export const getGeographyExtended = async (
  allianceId: number,
  days: number = 30
): Promise<import('../types/geography-dotlan').GeographyExtended> => {
  const response = await fetch(
    `/api/intelligence/fast/alliance/${allianceId}/geography/extended?days=${days}`
  );
  if (!response.ok) throw new Error(`Failed to fetch alliance geography extended: ${response.status}`);
  return response.json();
};
