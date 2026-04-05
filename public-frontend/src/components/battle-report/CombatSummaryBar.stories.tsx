import type { Meta, StoryObj } from '@storybook/react';
import { CombatSummaryBar } from './CombatSummaryBar';

const meta: Meta<typeof CombatSummaryBar> = {
  title: 'BattleReport/CombatSummaryBar',
  component: CombatSummaryBar,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof CombatSummaryBar>;

export const Default: Story = {
  args: {
    summary: {
      total_kills: 1247,
      total_isk_destroyed: 350_000_000_000,
      active_systems: 42,
      capital_kills: 18,
    },
  },
};

export const LowActivity: Story = {
  args: {
    summary: {
      total_kills: 12,
      total_isk_destroyed: 500_000_000,
      active_systems: 3,
      capital_kills: 0,
    },
  },
};

export const NullSummary: Story = {
  args: {
    summary: null,
  },
};
