import type { Meta, StoryObj } from '@storybook/react';
import { TradeRouteCard } from './TradeRouteCard';
import { fn } from '@storybook/test';

const safeRoute = {
  origin_system: 'Jita',
  destination_system: 'Amarr',
  jumps: 9,
  total_kills: 3,
  total_isk_destroyed: 450_000_000,
  danger_score: 1.2,
  systems: [
    { system_id: 30000142, system_name: 'Jita', security_status: 0.9, danger_score: 0.5, kills_24h: 1, isk_destroyed_24h: 50_000_000, is_gate_camp: false },
    { system_id: 30000144, system_name: 'Perimeter', security_status: 0.9, danger_score: 0.8, kills_24h: 2, isk_destroyed_24h: 200_000_000, is_gate_camp: false },
    { system_id: 30002187, system_name: 'Amarr', security_status: 1.0, danger_score: 0.2, kills_24h: 0, isk_destroyed_24h: 0, is_gate_camp: false },
  ],
};

const dangerousRoute = {
  origin_system: 'Jita',
  destination_system: 'Rens',
  jumps: 15,
  total_kills: 42,
  total_isk_destroyed: 8_500_000_000,
  danger_score: 7.8,
  systems: [
    { system_id: 30000142, system_name: 'Jita', security_status: 0.9, danger_score: 0.5, kills_24h: 1, isk_destroyed_24h: 50_000_000, is_gate_camp: false },
    { system_id: 30002813, system_name: 'Uedama', security_status: 0.5, danger_score: 8.5, kills_24h: 28, isk_destroyed_24h: 6_200_000_000, is_gate_camp: true },
    { system_id: 30002053, system_name: 'Sivala', security_status: 0.4, danger_score: 5.2, kills_24h: 8, isk_destroyed_24h: 1_800_000_000, is_gate_camp: false, battle_id: 105432 },
    { system_id: 30002510, system_name: 'Rens', security_status: 0.9, danger_score: 0.3, kills_24h: 0, isk_destroyed_24h: 0, is_gate_camp: false },
  ],
};

const meta: Meta<typeof TradeRouteCard> = {
  title: 'Economy & Market/Supply Chain/TradeRouteCard',
  component: TradeRouteCard,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  args: {
    onToggle: fn(),
    onSystemHover: fn(),
    onSystemLeave: fn(),
    onBattleClick: fn(),
    selectedMinutes: 1440,
  },
};

export default meta;
type Story = StoryObj<typeof TradeRouteCard>;

/** Safe route: Jita to Amarr, low danger score. Collapsed state. */
export const SafeCollapsed: Story = {
  args: {
    route: safeRoute,
    isExpanded: false,
  },
};

/** Safe route expanded: shows system chain and recommendations. */
export const SafeExpanded: Story = {
  args: {
    route: safeRoute,
    isExpanded: true,
  },
};

/** Critical danger: Jita to Rens via Uedama with active gate camp and battle. */
export const DangerousCollapsed: Story = {
  args: {
    route: dangerousRoute,
    isExpanded: false,
  },
};

/** Dangerous route expanded: gate camp warnings, battle markers, danger recommendations. */
export const DangerousExpanded: Story = {
  args: {
    route: dangerousRoute,
    isExpanded: true,
  },
};
