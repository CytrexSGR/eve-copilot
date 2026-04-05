import { createElement } from 'react';
import type { Meta, StoryObj, Decorator } from '@storybook/react';
import { http, HttpResponse } from 'msw';
import { TopOpportunities } from './TopOpportunities';
import { PilotIntelContext } from '../../context/PilotIntelContext';
import type { PilotIntelState } from '../../types/pilot-intel';
import type { CharacterSummary } from '../../types/character';

const mockCharacters = [
  {
    character_id: 1117367444,
    character_name: 'Cytrex',
    info: null,
    wallet: { balance: 3_080_000_000, formatted: '3.08B' },
    skills: null,
    skillqueue: null,
    location: null,
    ship: null,
    industry: { character_id: 1117367444, total_jobs: 0, active_jobs: 0, jobs: [] },
  },
] as unknown as CharacterSummary[];

const mockPilotIntel: PilotIntelState = {
  isLoading: false,
  refresh: async () => {},
  profile: {
    characters: mockCharacters,
    portfolioSummary: null,
    orders: null,
    lastUpdated: null,
  },
  derived: {
    totalWallet: 3_080_000_000,
    totalAssetValue: 5_200_000_000,
    totalSellOrderValue: 1_450_000_000,
    totalBuyEscrow: 680_000_000,
    totalNetWorth: 10_410_000_000,
    activeIndustryJobs: 0,
    completingSoonJobs: [],
    outbidCount: 0,
    skillMap: new Map(),
    primaryCharacter: mockCharacters[0],
  },
};

const withPilotIntel: Decorator = (Story) =>
  createElement(PilotIntelContext.Provider, { value: mockPilotIntel }, createElement(Story));

/** MSW handlers for market opportunity APIs consumed by TopOpportunities. */
const opportunityHandlers = [
  http.get('/api/market/hunter/scan', () => {
    return HttpResponse.json({
      results: [
        { product_name: 'Drake', product_type_id: 24698, material_cost: 80_000_000, sell_price: 120_000_000, profit: 40_000_000, net_profit: 35_000_000, roi: 50, net_roi: 44, risk_score: 25, avg_daily_volume: 12, difficulty: 3 },
        { product_name: 'Raven', product_type_id: 638, material_cost: 200_000_000, sell_price: 310_000_000, profit: 110_000_000, net_profit: 95_000_000, roi: 55, net_roi: 48, risk_score: 30, avg_daily_volume: 5, difficulty: 5 },
      ],
      count: 2,
    });
  }),
  http.get('/api/market/routes', () => {
    return HttpResponse.json({
      routes: [
        {
          source_hub: 'Jita',
          destination_hub: 'Amarr',
          jumps: 9,
          safety: 'SAFE',
          summary: { total_items: 15, total_buy_cost: 500_000_000, total_sell_value: 650_000_000, total_profit: 150_000_000, total_volume: 8000 },
          logistics: { round_trip_time: '2.5', recommended_ship: 'Blockade Runner', cargo_needed: 8000 },
        },
      ],
      total_routes: 1,
    });
  }),
  http.get('/api/market/trading/opportunities', () => {
    return HttpResponse.json({
      results: [
        { item_name: 'Tritanium', type_id: 34, buy_price: 5.2, sell_price: 5.8, profit_per_unit: 0.6, roi: 11.5, margin: 10.3, volume: 5_000_000, risk_score: 15 },
        { item_name: 'Isogen', type_id: 37, buy_price: 42, sell_price: 48, profit_per_unit: 6, roi: 14.3, margin: 12.5, volume: 150_000, risk_score: 25 },
      ],
      count: 2,
    });
  }),
];

const meta: Meta<typeof TopOpportunities> = {
  title: 'Characters & Account/Dashboard/TopOpportunities',
  component: TopOpportunities,
  tags: ['autodocs'],
  decorators: [withPilotIntel],
  parameters: {
    msw: { handlers: opportunityHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof TopOpportunities>;

export const Default: Story = {};
