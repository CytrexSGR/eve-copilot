import type { Meta, StoryObj } from '@storybook/react';
import { CombatTab } from './CombatTab';
import { mockWarEconomyReport } from '../../../.storybook/mocks/data/war-economy';

const meta: Meta<typeof CombatTab> = {
  title: 'Economy & Market/War Economy/CombatTab',
  component: CombatTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof CombatTab>;

/**
 * Default 1-hour timeframe: Combat hotspots, regional losses,
 * capital activity, doctrine demand, and top ships lost panels.
 * Fetches hot systems and capital intel via MSW.
 */
export const Default: Story = {
  args: {
    report: mockWarEconomyReport,
    timeframeMinutes: 60,
  },
};

/** 24-hour timeframe: broader combat data aggregation. */
export const DayTimeframe: Story = {
  args: {
    report: mockWarEconomyReport,
    timeframeMinutes: 1440,
  },
};
