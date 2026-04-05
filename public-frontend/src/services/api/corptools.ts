import { createApiClient } from './client';
import type {
  ContractActiveResponse, ContractStatsResponse, CourierAnalysisResponse,
  ContractChange, DiscordRelay, DiscordRelayCreate, DiscordRelayUpdate,
} from '../../types/corptools';

const contractApi = createApiClient('/api/corp-contracts');
const militaryApi = createApiClient('/api/military');

export const contractsApi = {
  getActive: async (corpId: number, contractType?: string): Promise<ContractActiveResponse> => {
    const { data } = await contractApi.get(`/active/${corpId}`, {
      params: contractType ? { contract_type: contractType } : undefined,
    });
    return data;
  },

  getStats: async (corpId: number, days = 30): Promise<ContractStatsResponse> => {
    const { data } = await contractApi.get(`/stats/${corpId}`, { params: { days } });
    return data;
  },

  getCourier: async (corpId: number, days = 30): Promise<CourierAnalysisResponse> => {
    const { data } = await contractApi.get(`/courier/${corpId}`, { params: { days } });
    return data;
  },

  getChanges: async (corpId: number, hours = 24): Promise<{ corporationId: number; hours: number; count: number; changes: ContractChange[] }> => {
    const { data } = await contractApi.get(`/changes/${corpId}`, { params: { hours } });
    return data;
  },
};

export const discordApi = {
  getRelays: async (activeOnly = false): Promise<DiscordRelay[]> => {
    const { data } = await militaryApi.get('/discord/relays', { params: { active_only: activeOnly } });
    return Array.isArray(data) ? data : [];
  },

  createRelay: async (req: DiscordRelayCreate): Promise<DiscordRelay> => {
    const { data } = await militaryApi.post('/discord/relays', req);
    return data;
  },

  updateRelay: async (relayId: number, updates: DiscordRelayUpdate): Promise<DiscordRelay> => {
    const { data } = await militaryApi.put(`/discord/relays/${relayId}`, updates);
    return data;
  },

  deleteRelay: async (relayId: number): Promise<{ message: string; id: number }> => {
    const { data } = await militaryApi.delete(`/discord/relays/${relayId}`);
    return data;
  },

  testRelay: async (relayId: number): Promise<{ success: boolean; message: string; detail?: string }> => {
    const { data } = await militaryApi.post(`/discord/relays/test/${relayId}`);
    return data;
  },
};
