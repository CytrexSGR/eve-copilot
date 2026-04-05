import { http, HttpResponse } from 'msw';
import {
  mockWormholeSummary,
  mockThreats,
  mockEvictions,
} from '../data/wormhole';

/**
 * MSW handlers for Wormhole Intel API endpoints.
 */
export const wormholeHandlers = [
  // GET /api/wormhole/summary
  http.get('/api/wormhole/summary', () => {
    return HttpResponse.json({
      summary: mockWormholeSummary,
      threats: mockThreats,
      evictions: mockEvictions,
    });
  }),

  // GET /api/wormhole/threats
  http.get('/api/wormhole/threats', () => {
    return HttpResponse.json(mockThreats);
  }),

  // GET /api/wormhole/evictions
  http.get('/api/wormhole/evictions', () => {
    return HttpResponse.json(mockEvictions);
  }),

  // GET /api/wormhole/hunters
  http.get('/api/wormhole/hunters', () => {
    return HttpResponse.json({
      hunters: [
        { alliance_id: 99005065, name: 'Hard Knocks Inc.', kills: 142, systems_active: 28 },
        { alliance_id: 99008225, name: 'Wingspan Delivery Network', kills: 89, systems_active: 45 },
        { alliance_id: 99007235, name: 'Lazerhawks', kills: 67, systems_active: 18 },
      ],
    });
  }),

  // GET /api/wormhole/market
  http.get('/api/wormhole/market', () => {
    return HttpResponse.json({
      commodities: {
        gas: [
          { type_id: 30370, name: 'Fullerite-C320', tier: 'high', sell_price: 142000, buy_price: 138000, spread: 2.9, trend_7d: 5.2, trend_direction: 'up', daily_volume: 12500 },
          { type_id: 30371, name: 'Fullerite-C540', tier: 'high', sell_price: 89000, buy_price: 85000, spread: 4.5, trend_7d: -2.1, trend_direction: 'down', daily_volume: 8900 },
        ],
        blue_loot: [
          { type_id: 30744, name: 'Sleeper Data Library', tier: 'mid', sell_price: 200000, buy_price: 200000, spread: 0, trend_7d: 0, trend_direction: 'stable', daily_volume: 45000 },
        ],
        polymers: [],
        updated_at: '2026-02-20T22:00:00Z',
      },
    });
  }),

  // GET /api/wormhole/thera/routes
  http.get('/api/wormhole/thera/routes', () => {
    return HttpResponse.json({
      routes: [
        { from: 'K-6K16', to: 'Jita', direct_jumps: 42, thera_jumps: 18, savings: 24, entry_wh: 'E-VKJV', exit_wh: 'Raih' },
      ],
    });
  }),
];
