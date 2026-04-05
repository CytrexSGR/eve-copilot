// Economy-related API functions
import { api } from './client';
import type {
  FuelTrendsResponse,
  SupercapTimersResponse,
  ManipulationAlertsResponse,
  EconomicOverview,
  DoctrineListResponse,
  ItemsListResponse,
  ReclusterResponse,
  ExtendedHotItemsResponse,
  WarzoneRoutesResponse,
  AllianceCapitalDetailExtended,
} from '../../types/economy';

// API client imported from ./client

// ==================== Capital Alliance Types ====================

export interface CapitalAllianceCorp {
  corporation_id: number;
  corporation_name: string;
  engagements: number;
  pilots: number;
  ships: string[];
}

export interface CapitalAllianceRegion {
  region: string;
  ops: number;
  hours_ago: number;
}

export interface CapitalAllianceInfo {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  capital_count: number;
  total_capitals: number;
  race_preference_pct: number;
  confidence_score: number;
  last_activity: string | null;
  top_corps: CapitalAllianceCorp[];
  active_regions: CapitalAllianceRegion[];
}

export interface CapitalAlliancesResponse {
  days_analyzed: number;
  by_race: {
    Minmatar: CapitalAllianceInfo[];
    Gallente: CapitalAllianceInfo[];
    Caldari: CapitalAllianceInfo[];
    Amarr: CapitalAllianceInfo[];
  };
  by_isotope: Record<number, {
    race: string;
    alliances: CapitalAllianceInfo[];
  }>;
}

// ==================== Doctrine API ====================

export const doctrineApi = {
  getDoctrineTemplates: async (
    limit = 50,
    offset = 0,
    regionId?: number,
    since?: string
  ): Promise<DoctrineListResponse> => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (regionId) params.append('region_id', regionId.toString());
    if (since) params.append('since', since);

    const response = await api.get(`/war/economy/doctrines?${params}`);
    return response.data;
  },

  getDoctrineItems: async (doctrineId: number): Promise<ItemsListResponse> => {
    const response = await api.get(`/war/economy/doctrines/${doctrineId}/items`);
    return response.data;
  },

  getDoctrineItemsWithMaterials: async (doctrineId: number) => {
    const response = await api.get(`/war/economy/doctrines/${doctrineId}/items/materials`);
    return response.data;
  },

  triggerRecluster: async (hoursBack = 168): Promise<ReclusterResponse> => {
    const response = await api.post('/war/economy/doctrines/recluster', {
      hours_back: hoursBack,
    });
    return response.data;
  }
};

// ==================== War Economy API ====================

export const warEconomyApi = {
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

  // Regional Economic Overview (combined intelligence)
  getEconomicOverview: async (regionId: number): Promise<EconomicOverview> => {
    const response = await api.get(`/war/economy/overview/${regionId}`);
    return response.data;
  },

  // Extended Hot Items (with regional prices and trends)
  getExtendedHotItems: async (limit: number = 10): Promise<ExtendedHotItemsResponse> => {
    const { data } = await api.get('/war/economy/hot-items-extended', { params: { limit } });
    return data;
  },

  // Warzone Trade Routes
  getWarzoneRoutes: async (limit: number = 5): Promise<WarzoneRoutesResponse> => {
    const { data } = await api.get('/war/economy/warzone-routes', { params: { limit } });
    return data;
  },
};

// ==================== Standalone Functions ====================

export async function getExtendedHotItems(limit: number = 10): Promise<ExtendedHotItemsResponse> {
  return warEconomyApi.getExtendedHotItems(limit);
}

export async function getWarzoneRoutes(limit: number = 5): Promise<WarzoneRoutesResponse> {
  return warEconomyApi.getWarzoneRoutes(limit);
}

export default api;
