// Killmail Intelligence API functions
import { createApiClient } from './client';
import type {
  ThreatComposition,
  CapitalRadar,
  HuntingScores,
  PilotRiskData,
  CorpHealth,
} from '../../types/intelligence';

const api = createApiClient('/api/intelligence');

export const intelligenceApi = {
  // Defensive Tab
  getThreats: async (entityType: string, entityId: number, days = 30): Promise<ThreatComposition> => {
    const { data } = await api.get(`/threats/${entityType}/${entityId}`, { params: { days } });
    return data;
  },

  getCapitalRadar: async (entityType: string, entityId: number, days = 30): Promise<CapitalRadar> => {
    const { data } = await api.get(`/capital-radar/${entityType}/${entityId}`, { params: { days } });
    return data;
  },

  getLogiScores: async (entityType: string, entityId: number, days = 30) => {
    const { data } = await api.get(`/logi-score/${entityType}/${entityId}`, { params: { days } });
    return data;
  },

  // Hunting Tab
  getHuntingScores: async (regionId?: number, days = 30, limit = 50): Promise<HuntingScores> => {
    const params: Record<string, number> = { days, limit };
    if (regionId) params.region_id = regionId;
    const { data } = await api.get('/hunting/scores', { params });
    return data;
  },

  // Pilots Tab
  getPilotRisk: async (corpId: number, days = 90): Promise<PilotRiskData> => {
    const { data } = await api.get(`/pilot-risk/${corpId}`, { params: { days } });
    return data;
  },

  getCorpHealth: async (corpId: number, days = 30): Promise<CorpHealth> => {
    const { data } = await api.get(`/corp-health/${corpId}`, { params: { days } });
    return data;
  },
};
