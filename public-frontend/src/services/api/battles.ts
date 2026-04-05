// Battle-related API functions
import { api } from './client';
import type {
  ActiveBattle,
  BattleTimelineResponse,
  BattleReshipmentResponse,
  ConflictsResponse,
  TimezoneHeatmapResponse,
} from '../../types/battle';
import type {
  FuelTrendsResponse,
  SupercapTimersResponse,
  ManipulationAlertsResponse,
  AllianceCapitalDetailExtended,
} from '../../types/economy';
import type { CapitalAlliancesResponse } from './economy';

// API client imported from ./client

// ==================== Battle Side Types ====================

export interface BattleSideAlliance {
  alliance_id: number;
  alliance_name: string;
  coalition_id?: number | null;
  coalition_name?: string | null;
  pilots: number;
  corps?: number;
  kills: number;
  losses: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
}

export interface BattleSideShipLost {
  ship_type_id: number;
  ship_name: string;
  ship_class: string;
  count: number;
  total_value: number;
}

export interface BattleSideShipUsed {
  ship_type_id: number;
  ship_name: string;
  ship_class: string;
  kills: number;
  isk_destroyed: number;
}

export interface BattleSideTotals {
  pilots: number;
  kills: number;
  losses: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
  alliance_count: number;
  ship_types_lost?: number;
  ship_types_used?: number;
}

export interface BattleSide {
  alliances: BattleSideAlliance[];
  ships_lost?: BattleSideShipLost[];
  ships_used?: BattleSideShipUsed[];
  totals: BattleSideTotals;
}

export interface BattleSidesResponse {
  battle_id: number;
  sides_determined: boolean;
  message?: string;
  side_a: BattleSide;
  side_b: BattleSide;
}

// ==================== Commander Intel Types ====================

export interface CapitalPresence {
  lost: Array<{
    ship_name: string;
    alliance_id: number | null;
    alliance_name: string;
    count: number;
    value: number;
  }>;
  on_field: Array<{
    ship_name: string;
    alliance_id: number | null;
    alliance_name: string;
  }>;
  has_capitals: boolean;
  has_supers: boolean;
}

export interface TopKiller {
  character_id: number;
  character_name: string;
  corporation_id: number | null;
  corporation_name: string | null;
  corporation_ticker: string | null;
  alliance_id: number | null;
  alliance_name: string;
  coalition_id: number | null;
  coalition_name: string | null;
  kills: number;
  isk_destroyed: number;
}

export interface HighValueLoss {
  killmail_id: number;
  ship_name: string;
  ship_class: string;
  value: number;
  pilot_name: string;
  corporation_id: number | null;
  corporation_name: string | null;
  corporation_ticker: string | null;
  alliance_id: number | null;
  alliance_name: string;
  coalition_id: number | null;
  coalition_name: string | null;
  time: string | null;
}

export interface DoctrineInfo {
  losses: Array<{
    ship_class: string;
    ship_name: string;
    count: number;
    value: number;
  }>;
  fielding: Array<{
    ship_class: string;
    ship_name: string;
    engagements: number;
  }>;
}

export interface CommanderIntelResponse {
  battle_id: number;
  generated_at: string;
  capitals: CapitalPresence;
  top_killers: TopKiller[];
  high_value_losses: HighValueLoss[];
  momentum: Array<{
    time: string;
    kills_by_alliance: Record<string, { kills: number; isk_destroyed: number }>;
  }>;
  doctrines: Record<string, DoctrineInfo>;
  summary: {
    total_kills: number;
    total_isk: number;
    capital_engagement: boolean;
    super_escalation: boolean;
    high_value_count: number;
  };
}

// ==================== Damage Analysis Response ====================

export interface DamageAnalysisResponse {
  battle_id: number;
  generated_at: string;
  total_damage_analyzed: number;
  damage_profile: {
    em: number;
    thermal: number;
    kinetic: number;
    explosive: number;
  };
  primary_damage_type: string | null;
  secondary_damage_type: string | null;
  tank_recommendation: string | null;
  alliance_profiles: Array<{
    alliance_id: number;
    alliance_name: string;
    total_damage: number;
    damage_profile: {
      em: number;
      thermal: number;
      kinetic: number;
      explosive: number;
    };
    primary_weapons: Array<{
      class: string;
      damage: number;
    }>;
  }>;
  top_damage_ships: Array<{
    alliance_id: number;
    alliance_name: string;
    ship_name: string;
    ship_class: string;
    total_damage: number;
    engagements: number;
  }>;
  coverage: {
    matched_weapons: number;
    unmatched_weapons: number;
  };
}

