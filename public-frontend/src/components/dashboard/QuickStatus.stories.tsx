import { createElement } from 'react';
import type { Meta, StoryObj, Decorator } from '@storybook/react';
import { QuickStatus } from './QuickStatus';
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
    location: { character_id: 1117367444, solar_system_id: 30004609, solar_system_name: 'K-6K16', station_id: null, station_name: null, structure_id: null },
    ship: { character_id: 1117367444, ship_type_id: 24688, ship_type_name: 'Drake', ship_item_id: 1234567890, ship_name: 'Combat Drake' },
    industry: {
      character_id: 1117367444,
      total_jobs: 1,
      active_jobs: 1,
      jobs: [
        { job_id: 1, activity_id: 1, blueprint_id: 11379, blueprint_type_id: 11379, blueprint_type_name: '', product_type_id: 24698, product_type_name: 'Drake', status: 'active', runs: 5, licensed_runs: 10, cost: 45_000_000, start_date: '2026-02-19T10:00:00Z', end_date: '2026-02-21T10:00:00Z', duration: 172800, station_id: 60003760, station_name: 'Jita IV - Moon 4' },
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
    location: { character_id: 526379435, solar_system_id: 30002764, solar_system_name: 'Isikemi', station_id: null, station_name: null, structure_id: null },
    ship: { character_id: 526379435, ship_type_id: 17478, ship_type_name: 'Orca', ship_item_id: 1234567891, ship_name: 'Mining Orca' },
    industry: { character_id: 526379435, total_jobs: 0, active_jobs: 0, jobs: [] },
  },
  {
    character_id: 110592475,
    character_name: 'Cytricia',
    info: null,
    wallet: { balance: 17_100_000, formatted: '17.1M' },
    skills: null,
    skillqueue: null,
    location: { character_id: 110592475, solar_system_id: 30002764, solar_system_name: 'Isikemi', station_id: null, station_name: null, structure_id: null },
    ship: { character_id: 110592475, ship_type_id: 17478, ship_type_name: 'Orca', ship_item_id: 1234567892, ship_name: 'Industry Orca' },
    industry: { character_id: 110592475, total_jobs: 0, active_jobs: 0, jobs: [] },
  },
  {
    character_id: 2124063958,
    character_name: 'Mind Overmatter',
    info: null,
    wallet: { balance: 6_600_000, formatted: '6.6M' },
    skills: null,
    skillqueue: null,
    location: { character_id: 2124063958, solar_system_id: 30000142, solar_system_name: 'Jita', station_id: 60003760, station_name: 'Jita IV - Moon 4', structure_id: null },
    ship: { character_id: 2124063958, ship_type_id: 587, ship_type_name: 'Rifter', ship_item_id: 1234567893, ship_name: '' },
    industry: { character_id: 2124063958, total_jobs: 0, active_jobs: 0, jobs: [] },
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
    totalWallet: 3_117_800_000,
    totalAssetValue: 0,
    totalSellOrderValue: 0,
    totalBuyEscrow: 0,
    totalNetWorth: 3_117_800_000,
    activeIndustryJobs: 1,
    completingSoonJobs: [],
    outbidCount: 0,
    skillMap: new Map(),
    primaryCharacter: mockCharacters[0],
  },
};

const withPilotIntel: Decorator = (Story) =>
  createElement(PilotIntelContext.Provider, { value: mockPilotIntel }, createElement(Story));

const meta: Meta<typeof QuickStatus> = {
  title: 'Characters & Account/Dashboard/QuickStatus',
  component: QuickStatus,
  tags: ['autodocs'],
  decorators: [withPilotIntel],
};
export default meta;
type Story = StoryObj<typeof QuickStatus>;

export const Default: Story = {};
