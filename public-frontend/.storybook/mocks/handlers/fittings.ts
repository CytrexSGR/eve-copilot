import { http, HttpResponse } from 'msw';
import {
  mockESIFittings,
  mockCustomFittings,
  mockDrakeDetail,
  mockMuninnDetail,
  mockGilaDetail,
  mockJackdawDetail,
  mockVedmakDetail,
  mockThanatosDetail,
  mockDrakeSummary,
  mockMuninnSummary,
  mockGilaSummary,
  mockJackdawSummary,
  mockVedmakSummary,
  mockThanatosSummary,
  mockShipGroups,
  mockModules,
  mockModuleGroups,
  mockCharges,
  mockMarketTreeChildren,
  mockDrakeStats,
  mockMuninnStats,
  mockJackdawStats,
  mockVedmakStats,
  mockThanatosStats,
  mockJackdawModes,
  mockTypeNames,
  mockBoostPresets,
  mockProjectedPresets,
  mockJumpShips,
  mockJumpRange,
  mockJumpRoute,
  mockShoppingLists,
  mockShoppingItems,
  mockCargoSummary,
  mockFreightRoutes,
  mockFreightCalculation,
  DRAKE_TYPE_ID,
  MUNINN_TYPE_ID,
  GILA_TYPE_ID,
  JACKDAW_TYPE_ID,
  VEDMAK_TYPE_ID,
  THANATOS_TYPE_ID,
} from '../data/fittings';

import type { ShipDetail, FittingStats } from '../../../src/types/fittings';

/**
 * MSW handlers for Fittings, Navigation, and Shopping API endpoints.
 */