// ==================== Victim Tank Analysis Response ====================

export interface VictimTankResistEntry {
  avg: number;
  weakness: 'EXPLOIT' | 'SOFT' | 'NORMAL';
}

export interface VictimTankTopLoss {
  killmail_id: number;
  ship_name: string;
  ship_value: number;
  ehp: number;
  tank_type: string;
  resist_weakness: string;
}

export interface VictimTankAnalysisResponse {
  battle_id: number;
  killmails_analyzed: number;
  tank_distribution: { shield: number; armor: number; hull: number };
  avg_ehp: number;
  resist_profile: {
    em: VictimTankResistEntry;
    thermal: VictimTankResistEntry;
    kinetic: VictimTankResistEntry;
    explosive: VictimTankResistEntry;
  };
  top_losses: VictimTankTopLoss[];
}

// ==================== Strategic Context Response ====================

export interface SovCampaign {
  system_name: string;
  structure_type: string;
  defender: string | null;
  score: number | null;
  adm: number | null;
}

export interface StrategicContextResponse {
  battle_id: number;
  system_sov: { alliance_id: number; alliance_name: string } | null;
  active_campaigns: SovCampaign[];
  constellation_campaigns: number;
  strategic_note: string | null;
}

// ==================== Attacker Loadouts Response ====================

export interface LoadoutEntry {
  ship_name: string;
  ship_class: string;
  weapon_name: string | null;
  weapon_class: string | null;
  range: string;
  damage_type: string | null;
  pilot_count: number;
  engagements: number;
  total_damage: number;
}

export interface AllianceFleetSize {
  avg: number | null;
  median: number | null;
  max: number | null;
  kills_sampled: number;
}

export interface AllianceLoadout {
  alliance_id: number;
  alliance_name: string;
  total_damage: number;
  pilot_count: number;
  fleet_size: AllianceFleetSize | null;
  loadouts: LoadoutEntry[];
}

export interface AttackerLoadoutsResponse {
  battle_id: number;
  alliances: AllianceLoadout[];
}

// ==================== Active Battles Response ====================

export interface ActiveBattlesResponse {
  battles: ActiveBattle[];
  total_active: number;
}

// Backend CamelModel returns camelCase keys, but frontend expects snake_case
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeBattle(raw: any): ActiveBattle {
  return {
    battle_id: raw.battleId ?? raw.battle_id,
    system_id: raw.systemId ?? raw.solarSystemId ?? raw.system_id,
    system_name: raw.systemName ?? raw.solarSystemName ?? raw.system_name,
    region_name: raw.regionName ?? raw.region_name,
    security: raw.security ?? 0,
    total_kills: raw.totalKills ?? raw.total_kills ?? 0,
    total_isk_destroyed: raw.totalIskDestroyed ?? raw.total_isk_destroyed ?? 0,
    last_milestone: raw.lastMilestone ?? raw.last_milestone ?? 0,
    started_at: raw.startedAt ?? raw.started_at,
    last_kill_at: raw.lastKillAt ?? raw.last_kill_at,
    duration_minutes: raw.durationMinutes ?? raw.duration_minutes ?? 0,
    telegram_sent: raw.telegramSent ?? raw.telegram_sent ?? false,
    intensity: raw.intensity ?? 'low',
    status_level: raw.statusLevel ?? raw.status_level,
  };
}

// ==================== Battle Events Types ====================

export interface BattleEvent {
  id: number;
  event_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string | null;
  system_id: number | null;
  system_name: string | null;
  region_id: number | null;
  region_name: string | null;
  alliance_id: number | null;
  alliance_name: string | null;
  event_data: Record<string, unknown>;
  detected_at: string;
  event_time: string | null;
}

export interface BattleEventResponse {
  events: BattleEvent[];
  total: number;
  since: string | null;
}

// ==================== Battle API ====================

