import type { Meta, StoryObj } from '@storybook/react';
import { RoutesTab } from './RoutesTab';
import { fn } from '@storybook/test';

const meta: Meta<typeof RoutesTab> = {
  title: 'Economy & Market/War Economy/RoutesTab',
  component: RoutesTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof RoutesTab>;

/**
 * Default 1-hour view: Trade route intelligence panel with
 * danger-scored routes, expandable system chains, gate camp
 * and battle markers. Fetches via MSW reportsApi.
 */
export const Default: Story = {
  args: {
    selectedMinutes: 60,
    onTimeChange: fn(),
  },
};

/** 24-hour timeframe: broader route danger aggregation. */
export const DayTimeframe: Story = {
  args: {
    selectedMinutes: 1440,
    onTimeChange: fn(),
  },
};