export const fittingsHandlers = [
  // ── SDE Browser ─────────────────────────────────
  http.get('/api/sde/ships', ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search')?.toLowerCase();
    const ships = [mockDrakeSummary, mockMuninnSummary, mockGilaSummary, mockJackdawSummary, mockVedmakSummary, mockThanatosSummary];
    if (search) {
      return HttpResponse.json(ships.filter(s => s.type_name.toLowerCase().includes(search)));
    }
    return HttpResponse.json(ships);
  }),

  http.get('/api/sde/ship-groups', () => {
    return HttpResponse.json(mockShipGroups);
  }),

  http.get('/api/sde/ships/:typeId', ({ params }) => {
    const typeId = Number(params.typeId);
    const map: Record<number, ShipDetail> = {
      [DRAKE_TYPE_ID]: mockDrakeDetail,
      [MUNINN_TYPE_ID]: mockMuninnDetail,
      [GILA_TYPE_ID]: mockGilaDetail,
      [JACKDAW_TYPE_ID]: mockJackdawDetail,
      [VEDMAK_TYPE_ID]: mockVedmakDetail,
      [THANATOS_TYPE_ID]: mockThanatosDetail,
    };
    return HttpResponse.json(map[typeId] || mockDrakeDetail);
  }),

  http.get('/api/sde/modules', ({ request }) => {
    const url = new URL(request.url);
    const slotType = url.searchParams.get('slot_type');
    const search = url.searchParams.get('search')?.toLowerCase();
    let results = mockModules;
    if (slotType) {
      results = results.filter(m => m.slot_type === slotType);
    }
    if (search) {
      results = results.filter(m => m.name.toLowerCase().includes(search));
    }
    return HttpResponse.json(results);
  }),

  http.get('/api/sde/module-groups', ({ request }) => {
    const url = new URL(request.url);
    const slotType = url.searchParams.get('slot_type');
    if (slotType) {
      const slotModules = mockModules.filter(m => m.slot_type === slotType);
      const groups = new Map<string, number>();
      slotModules.forEach(m => {
        groups.set(m.group_name, (groups.get(m.group_name) || 0) + 1);
      });
      return HttpResponse.json(
        Array.from(groups.entries()).map(([name, count], i) => ({
          group_id: 500 + i,
          group_name: name,
          count,
        }))
      );
    }
    return HttpResponse.json(mockModuleGroups);
  }),

  http.get('/api/sde/charges', () => {
    return HttpResponse.json(mockCharges);
  }),

  http.get('/api/sde/market-tree/children', () => {
    return HttpResponse.json(mockMarketTreeChildren);
  }),

  http.get('/api/sde/market-tree/items', () => {
    return HttpResponse.json(mockModules.slice(0, 5));
  }),

  http.get('/api/sde/modes/:shipTypeId', ({ params }) => {
    const shipTypeId = Number(params.shipTypeId);
    if (shipTypeId === JACKDAW_TYPE_ID) {
      return HttpResponse.json(mockJackdawModes);
    }
    return HttpResponse.json([]);
  }),

  http.post('/api/sde/resolve-names', async ({ request }) => {
    const names = await request.json() as string[];
    return HttpResponse.json(
      names.map(name => {
        const entry = Object.entries(mockTypeNames).find(([, v]) => v.toLowerCase() === name.toLowerCase());
        return { type_id: entry ? Number(entry[0]) : 0, type_name: name };
      })
    );
  }),

  // ── Type Names (Dogma) ──────────────────────────
  http.get('/api/dogma/types/names', ({ request }) => {
    const url = new URL(request.url);
    const ids = url.searchParams.get('ids')?.split(',') || [];
    const types: Record<string, string> = {};
    ids.forEach(id => {
      types[id] = mockTypeNames[id] || `Type #${id}`;
    });
    return HttpResponse.json({ types });
  }),

  // ── Fittings CRUD ───────────────────────────────

  // GET /api/fittings/esi/:characterId — return ESI fittings for a character
  http.get('/api/fittings/esi/:characterId', () => {
    return HttpResponse.json(mockESIFittings);
  }),

  // GET /api/fittings/:characterId — return ESI fittings for a character
  http.get('/api/fittings/:characterId', () => {
    return HttpResponse.json(mockESIFittings);
  }),

  // POST /api/fittings/stats — return stats based on ship_type_id in request body
  http.post('/api/fittings/stats', async ({ request }) => {
    const body = await request.json() as { ship_type_id?: number };
    const shipTypeId = body?.ship_type_id;
    const statsMap: Record<number, FittingStats> = {
      [DRAKE_TYPE_ID]: mockDrakeStats,
      [MUNINN_TYPE_ID]: mockMuninnStats,
      [JACKDAW_TYPE_ID]: mockJackdawStats,
      [VEDMAK_TYPE_ID]: mockVedmakStats,
      [THANATOS_TYPE_ID]: mockThanatosStats,
    };
    return HttpResponse.json(statsMap[shipTypeId ?? 0] || mockDrakeStats);
  }),

  // GET /api/fittings/shared — return shared/public fittings
  http.get('/api/fittings/shared', () => {
    return HttpResponse.json(mockCustomFittings);
  }),

  http.get('/api/fittings/custom/:characterId', () => {
    return HttpResponse.json(mockCustomFittings);
  }),

  http.get('/api/fittings/detail/:fittingId', ({ params }) => {
    const fittingId = Number(params.fittingId);
    const found = mockCustomFittings.find(f => f.id === fittingId);
    return HttpResponse.json(found || mockCustomFittings[0]);
  }),

  http.post('/api/fittings/save', () => {
    return HttpResponse.json(mockCustomFittings[0]);
  }),

  http.put('/api/fittings/custom/:id', () => {
    return HttpResponse.json(mockCustomFittings[0]);
  }),

  // POST /api/fittings/compare — return comparison data for 2-4 fittings
  http.post('/api/fittings/compare', async ({ request }) => {
    const body = await request.json() as { fittings: Array<{ ship_type_id: number }> };
    const statsMap: Record<number, FittingStats> = {
      [DRAKE_TYPE_ID]: mockDrakeStats,
      [MUNINN_TYPE_ID]: mockMuninnStats,
      [JACKDAW_TYPE_ID]: mockJackdawStats,
      [VEDMAK_TYPE_ID]: mockVedmakStats,
      [THANATOS_TYPE_ID]: mockThanatosStats,
    };
    const comparisons = (body?.fittings || []).map(f => statsMap[f.ship_type_id] || mockDrakeStats);
    return HttpResponse.json({ comparisons });
  }),

  // ── Boost & Projected ───────────────────────────
  http.get('/api/fittings/boost-presets', () => {
    return HttpResponse.json(mockBoostPresets);
  }),

  http.get('/api/fittings/boost-definitions', () => {
    return HttpResponse.json({});
  }),

  http.get('/api/fittings/projected-presets', () => {
    return HttpResponse.json(mockProjectedPresets);
  }),

  // ── Jump Planner ────────────────────────────────
  http.get('/api/jump/ships', () => {
    return HttpResponse.json({ ships: mockJumpShips });
  }),

  http.get('/api/jump/range/:shipName', () => {
    return HttpResponse.json(mockJumpRange);
  }),

  http.get('/api/jump/route', () => {
    return HttpResponse.json(mockJumpRoute);
  }),

  http.get('/api/jump/fatigue', () => {
    return HttpResponse.json({
      distance_ly: 8.5,
      current_fatigue_minutes: 0,
      new_fatigue_minutes: 60,
      blue_timer_minutes: 10,
      red_timer_minutes: 60,
      fatigue_capped: false,
      time_until_jump: 0,
      time_until_fatigue_clear: 3600,
    });
  }),

  // ── Shopping Lists ──────────────────────────────
  http.get('/api/shopping/lists', () => {
    return HttpResponse.json(mockShoppingLists);
  }),

  http.get('/api/shopping/lists/:listId', () => {
    return HttpResponse.json(mockShoppingLists[0]);
  }),

  http.get('/api/shopping/lists/:listId/items', () => {
    return HttpResponse.json(mockShoppingItems);
  }),

  http.post('/api/shopping/lists', () => {
    return HttpResponse.json(mockShoppingLists[0]);
  }),

  http.post('/api/shopping/lists/:listId/items', () => {
    return HttpResponse.json(mockShoppingItems[0]);
  }),

  http.get('/api/shopping/lists/:listId/cargo-summary', () => {
    return HttpResponse.json(mockCargoSummary);
  }),

  http.get('/api/shopping/lists/:listId/export', () => {
    return HttpResponse.json('Drake x3\nHeavy Missile Launcher II x21');
  }),

  // ── Freight Calculator ──────────────────────────
  http.get('/api/shopping/freight/routes', () => {
    return HttpResponse.json({ routes: mockFreightRoutes, count: mockFreightRoutes.length });
  }),

  http.post('/api/shopping/freight/calculate', () => {
    return HttpResponse.json(mockFreightCalculation);
  }),

  // ── Production Projects (for FittingDetail's Create Project) ──
  http.post('/api/production/projects', () => {
    return HttpResponse.json({ id: 42, name: 'Mock Project', status: 'draft' });
  }),

  http.post('/api/production/projects/:projectId/items', () => {
    return HttpResponse.json({ id: 1, type_id: DRAKE_TYPE_ID, quantity: 1 });
  }),

  // ── Market search (for Production page) ──
  http.get('/api/market/search', ({ request }) => {
    const url = new URL(request.url);
    const q = url.searchParams.get('q')?.toLowerCase() || '';
    const results = [
      { typeID: DRAKE_TYPE_ID, typeName: 'Drake', groupName: 'Battlecruiser' },
      { typeID: MUNINN_TYPE_ID, typeName: 'Muninn', groupName: 'Heavy Assault Cruiser' },
    ].filter(i => i.typeName.toLowerCase().includes(q));
    return HttpResponse.json({ results });
  }),

  http.get('/api/market/detail/:typeId', ({ params }) => {
    const typeId = Number(params.typeId);
    return HttpResponse.json({
      typeID: typeId,
      typeName: mockTypeNames[String(typeId)] || 'Unknown',
      groupName: 'Ship',
      categoryName: 'Ship',
      volume: 15000,
    });
  }),

  // ── Bulk Prices (for PlannerTab) ──
  http.post('/api/market/prices/bulk', () => {
    return HttpResponse.json({
      '34': { sell_price: 5.82, buy_price: 5.50 },
      '35': { sell_price: 9.15, buy_price: 8.80 },
      '36': { sell_price: 62.50, buy_price: 60.00 },
      '37': { sell_price: 58.90, buy_price: 56.00 },
      '38': { sell_price: 520.00, buy_price: 500.00 },
    });
  }),

  http.get('/api/market/prices/bulk', ({ request }) => {
    const url = new URL(request.url);
    url.searchParams.get('type_ids');
    return HttpResponse.json({
      '34': { sell_price: 5.82, buy_price: 5.50 },
      '35': { sell_price: 9.15, buy_price: 8.80 },
      '36': { sell_price: 62.50, buy_price: 60.00 },
    });
  }),

  // ── Project Decisions (for PlannerTab in project context) ──
  http.get('/api/production/projects/:projectId/items/:itemId/decisions', () => {
    return HttpResponse.json([]);
  }),
];