export const battleApi = {
  getActiveBattles: async (limit = 10, minutes?: number): Promise<ActiveBattlesResponse> => {
    const { data } = await api.get('/war/battles/active', { params: { limit, minutes } });
    return {
      ...data,
      battles: (data.battles || []).map(normalizeBattle),
    };
  },

  getBattleEvents: async (limit?: number): Promise<BattleEventResponse> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    const response = await api.get(`/events/battle?${params}`);
    return response.data;
  },

  getLastSupercaps: async (): Promise<Record<string, {
    title: string;
    description: string;
    system_name: string;
    region_name: string;
    alliance_name: string;
    event_time: string | null;
    event_data: Record<string, unknown>;
  }>> => {
    const response = await api.get('/events/battle/last-supercaps');
    return response.data;
  },

  getBattle: async (battleId: number): Promise<ActiveBattle> => {
    const { data } = await api.get(`/war/battle/${battleId}`);
    return normalizeBattle(data);
  },

  getRecentTelegramAlerts: async (limit = 5) => {
    const { data } = await api.get('/war/telegram/recent', { params: { limit } });
    return data;
  },

  getLiveKills: async (systemId: number, limit = 20) => {
    const { data } = await api.get('/war/live/kills', { params: { system_id: systemId, limit } });
    return data;
  },

  getSystemKills: async (systemId: number, limit = 500, minutes = 1440) => {
    const { data } = await api.get(`/war/system/${systemId}/kills`, { params: { limit, minutes } });
    return data;
  },

  getBattleKills: async (battleId: number, limit = 500) => {
    const { data } = await api.get(`/war/battle/${battleId}/kills`, { params: { limit } });
    return data;
  },

  getBattleShipClasses: async (battleId: number, groupBy = 'category') => {
    const { data } = await api.get(`/war/battle/${battleId}/ship-classes`, {
      params: { group_by: groupBy }
    });
    return data;
  },

  getBattleParticipants: async (battleId: number) => {
    const { data } = await api.get(`/war/battle/${battleId}/participants`);
    return data;
  },

  getBattleTimeline: async (battleId: number, bucketSizeSeconds = 60): Promise<BattleTimelineResponse> => {
    const { data } = await api.get(`/war/battle/${battleId}/timeline`, {
      params: { bucket_size_seconds: bucketSizeSeconds }
    });
    return data;
  },

  getBattleReshipments: async (battleId: number): Promise<BattleReshipmentResponse> => {
    const response = await api.get(`/war/battle/${battleId}/reshipments`);
    return response.data;
  },

  getBattleSides: async (battleId: number): Promise<BattleSidesResponse> => {
    const { data } = await api.get(`/war/battle/${battleId}/sides`);
    return data;
  },

  getCommanderIntel: async (battleId: number): Promise<CommanderIntelResponse> => {
    const { data } = await api.get(`/war/battle/${battleId}/commander-intel`);
    return data;
  },

  getDamageAnalysis: async (battleId: number): Promise<DamageAnalysisResponse> => {
    const { data } = await api.get(`/war/battle/${battleId}/damage-analysis`);
    return data;
  },

  getVictimTankAnalysis: async (battleId: number): Promise<VictimTankAnalysisResponse> => {
    const { data } = await api.get(`/war/battle/${battleId}/victim-tank-analysis`);
    return data;
  },

  getStrategicContext: async (battleId: number): Promise<StrategicContextResponse> => {
    const { data } = await api.get(`/war/battle/${battleId}/strategic-context`);
    return data;
  },

  getAttackerLoadouts: async (battleId: number): Promise<AttackerLoadoutsResponse> => {
    const { data } = await api.get(`/war/battle/${battleId}/attacker-loadouts`);
    return data;
  },

  getSystemDanger: async (systemId: number, minutes = 1440) => {
    const { data } = await api.get(`/war/system/${systemId}/danger`, { params: { minutes } });
    return data;
  },

  getSystemShipClasses: async (systemId: number, hours = 24, groupBy = 'category') => {
    const { data } = await api.get(`/war/system/${systemId}/ship-classes`, {
      params: { hours, group_by: groupBy }
    });
    return data;
  },

  getMapSystems: async () => {
    const { data } = await api.get('/war/map/systems');
    return data;
  },
};

// ==================== War API (Timezone, Conflicts & Economy) ====================

