// Reports-related API functions
import { api } from './client';
import type { BattleReport } from '../../types/battle';
import type { PowerBlocComplete } from '../../types/powerbloc';
import type {
  WarProfiteering,
  TradeRoutes,
  WarEconomy,
  WarEconomyAnalysis,
} from '../../types/economy';
import type {
  AllianceWars,
  AllianceWarsAnalysis,
  StrategicBriefing,
  PowerAssessment,
} from '../../types/reports';

// API client imported from ./client

// ==================== Reports API ====================

export const reportsApi = {
  getBattleReport: async (): Promise<BattleReport> => {
    const { data } = await api.get('/reports/battle-24h');
    return data;
  },

  getWarProfiteering: async (): Promise<WarProfiteering> => {
    const { data } = await api.get('/reports/war-profiteering');
    return data;
  },

  getAllianceWars: async (): Promise<AllianceWars> => {
    const { data } = await api.get('/reports/alliance-wars');
    return data;
  },

  getPowerBlocsLive: async (minutes: number = 1440): Promise<{ coalitions: AllianceWars['coalitions']; minutes: number; timeframe: string }> => {
    const { data } = await api.get('/reports/power-blocs/live', { params: { minutes } });
    return data;
  },

  getPowerBlocDetail: async (leaderAllianceId: number, minutes: number = 10080): Promise<PowerBlocComplete> => {
    const { data } = await api.get(`/reports/powerbloc/${leaderAllianceId}`, { params: { minutes } });
    return data;
  },

  getAllianceWarsAnalysis: async (): Promise<AllianceWarsAnalysis> => {
    const { data } = await api.get('/reports/alliance-wars/analysis');
    return data;
  },

  getStrategicBriefing: async (): Promise<StrategicBriefing> => {
    const { data } = await api.get('/reports/strategic-briefing');
    return data;
  },

  getPowerAssessment: async (minutes: number = 1440): Promise<PowerAssessment & { minutes: number; timeframe: string }> => {
    const { data } = await api.get('/reports/power-assessment', { params: { minutes } });
    return data;
  },

  getTradeRoutes: async (minutes?: number): Promise<TradeRoutes & { minutes?: number }> => {
    // Use live endpoint for dynamic time periods, cached endpoint for default 24h
    if (minutes && minutes !== 1440) {
      const { data } = await api.get('/reports/trade-routes/live', { params: { minutes, limit: 10 } });
      return data;
    }
    const { data } = await api.get('/reports/trade-routes', { params: { limit: 10 } });
    return data;
  },

  getWarEconomy: async (): Promise<WarEconomy> => {
    const { data } = await api.get('/reports/war-economy');
    return data;
  },

  getWarEconomyAnalysis: async (): Promise<WarEconomyAnalysis> => {
    const { data } = await api.get('/reports/war-economy/analysis');
    return data;
  },

  getHealth: async () => {
    const { data } = await api.get('/health');
    return data;
  }
};

// ==================== Standalone Functions ====================

export async function getBattleReport(): Promise<BattleReport> {
  return reportsApi.getBattleReport();
}

export async function getWarProfiteering(): Promise<WarProfiteering> {
  return reportsApi.getWarProfiteering();
}

export async function getAllianceWars(): Promise<AllianceWars> {
  return reportsApi.getAllianceWars();
}

export async function getAllianceWarsAnalysis(): Promise<AllianceWarsAnalysis> {
  return reportsApi.getAllianceWarsAnalysis();
}

export async function getStrategicBriefing(): Promise<StrategicBriefing> {
  return reportsApi.getStrategicBriefing();
}

export async function getPowerAssessment(minutes: number = 1440): Promise<PowerAssessment & { minutes: number; timeframe: string }> {
  return reportsApi.getPowerAssessment(minutes);
}

export async function getTradeRoutes(minutes?: number): Promise<TradeRoutes & { minutes?: number }> {
  return reportsApi.getTradeRoutes(minutes);
}

export async function getWarEconomy(): Promise<WarEconomy> {
  return reportsApi.getWarEconomy();
}

export async function getWarEconomyAnalysis(): Promise<WarEconomyAnalysis> {
  return reportsApi.getWarEconomyAnalysis();
}

export async function getHealth() {
  return reportsApi.getHealth();
}

export default api;
