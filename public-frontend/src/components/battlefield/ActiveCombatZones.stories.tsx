import type { Meta, StoryObj } from '@storybook/react';
import { ActiveCombatZones } from './ActiveCombatZones';
import { fn } from '@storybook/test';

const meta: Meta<typeof ActiveCombatZones> = {
  title: 'Battlefield/ActiveCombatZones',
  component: ActiveCombatZones,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof ActiveCombatZones>;

const mockSystems = [
  {
    solar_system_id: 30004759,
    system_name: 'M-OEE8',
    region_name: 'Tribute',
    security_status: -0.4,
    kill_count: 87,
    total_value: 45_000_000_000,
    capital_kills: 3,
    last_kill_minutes_ago: 2,
    threat_level: 'critical' as const,
    sov_alliance_id: 99003581,
    sov_alliance_name: 'Fraternity.',
    sov_alliance_ticker: 'FRT',
  },
  {
    solar_system_id: 30002813,
    system_name: 'HED-GP',
    region_name: 'Catch',
    security_status: -0.3,
    kill_count: 42,
    total_value: 12_000_000_000,
    capital_kills: 1,
    last_kill_minutes_ago: 8,
    threat_level: 'hot' as const,
    sov_alliance_id: 99010079,
    sov_alliance_name: 'Brave Collective',
    sov_alliance_ticker: 'BRAVE',
  },
  {
    solar_system_id: 30001198,
    system_name: 'Amamake',
    region_name: 'Heimatar',
    security_status: 0.4,
    kill_count: 15,
    total_value: 800_000_000,
    capital_kills: 0,
    last_kill_minutes_ago: 25,
    threat_level: 'active' as const,
    sov_alliance_id: null,
    sov_alliance_name: null,
    sov_alliance_ticker: null,
  },
  {
    solar_system_id: 30000142,
    system_name: 'Jita',
    region_name: 'The Forge',
    security_status: 0.9,
    kill_count: 3,
    total_value: 120_000_000,
    capital_kills: 0,
    last_kill_minutes_ago: 120,
    threat_level: 'low' as const,
    sov_alliance_id: null,
    sov_alliance_name: null,
    sov_alliance_ticker: null,
  },
];

export const Default: Story = {
  args: {
    systems: mockSystems,
    onSystemClick: fn(),
  },
};

export const CriticalOnly: Story = {
  args: {
    systems: mockSystems.filter(s => s.threat_level === 'critical'),
    onSystemClick: fn(),
  },
};

export const Empty: Story = {
  args: {
    systems: [],
  },
};

export const ManyZones: Story = {
  args: {
    systems: [
      ...mockSystems,
      {
        solar_system_id: 30001200,
        system_name: 'Tama',
        region_name: 'The Citadel',
        security_status: 0.3,
        kill_count: 28,
        total_value: 2_500_000_000,
        capital_kills: 0,
        last_kill_minutes_ago: 4,
        threat_level: 'hot' as const,
        sov_alliance_id: null,
        sov_alliance_name: null,
        sov_alliance_ticker: null,
      },
      {
        solar_system_id: 30002813,
        system_name: 'GE-8JV',
        region_name: 'Catch',
        security_status: -0.5,
        kill_count: 55,
        total_value: 8_000_000_000,
        capital_kills: 2,
        last_kill_minutes_ago: 1,
        threat_level: 'critical' as const,
        sov_alliance_id: 99010079,
        sov_alliance_name: 'Brave Collective',
        sov_alliance_ticker: 'BRAVE',
      },
    ],
    onSystemClick: fn(),
  },
};
