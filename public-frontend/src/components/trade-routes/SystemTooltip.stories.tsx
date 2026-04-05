import type { Meta, StoryObj } from '@storybook/react';
import { SystemTooltip } from './SystemTooltip';

const meta: Meta<typeof SystemTooltip> = {
  title: 'Economy & Market/Supply Chain/SystemTooltip',
  component: SystemTooltip,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof SystemTooltip>;

/** Normal system: standard kill/ISK stats and danger level. */
export const NormalSystem: Story = {
  args: {
    tooltip: {
      system: {
        system_name: 'Perimeter',
        security_status: 0.9,
        danger_score: 1.5,
        kills_24h: 3,
        isk_destroyed_24h: 450_000_000,
        is_gate_camp: false,
      },
      x: 300,
      y: 200,
    },
    selectedMinutes: 1440,
  },
};

/** Gate camp system: warning banner and orange styling. */
export const GateCampSystem: Story = {
  args: {
    tooltip: {
      system: {
        system_name: 'Uedama',
        security_status: 0.5,
        danger_score: 8.5,
        kills_24h: 28,
        isk_destroyed_24h: 6_200_000_000,
        is_gate_camp: true,
      },
      x: 300,
      y: 200,
    },
    selectedMinutes: 1440,
  },
};

/** Battle system: shows "click to view battle details" hint. */
export const BattleSystem: Story = {
  args: {
    tooltip: {
      system: {
        system_name: 'Sivala',
        security_status: 0.4,
        danger_score: 5.2,
        kills_24h: 14,
        isk_destroyed_24h: 2_800_000_000,
        is_gate_camp: false,
        battle_id: 105432,
      },
      x: 300,
      y: 200,
    },
    selectedMinutes: 1440,
  },
};
