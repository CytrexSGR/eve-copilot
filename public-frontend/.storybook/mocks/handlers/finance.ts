import { http, HttpResponse } from 'msw';
import {
  mockWalletDivisions, mockWalletBalance, mockWalletJournal,
  mockIncome, mockExpenses, mockPnl,
  mockMiningConfig, mockMiningTaxSummary, mockInvoices,
  mockBuybackConfigs, mockBuybackRequests,
  mockRedList, mockInactiveMembers, mockFleetSessions,
  mockApplications, mockVettingReport,
  mockActiveFleets, mockFleetHistory, mockFleetParticipation,
  mockSrpRequests, mockSrpConfig, mockDoctrines,
  mockCockpitData,
} from '../data/finance';

/**
 * MSW handlers for Corp Tools: Finance, HR, Fleet, and SRP.
 */
export const financeHandlers = [
  // ---- Wallet ----
  http.get('/api/finance/wallet/divisions/:corpId', () => {
    return HttpResponse.json(mockWalletDivisions);
  }),

  http.get('/api/finance/wallet/balance/:corpId', () => {
    return HttpResponse.json(mockWalletBalance);
  }),

  http.get('/api/finance/wallet/journal/:corpId', () => {
    return HttpResponse.json(mockWalletJournal);
  }),

  // ---- Reports ----
  http.get('/api/finance/reports/income/:corpId', () => {
    return HttpResponse.json(mockIncome);
  }),

  http.get('/api/finance/reports/expenses/:corpId', () => {
    return HttpResponse.json(mockExpenses);
  }),

  http.get('/api/finance/reports/pnl/:corpId', () => {
    return HttpResponse.json(mockPnl);
  }),

  // ---- Mining Tax ----
  http.get('/api/finance/mining/config/:corpId', () => {
    return HttpResponse.json(mockMiningConfig);
  }),

  http.put('/api/finance/mining/config/:corpId', () => {
    return HttpResponse.json(mockMiningConfig);
  }),

  http.get('/api/finance/mining/tax-summary/:corpId', () => {
    return HttpResponse.json(mockMiningTaxSummary);
  }),

  // ---- Invoices ----
  http.get('/api/finance/invoices', () => {
    return HttpResponse.json(mockInvoices);
  }),

  http.post('/api/finance/invoices/generate', () => {
    return HttpResponse.json({ generated: 3 });
  }),

  http.post('/api/finance/invoices/match-payments/:corpId', () => {
    return HttpResponse.json({ matched: 1 });
  }),

  // ---- Buyback ----
  http.get('/api/finance/buyback/configs', () => {
    return HttpResponse.json({ configs: mockBuybackConfigs, count: mockBuybackConfigs.length });
  }),

  http.get('/api/finance/buyback/requests', () => {
    return HttpResponse.json({ requests: mockBuybackRequests, count: mockBuybackRequests.length });
  }),

  http.post('/api/finance/buyback/appraise', () => {
    return HttpResponse.json({
      items: [
        { type_id: 1228, type_name: 'Veldspar', quantity: 50000, jita_sell: 15, jita_buy: 14, jita_sell_total: 750000, jita_buy_total: 700000, total_volume: 5000, buyback_price: 13.5, buyback_total: 675000 },
      ],
      summary: { item_count: 1, total_jita_sell: 750000, total_jita_buy: 700000, total_volume: 5000 },
      buyback: { total_payout: 675000, discount_applied: 0.1 },
      config: { name: 'Standard Ore', base_discount: 0.1, ore_modifier: 1.0 },
    });
  }),

  // ---- HR: Red List ----
  http.get('/api/hr/redlist', () => {
    return HttpResponse.json(mockRedList);
  }),

  http.post('/api/hr/redlist', () => {
    return HttpResponse.json(mockRedList[0]);
  }),

  // ---- HR: Vetting ----
  http.post('/api/hr/vetting/check', () => {
    return HttpResponse.json(mockVettingReport);
  }),

  http.get('/api/hr/vetting/report/:characterId', () => {
    return HttpResponse.json(mockVettingReport);
  }),

  http.get('/api/hr/vetting/history/:characterId', () => {
    return HttpResponse.json([mockVettingReport]);
  }),

  // ---- HR: Activity ----
  http.get('/api/hr/activity/inactive', () => {
    return HttpResponse.json(mockInactiveMembers);
  }),

  http.get('/api/hr/activity/fleet-sessions', () => {
    return HttpResponse.json(mockFleetSessions);
  }),

  // ---- HR: Applications ----
  http.get('/api/hr/applications/', () => {
    return HttpResponse.json({ applications: mockApplications, count: mockApplications.length });
  }),

  http.put('/api/hr/applications/:id/review', () => {
    return HttpResponse.json({ application_id: 1, status: 'approved' });
  }),

  http.post('/api/hr/applications/:id/vet', () => {
    return HttpResponse.json({ application_id: 1, vetting_report: mockVettingReport });
  }),

  // ---- Fleet ----
  http.get('/api/fleet/active', () => {
    return HttpResponse.json(mockActiveFleets);
  }),

  http.get('/api/fleet/history', () => {
    return HttpResponse.json(mockFleetHistory);
  }),

  http.get('/api/fleet/:opId/participation', () => {
    return HttpResponse.json(mockFleetParticipation);
  }),

  http.get('/api/fleet/:opId/status', () => {
    return HttpResponse.json({
      fleet: mockFleetParticipation.fleet,
      snapshotCount: 12,
      memberCount: 87,
      members: mockFleetParticipation.participants,
    });
  }),

  http.post('/api/fleet/register', () => {
    return HttpResponse.json(mockFleetParticipation.fleet);
  }),

  // ---- SRP ----
  http.get('/api/finance/srp/requests/:corpId', () => {
    return HttpResponse.json(mockSrpRequests);
  }),

  http.get('/api/finance/srp/config/:corpId', () => {
    return HttpResponse.json(mockSrpConfig);
  }),

  http.put('/api/finance/srp/config/:corpId', () => {
    return HttpResponse.json(mockSrpConfig);
  }),

  http.post('/api/finance/srp/sync-prices', () => {
    return HttpResponse.json({ synced: 42, total_types: 42 });
  }),

  // ---- Doctrines ----
  http.get('/api/finance/doctrines/:corpId', () => {
    return HttpResponse.json({ doctrines: mockDoctrines, total: mockDoctrines.length });
  }),

  // ---- Cockpit / Corptools ----
  http.get('/api/corptools/cockpit/:corpId', () => {
    return HttpResponse.json(mockCockpitData);
  }),

  // ---- Doctrine Stats ----
  http.get('/api/doctrines/:doctrineId/stats', () => {
    return HttpResponse.json({
      offense: { total_dps: 1250, weapon_dps: 1050, drone_dps: 200 },
      defense: { total_ehp: 95000, tank_type: 'shield', shield_ehp: 72000, armor_ehp: 23000 },
      capacitor: { stable: true, cap_amount: 4200 },
      navigation: { max_velocity: 1450, align_time: 8.2 },
      targeting: { max_range: 120000, scan_resolution: 280 },
    });
  }),

  http.get('/api/doctrines/:doctrineId/readiness/:characterId', () => {
    return HttpResponse.json({
      doctrine_id: 5, character_id: 1117367444,
      all_v_stats: { offense: { total_dps: 1250, weapon_dps: 1050, drone_dps: 200 }, defense: { total_ehp: 95000, tank_type: 'shield', shield_ehp: 72000, armor_ehp: 23000 }, capacitor: { stable: true }, navigation: { max_velocity: 1450, align_time: 8.2 }, targeting: { max_range: 120000, scan_resolution: 280 } },
      character_stats: { offense: { total_dps: 1100, weapon_dps: 920, drone_dps: 180 }, defense: { total_ehp: 88000, tank_type: 'shield', shield_ehp: 66000, armor_ehp: 22000 }, capacitor: { stable: true }, navigation: { max_velocity: 1380, align_time: 8.5 }, targeting: { max_range: 110000, scan_resolution: 260 } },
      dps_ratio: 0.88, ehp_ratio: 0.93, missing_skills: [], can_fly: true,
    });
  }),

  http.get('/api/doctrines/:doctrineId/bom', () => {
    return HttpResponse.json({
      items: [
        { type_id: 17726, type_name: 'Nightmare', quantity: 1 },
        { type_id: 3170, type_name: 'Large Pulse Laser II', quantity: 4 },
        { type_id: 3841, type_name: 'Large Shield Extender II', quantity: 2 },
      ],
    });
  }),

  // ---- Corp Summary helpers ----
  http.get('/api/timers/upcoming', () => {
    return HttpResponse.json([]);
  }),
];
