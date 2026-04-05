import { http, HttpResponse } from 'msw';
import {
  mockHotSystems,
  mockCapitalIntel,
  mockTradeRoutes,
} from '../data/war-economy';

/**
 * MSW handlers for war-economy tab components.
 * CombatTab fetches hot-systems + capital-intel via fetch().
 * RoutesTab fetches trade-routes via reportsApi.
 */
export const warEconomyHandlers = [
  // CombatTab: hot systems
  http.get('/api/war/hot-systems', () => {
    return HttpResponse.json(mockHotSystems);
  }),

  // CombatTab: capital intel
  http.get('/api/war/economy/capital-intel', () => {
    return HttpResponse.json(mockCapitalIntel);
  }),

  // RoutesTab: trade routes via reportsApi
  http.get('/api/reports/trade-routes', () => {
    return HttpResponse.json(mockTradeRoutes);
  }),
];