export const warApi = {
  // Timezone Heatmap
  getTimezoneHeatmap: async (params?: {
    days_back?: number;
    alliance_id?: number;
    region_id?: number;
  }): Promise<TimezoneHeatmapResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.days_back) queryParams.append('days_back', params.days_back.toString());
    if (params?.alliance_id) queryParams.append('alliance_id', params.alliance_id.toString());
    if (params?.region_id) queryParams.append('region_id', params.region_id.toString());

    const query = queryParams.toString();
    const response = await api.get(`/war/timezone-heatmap${query ? `?${query}` : ''}`);
    return response.data;
  },

  getTimezoneAlliances: async (params?: { days_back?: number; limit?: number }) => {
    const queryParams = new URLSearchParams();
    if (params?.days_back) queryParams.append('days_back', params.days_back.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    const query = queryParams.toString();
    const response = await api.get(`/war/timezone-heatmap/alliances${query ? `?${query}` : ''}`);
    return response.data;
  },

  // Coalition Conflicts
  getConflicts: async (minutes: number = 60): Promise<ConflictsResponse> => {
    const { data } = await api.get('/war/conflicts', { params: { minutes } });
    return data;
  },

  // ==================== War Analytics ====================

  // War Summary (kills, ISK, active systems, capital kills)
  getWarSummary: async (hours: number = 24): Promise<{
    period_hours: number;
    total_kills: number;
    total_isk_destroyed: number;
    active_systems: number;
    capital_kills: number;
    generated_at: string;
  }> => {
    const response = await api.get('/war/summary', { params: { hours } });
    return response.data;
  },

  // Top Destroyed Ships
  getTopShips: async (hours: number = 24, limit: number = 20): Promise<Array<{
    ship_type_id: number;
    ship_name: string | null;
    ship_class: string | null;
    destroyed_count: number;
    total_value: number;
  }>> => {
    const response = await api.get('/war/top-ships', { params: { hours, limit } });
    return response.data;
  },

  // Kill Heatmap (per-system kill data)
  getHeatmap: async (days: number = 7, minKills: number = 5): Promise<{
    systems: Array<{
      solar_system_id: number;
      system_name: string | null;
      region_name: string | null;
      security: number;
      kill_count: number;
      total_value: number;
      capital_kills: number;
    }>;
    period_days: number;
    generated_at: string;
  }> => {
    const response = await api.get('/war/heatmap', { params: { days, min_kills: minKills } });
    return response.data;
  },

  // Hot Systems with Sovereignty Data (for Battlefield view)
  getHotSystems: async (minutes: number = 60, limit: number = 10): Promise<{
    minutes: number;
    systems: Array<{
      solar_system_id: number;
      system_name: string;
      region_name: string;
      security_status: number;
      kill_count: number;
      total_value: number;
      capital_kills: number;
      last_kill_minutes_ago: number | null;
      threat_level: 'critical' | 'hot' | 'active' | 'low';
      sov_alliance_id: number | null;
      sov_alliance_name: string | null;
      sov_alliance_ticker: string | null;
    }>;
    generated_at: string;
  }> => {
    const response = await api.get('/war/hot-systems', { params: { minutes, limit } });
    return response.data;
  },

  // ==================== War Economy Intelligence ====================
  // These are economy functions but kept in warApi for backwards compatibility

  // Capital Alliances (isotope-to-alliance correlation)
  getCapitalAlliances: async (days: number = 30): Promise<CapitalAlliancesResponse> => {
    const response = await api.get('/war/economy/capital-alliances', {
      params: { days }
    });
    return response.data;
  },

  // Capital Intelligence Dashboard
  getCapitalIntel: async (days: number = 30) => {
    const response = await api.get('/war/economy/capital-intel', { params: { days } });
    return response.data;
  },

  // Alliance-specific Capital Intel
  getAllianceCapitalIntel: async (allianceId: number, days: number = 30) => {
    const response = await api.get(`/war/economy/capital-intel/alliance/${allianceId}`, { params: { days } });
    return response.data;
  },

  // Alliance Capital Detail (extended with corp breakdown and regional activity)
  getCapitalAllianceDetail: async (allianceId: number, days: number = 30): Promise<AllianceCapitalDetailExtended> => {
    const { data } = await api.get(`/war/economy/capital-intel/alliance/${allianceId}`, { params: { days } });
    return data;
  },

  // Fuel Market Trends (isotope tracking for capital movement prediction)
  getFuelTrends: async (regionId: number, hours: number = 24): Promise<FuelTrendsResponse> => {
    const response = await api.get('/war/economy/fuel/trends', {
      params: { region_id: regionId, hours }
    });
    return response.data;
  },

  // Supercapital Construction Timers
  getSupercapTimers: async (regionId?: number): Promise<SupercapTimersResponse> => {
    const params: Record<string, number> = {};
    if (regionId) params.region_id = regionId;
    const response = await api.get('/war/economy/supercap-timers', { params });
    return response.data;
  },

  // Market Manipulation Detection
  getManipulationAlerts: async (regionId: number, hours: number = 24): Promise<ManipulationAlertsResponse> => {
    const response = await api.get('/war/economy/manipulation', {
      params: { region_id: regionId, hours }
    });
    return response.data;
  },
};

export default api;
