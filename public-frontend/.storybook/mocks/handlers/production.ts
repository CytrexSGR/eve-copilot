import { http, HttpResponse } from 'msw';
import {
  mockProductionSimulation,
  mockCompareResult,
  mockEconomicsOpportunities,
  mockDecryptorComparison,
  mockInventionDetail,
  mockReactionRequirements,
  mockPISchematicFormulas,
  mockPIProfitability,
  mockEmpireAnalysis,
  mockMaterialChain,
  mockDeepMaterialChain,
} from '../data/production';

/**
 * MSW handlers for production-related API endpoints.
 * Covers CalculatorTab, EconomicsTab, InventionTab, ReactionsTab,
 * PITab, PIChainBrowser, PIChainPlanner, and PIEmpireOverview.
 */
export const productionHandlers = [
  // Production simulation (CalculatorTab)
  http.get('/api/production/simulate/:typeId', () => {
    return HttpResponse.json(mockProductionSimulation);
  }),

  // Facility comparison (CalculatorTab)
  http.get('/api/production/compare/:typeId', () => {
    return HttpResponse.json(mockCompareResult);
  }),

  // Manufacturing opportunities (EconomicsTab)
  http.get('/api/production/economics/opportunities', () => {
    return HttpResponse.json(mockEconomicsOpportunities);
  }),

  // Decryptor comparison (InventionTab)
  http.get('/api/production/invention/decryptors/:typeId', () => {
    return HttpResponse.json(mockDecryptorComparison);
  }),

  // Invention detail (InventionTab)
  http.get('/api/production/invention/detail/:typeId', () => {
    return HttpResponse.json(mockInventionDetail);
  }),

  // Reaction requirements (ReactionsTab)
  http.get('/api/production/reactions/requirements/:typeId', () => {
    return HttpResponse.json(mockReactionRequirements);
  }),

  // PI schematic formulas (PIChainBrowser)
  http.get('/api/pi/schematics', () => {
    return HttpResponse.json(mockPISchematicFormulas);
  }),

  // PI profitability (PIChainBrowser)
  http.get('/api/pi/profitability', () => {
    return HttpResponse.json(mockPIProfitability);
  }),

  // PI empire analysis (PIEmpireOverview)
  http.get('/api/pi/empire/analysis', () => {
    return HttpResponse.json(mockEmpireAnalysis);
  }),

  // Material chain (PlannerTab) — returns deep chain for Tengu, shallow for everything else
  http.get('/api/production/chain/:typeId', ({ params }) => {
    const typeId = Number(params.typeId);
    if (typeId === 29984) {
      return HttpResponse.json(mockDeepMaterialChain);
    }
    return HttpResponse.json(mockMaterialChain);
  }),

  // PI plans list (PIChainPlanner)
  http.get('/api/pi/plans', () => {
    return HttpResponse.json({ plans: [] });
  }),

  // PI requirements (PITab)
  http.get('/api/pi/requirements/:typeId', () => {
    return HttpResponse.json({
      type_id: 2867,
      type_name: 'Broadcast Node',
      tier: 4,
      chain: {
        type_id: 2867,
        name: 'Broadcast Node',
        tier: 4,
        inputs: [],
      },
      materials: [],
      p0_resources: [],
    });
  }),
];
