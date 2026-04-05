// Wormhole Service API functions
import { api } from './client';
import type {
  WormholeSummary,
  WormholeThreat,
  WormholeOpportunity,
  WormholeEviction,
  WormholeMarketSignals,
  WormholeActivity,
  CommodityPrices,
  EvictionIntel,
  SupplyDisruption,
  MarketIndex,
  PriceHistory,
  PriceContext,
} from '../../types/wormhole';
import type {
  TheraStatus,
  TheraConnectionList,
  TheraRoute,
  ShipSize,
  HubType,
} from '../../types/thera';

// API client imported from ./client

// ==================== Wormhole API ====================

export const wormholeApi = {
  getSummary: async (): Promise<WormholeSummary> => {
    const { data } = await api.get('/wormhole/stats/summary');
    return data;
  },

  getThreats: async (whClass?: number, limit = 20): Promise<{ count: number; threats: WormholeThreat[] }> => {
    const params = new URLSearchParams();
    if (whClass) params.set('wh_class', whClass.toString());
    params.set('limit', limit.toString());
    const { data } = await api.get(`/wormhole/threats?${params}`);
    return data;
  },

  getOpportunities: async (
    whClass?: number,
    minActivity = 3,
    limit = 20
  ): Promise<{ count: number; opportunities: WormholeOpportunity[] }> => {
    const params = new URLSearchParams();
    if (whClass) params.set('wh_class', whClass.toString());
    params.set('min_activity', minActivity.toString());
    params.set('limit', limit.toString());
    const { data } = await api.get(`/wormhole/opportunities?${params}`);
    return data;
  },

  getEvictions: async (days = 30): Promise<{ count: number; evictions: WormholeEviction[] }> => {
    const { data } = await api.get(`/wormhole/evictions?days=${days}`);
    return data;
  },

  getMarketSignals: async (days = 7): Promise<WormholeMarketSignals> => {
    const { data } = await api.get(`/wormhole/market/signals?days=${days}`);
    return data;
  },

  getCommodityPrices: async (): Promise<CommodityPrices> => {
    const { data } = await api.get('/wormhole/market/commodities');
    return data;
  },

  getEvictionIntel: async (days = 7): Promise<EvictionIntel[]> => {
    const { data } = await api.get(`/wormhole/market/eviction-intel?days=${days}`);
    return data;
  },

  getSupplyDisruptions: async (days = 7): Promise<SupplyDisruption[]> => {
    const { data } = await api.get(`/wormhole/market/disruptions?days=${days}`);
    return data;
  },

  getMarketIndex: async (): Promise<MarketIndex> => {
    const { data } = await api.get('/wormhole/market/index');
    return data;
  },

  getPriceHistory: async (days = 7): Promise<PriceHistory> => {
    const { data } = await api.get(`/wormhole/market/price-history?days=${days}`);
    return data;
  },

  getPriceContext: async (): Promise<PriceContext> => {
    const { data } = await api.get('/wormhole/market/price-context');
    return data;
  },

  getActivity: async (
    whClass?: number,
    limit = 100
  ): Promise<{ count: number; systems: WormholeActivity[] }> => {
    const params = new URLSearchParams();
    if (whClass) params.set('wh_class', whClass.toString());
    params.set('limit', limit.toString());
    const { data } = await api.get(`/wormhole/activity?${params}`);
    return data;
  },

  searchSystem: async (query: string): Promise<{ systems: Array<{ system_id: number; system_name: string; wormhole_class: number }> }> => {
    const { data } = await api.get(`/wormhole/systems/search?q=${encodeURIComponent(query)}`);
    return data;
  },

  // ==================== Thera Router API ====================

  getTheraStatus: async (): Promise<TheraStatus> => {
    const { data } = await api.get('/route/thera/status');
    return data;
  },

  getTheraConnections: async (hub: HubType = 'thera'): Promise<TheraConnectionList> => {
    const { data } = await api.get(`/route/thera/connections?hub=${hub}`);
    return data;
  },

  calculateTheraRoute: async (
    fromSystem: string,
    toSystem: string,
    shipSize: ShipSize = 'large',
    hub: HubType = 'thera'
  ): Promise<TheraRoute> => {
    const { data } = await api.get(
      `/route/thera/${encodeURIComponent(fromSystem)}/${encodeURIComponent(toSystem)}?ship_size=${shipSize}&hub=${hub}`
    );
    return data;
  },
};

export default wormholeApi;
