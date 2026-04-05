import type { Meta, StoryObj } from '@storybook/react';
import { TradeRouteThreats } from './TradeRouteThreats';
import { fn } from '@storybook/test';

const meta: Meta<typeof TradeRouteThreats> = {
  title: 'Battlefield/TradeRouteThreats',
  component: TradeRouteThreats,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof TradeRouteThreats>;

const mockRoutes = [
  {
    origin_system: 'Jita',
    destination_system: '1DQ1-A',
    jumps: 42,
    danger_score: 65,
    total_kills: 78,
    total_isk_destroyed: 12_500_000_000,
    systems: [
      { system_id: 30000142, system_name: 'Jita', security_status: 0.9, danger_score: 5, kills_24h: 2, isk_destroyed_24h: 50_000_000, is_gate_camp: false },
      { system_id: 30002813, system_name: 'HED-GP', security_status: -0.3, danger_score: 80, kills_24h: 25, isk_destroyed_24h: 5_000_000_000, is_gate_camp: true },
      { system_id: 30004759, system_name: 'M-OEE8', security_status: -0.4, danger_score: 60, kills_24h: 15, isk_destroyed_24h: 2_000_000_000, is_gate_camp: false },
    ],
  },
  {
    origin_system: 'Amarr',
    destination_system: 'GE-8JV',
    jumps: 28,
    danger_score: 35,
    total_kills: 22,
    total_isk_destroyed: 3_200_000_000,
    systems: [
      { system_id: 30002187, system_name: 'Amarr', security_status: 1.0, danger_score: 2, kills_24h: 0, isk_destroyed_24h: 0, is_gate_camp: false },
      { system_id: 30002813, system_name: 'Keberz', security_status: 0.5, danger_score: 30, kills_24h: 8, isk_destroyed_24h: 500_000_000, is_gate_camp: true },
    ],
  },
  {
    origin_system: 'Dodixie',
    destination_system: 'K-6K16',
    jumps: 35,
    danger_score: 15,
    total_kills: 5,
    total_isk_destroyed: 200_000_000,
    systems: [
      { system_id: 30002659, system_name: 'Dodixie', security_status: 0.9, danger_score: 3, kills_24h: 1, isk_destroyed_24h: 50_000_000, is_gate_camp: false },
    ],
  },
];

export const Default: Story = {
  args: {
    routes: mockRoutes,
    onRouteClick: fn(),
    onSystemClick: fn(),
  },
};

export const AllClear: Story = {
  args: {
    routes: [mockRoutes[2]],
    onRouteClick: fn(),
  },
};

export const Empty: Story = {
  args: {
    routes: [],
  },
};
