import { createElement } from 'react';
import type { Meta, StoryObj, Decorator } from '@storybook/react';
import { ActiveJobs } from './ActiveJobs';
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
      total_jobs: 2,
      active_jobs: 2,
      jobs: [
        { job_id: 3, activity_id: 1, blueprint_id: 17478, blueprint_type_id: 17478, blueprint_type_name: 'Orca Blueprint', product_type_id: 17478, product_type_name: 'Orca', status: 'active', runs: 1, licensed_runs: 1, cost: 350_000_000, start_date: '2026-02-17T12:00:00Z', end_date: '2026-02-23T12:00:00Z', duration: 518400, station_id: 60003760, station_name: 'Jita IV - Moon 4' },
        { job_id: 4, activity_id: 9, blueprint_id: 30309, blueprint_type_id: 30309, blueprint_type_name: 'Fullerite-C72 Reaction', product_type_id: 30309, product_type_name: 'Fullerite-C72', status: 'active', runs: 10, licensed_runs: 100, cost: 5_000_000, start_date: '2026-02-20T00:00:00Z', end_date: '2026-02-20T12:00:00Z', duration: 43200, station_id: 60003760, station_name: 'Jita IV - Moon 4' },
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
    totalAssetValue: 0,
    totalSellOrderValue: 1_450_000_000,
    totalBuyEscrow: 680_000_000,
    totalNetWorth: 5_224_100_000,
    activeIndustryJobs: 4,
    completingSoonJobs: [
      { characterName: 'Artallus', jobName: 'Fullerite-C72', endsAt: new Date(Date.now() + 2 * 3600 * 1000) },
    ],
    outbidCount: 3,
    skillMap: new Map(),
    primaryCharacter: mockCharacters[0],
  },
};

const withPilotIntel: Decorator = (Story) =>
  createElement(PilotIntelContext.Provider, { value: mockPilotIntel }, createElement(Story));

const meta: Meta<typeof ActiveJobs> = {
  title: 'Characters & Account/Dashboard/ActiveJobs',
  component: ActiveJobs,
  tags: ['autodocs'],
  decorators: [withPilotIntel],
};
export default meta;
type Story = StoryObj<typeof ActiveJobs>;

export const Default: Story = {};
