import { api } from './client';
import type {
  MarketPrice, ItemSearchResult, ItemDetail, HotItemCategories,
  MarketStats, RegionalComparison, ArbitrageRoutesResponse,
  HunterScanResponse, HunterOpportunity, TradingOpportunity,
  PortfolioHistory, PortfolioSnapshot, AggregatedOrdersResponse,
  TradingPnLReport, TradingSummary,
} from '../../types/market';

export const marketApi = {
  // --- Existing (Phase A) ---
  searchItems: (q: string) =>
    api.get<{ results: ItemSearchResult[]; query: string; count: number }>(
      '/items/search', { params: { q } }
    ).then(r => r.data),

  getItemDetail: (typeId: number) =>
    api.get<ItemDetail>(`/items/${typeId}`).then(r => r.data),

  getPrice: (typeId: number, regionId = 10000002) =>
    api.get<MarketPrice>(
      `/market/price/${typeId}`, { params: { region_id: regionId } }
    ).then(r => r.data),

  getPricesBulk: (typeIds: number[], regionId = 10000002) =>
    api.post<Record<string, { type_id: number; sell_price: number; buy_price: number }>>(
      '/market/prices', { type_ids: typeIds, region_id: regionId }
    ).then(r => r.data),

  getHotItemsByCategory: (regionId = 10000002) =>
    api.get<HotItemCategories>(
      '/market/prices/hot-items/categories', { params: { region_id: regionId } }
    ).then(r => r.data),

  // --- Phase C: Stats ---
  getStats: (typeId: number, regionId = 10000002) =>
    api.get<MarketStats>(`/market/stats/${regionId}/${typeId}`).then(r => r.data),

  getRegionalComparison: (typeId: number) =>
    api.get<RegionalComparison>(`/market/compare/${typeId}`).then(r => r.data),

  getRawOrders: (typeId: number, regionId = 10000002, orderType = 'all') =>
    api.get<Array<Record<string, unknown>>>(
      `/market/orders/${typeId}`, { params: { region_id: regionId, order_type: orderType } }
    ).then(r => r.data),

  // --- Phase C: Arbitrage ---
  getArbitrageRoutes: (params: {
    start_region?: number;
    max_jumps?: number;
    min_profit_per_trip?: number;
    cargo_capacity?: number;
    turnover?: string;
    max_competition?: string;
    max_days_to_sell?: number;
    min_volume?: number;
  } = {}) =>
    api.get<ArbitrageRoutesResponse>('/market/routes', { params }).then(r => r.data),

  // --- Phase C: Hunter (Manufacturing Opportunities) ---
  getHunterCategories: () =>
    api.get<{ categories: Record<string, string[]>; total_items: number }>(
      '/hunter/categories'
    ).then(r => r.data),

  scanOpportunities: (params: {
    min_roi?: number;
    min_profit?: number;
    max_difficulty?: number;
    min_volume?: number;
    top?: number;
    category?: string;
    search?: string;
    sort_by?: string;
  } = {}) =>
    api.get<HunterScanResponse>('/hunter/scan', { params }).then(r => r.data),

  getQuickOpportunities: (params: {
    min_roi?: number;
    min_profit?: number;
    max_difficulty?: number;
    limit?: number;
  } = {}) =>
    api.get<{ results: HunterOpportunity[]; count: number }>(
      '/hunter/opportunities', { params }
    ).then(r => r.data),

  // --- Phase C: Trading Opportunities ---
  getTradingOpportunities: (params: {
    min_margin?: number;
    max_volume?: number;
    risk_level?: string;
  } = {}) =>
    api.get<{ results: TradingOpportunity[]; count: number }>(
      '/trading/opportunities', { params }
    ).then(r => r.data),
};

/** Trading analytics — requires character_id */
export const tradingApi = {
  getPnL: (characterId: number, days = 30) =>
    api.get<TradingPnLReport>(
      `/trading/${characterId}/pnl`, { params: { days } }
    ).then(r => r.data),

  getSummary: (characterId: number) =>
    api.get<TradingSummary>(`/trading/${characterId}/summary`).then(r => r.data),

  getVelocity: (characterId: number) =>
    api.get(`/trading/${characterId}/velocity`).then(r => r.data),

  getCompetition: (characterId: number) =>
    api.get(`/trading/${characterId}/competition`).then(r => r.data),

  getMarginAlerts: (characterId: number, threshold = 10) =>
    api.get(`/trading/${characterId}/margin-alerts`, { params: { threshold } }).then(r => r.data),
};

/** Portfolio tracking — requires character_id */
export const portfolioApi = {
  getHistory: (characterId: number, days = 30) =>
    api.get<PortfolioHistory>(
      `/portfolio/${characterId}/history`, { params: { days } }
    ).then(r => r.data),

  getLatest: (characterId: number) =>
    api.get<PortfolioSnapshot>(`/portfolio/${characterId}/latest`).then(r => r.data),

  getSummaryAll: () =>
    api.get<{ snapshots: PortfolioSnapshot[]; total_characters: number; combined_liquid: number }>(
      '/portfolio/summary/all'
    ).then(r => r.data),
};

/** Order aggregation — requires character_id */
export const ordersApi = {
  getAggregated: (characterIds?: number[], orderType?: string) =>
    api.get<AggregatedOrdersResponse>('/orders/aggregated', {
      params: {
        character_ids: characterIds?.join(','),
        order_type: orderType,
      },
    }).then(r => r.data),
};

/** Trading history */
export const historyApi = {
  getHistory: (characterId: number, days = 30) =>
    api.get(`/history/${characterId}`, { params: { days } }).then(r => r.data),

  getSummary: (characterId: number, days = 30) =>
    api.get(`/history/${characterId}/summary`, { params: { days } }).then(r => r.data),
};
