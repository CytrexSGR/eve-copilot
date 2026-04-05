import { http, HttpResponse } from 'msw';
import {
  mockHotItemsByCategory,
  mockTritaniumPrices,
  mockTritaniumStats,
  mockArbitrageRoutes,
  mockManufacturingOpportunities,
  mockTradingOpportunities,
  mockRegionalComparison,
  mockRawSellOrders,
  mockAggregatedOrders,
  mockPnlReport,
  mockPortfolioSnapshots,
} from '../data/market';

/**
 * MSW handlers for market-related API endpoints.
 * Covers MarketHeroSection, MarketTicker, PricesTab, HistoryTab,
 * ArbitrageTab, OpportunitiesTab, and PortfolioTab.
 */
export const marketHandlers = [
  // Hot items by category (MarketHeroSection + MarketTicker)
  http.get('/api/market/hot-items/categories', () => {
    return HttpResponse.json(mockHotItemsByCategory);
  }),

  // Price per type/region (PricesTab)
  http.get('/api/market/price/:typeId/:regionId', ({ params }) => {
    const regionId = Number(params.regionId);
    const price = mockTritaniumPrices[regionId] || mockTritaniumPrices[10000002];
    return HttpResponse.json(price);
  }),

  // Market stats (PricesTab)
  http.get('/api/market/stats/:typeId', () => {
    return HttpResponse.json(mockTritaniumStats);
  }),

  // Regional comparison (HistoryTab)
  http.get('/api/market/regional-comparison/:typeId', () => {
    return HttpResponse.json(mockRegionalComparison);
  }),

  // Raw orders (HistoryTab)
  http.get('/api/market/orders/:typeId/:regionId', () => {
    return HttpResponse.json(mockRawSellOrders);
  }),

  // Arbitrage routes (ArbitrageTab)
  http.get('/api/market/arbitrage/routes', () => {
    return HttpResponse.json(mockArbitrageRoutes);
  }),

  // Opportunity scanner (OpportunitiesTab - manufacturing)
  http.get('/api/market/opportunities/scan', () => {
    return HttpResponse.json(mockManufacturingOpportunities);
  }),

  // Trading opportunities (OpportunitiesTab - trading)
  http.get('/api/market/opportunities/trading', () => {
    return HttpResponse.json(mockTradingOpportunities);
  }),

  // Aggregated orders (PortfolioTab)
  http.get('/api/market/orders/aggregated', () => {
    return HttpResponse.json(mockAggregatedOrders);
  }),

  // Trading P&L (PortfolioTab)
  http.get('/api/market/trading/pnl/:characterId', () => {
    return HttpResponse.json(mockPnlReport);
  }),

  // Portfolio summary (PortfolioTab)
  http.get('/api/market/portfolio/summary', () => {
    return HttpResponse.json(mockPortfolioSnapshots);
  }),
];
