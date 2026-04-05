import { createElement } from 'react';
import type { Meta, StoryObj, Decorator } from '@storybook/react';
import { http, HttpResponse } from 'msw';
import { WealthDashboard } from './WealthDashboard';
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
    industry: {
      character_id: 1117367444,
      total_jobs: 2,
      active_jobs: 2,
      jobs: [
        { job_id: 1, activity_id: 1, blueprint_id: 11379, blueprint_type_id: 11379, blueprint_type_name: 'Drake Blueprint', product_type_id: 24698, product_type_name: 'Drake', status: 'active', runs: 5, licensed_runs: 10, cost: 45_000_000, start_date: '2026-02-19T10:00:00Z', end_date: '2026-02-21T10:00:00Z', duration: 172800, station_id: 60003760, station_name: 'Jita IV - Moon 4' },
        { job_id: 2, activity_id: 8, blueprint_id: 12011, blueprint_type_id: 12011, blueprint_type_name: 'Eagle Blueprint', product_type_id: 12011, product_type_name: 'Eagle', status: 'active', runs: 1, licensed_runs: 1, cost: 120_000_000, start_date: '2026-02-18T08:00:00Z', end_date: '2026-02-22T08:00:00Z', duration: 345600, station_id: 60003760, station_name: 'Jita IV - Moon 4' },
      ],
    },
  },
  {
    character_id: 526379435,
    character_name: 'Artallus',
    info: null,
    wallet: { balance: 14_100_000, formatted: '14.1M' },
    skills: null,
    skillqueue: null,
    location: null,
    ship: null,
    industry: {
      character_id: 526379435,
      total_jobs: 1,
      active_jobs: 1,
      jobs: [
        { job_id: 3, activity_id: 1, blueprint_id: 17478, blueprint_type_id: 17478, blueprint_type_name: 'Orca Blueprint', product_type_id: 17478, product_type_name: 'Orca', status: 'active', runs: 1, licensed_runs: 1, cost: 350_000_000, start_date: '2026-02-17T12:00:00Z', end_date: '2026-02-23T12:00:00Z', duration: 518400, station_id: 60003760, station_name: 'Jita IV - Moon 4' },
      ],
    },
  },
] as unknown as CharacterSummary[];

const mockPilotIntel: PilotIntelState = {
  isLoading: false,
  refresh: async () => {},
  profile: {
    characters: mockCharacters,
    portfolioSummary: null,
    orders: {
      summary: { total_characters: 2, total_isk_in_sell_orders: 1_450_000_000, total_isk_in_buy_orders: 680_000_000, outbid_count: 3, undercut_count: 1, total_sell_orders: 12, total_buy_orders: 5 },
      by_character: [],
      orders: [],
      generated_at: '2026-02-20T12:00:00Z',
    },
    lastUpdated: null,
  },
  derived: {
    totalWallet: 3_094_100_000,
    totalAssetValue: 5_200_000_000,
    totalSellOrderValue: 1_450_000_000,
    totalBuyEscrow: 680_000_000,
    totalNetWorth: 10_424_100_000,
    activeIndustryJobs: 3,
    completingSoonJobs: [],
    outbidCount: 3,
    skillMap: new Map(),
    primaryCharacter: mockCharacters[0],
  },
};

const withPilotIntel: Decorator = (Story) =>
  createElement(PilotIntelContext.Provider, { value: mockPilotIntel }, createElement(Story));

/** MSW handlers for portfolio and trading APIs consumed by WealthDashboard. */
const wealthHandlers = [
  http.get('/api/market/portfolio/:characterId/history', () => {
    return HttpResponse.json({
      character_id: 1117367444,
      days: 30,
      snapshots: [
        { date: '2026-02-10', total_value: 7_800_000_000 },
        { date: '2026-02-15', total_value: 8_100_000_000 },
        { date: '2026-02-20', total_value: 10_424_100_000 },
      ],
      growth_absolute: 2_624_100_000,
      growth_percent: 33.6,
    });
  }),
  http.get('/api/market/trading/:characterId/pnl', () => {
    return HttpResponse.json({
      character_id: 1117367444,
      period_days: 30,
      realized_pnl: 2_400_000_000,
      unrealized_pnl: 350_000_000,
      total_trades: 156,
      winning_trades: 98,
      losing_trades: 58,
    });
  }),
];

const meta: Meta<typeof WealthDashboard> = {
  title: 'Characters & Account/Characters/WealthDashboard',
  component: WealthDashboard,
  tags: ['autodocs'],
  decorators: [withPilotIntel],
  parameters: {
    msw: { handlers: wealthHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof WealthDashboard>;

export const Default: Story = {};
