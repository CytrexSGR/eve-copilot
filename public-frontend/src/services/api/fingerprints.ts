// Fingerprints and Counter-Doctrine API functions
import type {
  AllianceFingerprint,
  FingerprintListResponse,
  CoalitionSummary,
  DoctrineDistribution,
  FleetCounterRecommendation
} from '../../types/reports';

// ==================== API Configuration ====================

import { api } from './client';

// ==================== Fingerprint API ====================

export const fingerprintApi = {
  list: async (params: {
    limit?: number;
    offset?: number;
    doctrine?: string;
    coalition_id?: number;
    search?: string;
    min_activity?: number;
  } = {}): Promise<FingerprintListResponse> => {
    const queryParams: Record<string, string | number> = {};
    if (params.limit) queryParams.limit = params.limit;
    if (params.offset) queryParams.offset = params.offset;
    if (params.doctrine) queryParams.doctrine = params.doctrine;
    if (params.coalition_id) queryParams.coalition_id = params.coalition_id;
    if (params.search) queryParams.search = params.search;
    if (params.min_activity) queryParams.min_activity = params.min_activity;
    const { data } = await api.get('/fingerprints/', { params: queryParams });
    return data;
  },

  get: async (allianceId: number): Promise<AllianceFingerprint> => {
    const { data } = await api.get(`/fingerprints/${allianceId}`);
    return data;
  },

  getCoalitions: async (minMembers: number = 2): Promise<{ coalitions: CoalitionSummary[] }> => {
    const { data } = await api.get('/fingerprints/coalitions/list', { params: { min_members: minMembers } });
    return data;
  },

  getDoctrineDistribution: async (): Promise<DoctrineDistribution> => {
    const { data } = await api.get('/fingerprints/doctrines/distribution');
    return data;
  }
};

// ==================== Live Ops API ====================

export interface LiveOpsData {
  timeframe: { minutes: number; label: string };
  summary: {
    active_doctrines: number;
    total_fleets: number;
    alliances_active: number;
    hot_regions: number;
    dominant_doctrine: string;
    hottest_region: string;
    peak_hour: number;
    avg_fleet_size: number;
  };
  active_doctrines: Array<{
    ship_class: string;
    alliance_name: string;
    alliance_id: number;
    top_ships: string[];
    activity: number;
    isk_destroyed: number;
    isk_lost: number;
    isk_efficiency: number;
    kills: number;
    losses: number;
    kd_ratio: number;
    survival_rate: number;
  }>;
  hotspots: Array<{
    region_id: number;
    region_name: string;
    system_count: number;
    fleet_count: number;
    total_kills: number;
    threat_level: 'critical' | 'hot' | 'active' | 'low';
    dominant_ship_class: string;
    top_alliance_id: number | null;
    top_alliance_name: string | null;
  }>;
  counter_matrix: Array<{
    attacker_class: string;
    victim_class: string;
    kills: number;
  }>;
  trends: Array<{
    ship_class: string;
    current_activity: number;
    previous_activity: number;
    change_percent: number;
    trend: 'up' | 'down' | 'stable';
  }>;
  ship_distribution: Array<{
    ship_class: string;
    count: number;
    percent: number;
  }>;
  efficiency_ranking: {
    top: Array<{ ship_class: string; efficiency: number; kills: number; losses: number; trend: string }>;
    bottom: Array<{ ship_class: string; efficiency: number; kills: number; losses: number; trend: string }>;
  };
  alerts: Array<{
    type: 'detection' | 'counter' | 'trend';
    message: string;
    timestamp: string | null;
  }>;
  generated_at: string;
}

export async function getLiveOpsData(minutes: number): Promise<LiveOpsData> {
  const { data } = await api.get('/fingerprints/live-ops', { params: { minutes } });
  return data;
}

// ==================== Counter-Doctrine API ====================

export const counterDoctrineApi = {
  getCounter: async (input: {
    doctrine_name: string;
    ship_name: string;
    estimated_count: number;
    tank_type: 'shield' | 'armor';
    engagement_range: 'short' | 'medium' | 'long';
    avg_dps: number;
  }): Promise<FleetCounterRecommendation> => {
    const { data } = await api.post('/fleet/counter', input);
    return data;
  },

  listKnownDoctrines: async () => {
    const { data } = await api.get('/fleet/doctrines');
    return data;
  },

  listCompositions: async () => {
    const { data } = await api.get('/fleet/compositions');
    return data;
  }
};
