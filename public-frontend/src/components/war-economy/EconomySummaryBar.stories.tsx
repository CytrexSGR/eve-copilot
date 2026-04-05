import type { Meta, StoryObj } from '@storybook/react';
import { EconomySummaryBar } from './EconomySummaryBar';

const meta: Meta<typeof EconomySummaryBar> = {
  title: 'Economy & Market/War Economy/EconomySummaryBar',
  component: EconomySummaryBar,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof EconomySummaryBar>;

/** Active combat period: high kills, ISK destroyed, capitals engaged. */
export const ActiveCombat: Story = {
  args: {
    summary: {
      total_kills: 6_200,
      total_isk_destroyed: 850_000_000_000,
      active_systems: 342,
      capital_kills: 18,
    },
  },
};

/** Quiet period: low activity across New Eden. */
export const QuietPeriod: Story = {
  args: {
    summary: {
      total_kills: 480,
      total_isk_destroyed: 12_000_000_000,
      active_systems: 45,
      capital_kills: 0,
    },
  },
};

/** No data available. */
export const NoData: Story = {
  args: {
    summary: null,
  },
};
