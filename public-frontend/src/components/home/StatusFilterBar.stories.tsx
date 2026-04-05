import type { Meta, StoryObj } from '@storybook/react';
import { StatusFilterBar } from './StatusFilterBar';
import { fn } from '@storybook/test';

const meta: Meta<typeof StatusFilterBar> = {
  title: 'Home/StatusFilterBar',
  component: StatusFilterBar,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof StatusFilterBar>;

export const Default: Story = {
  args: {
    statusFilters: { gank: true, brawl: true, battle: true, hellcamp: true },
    onStatusFilterChange: fn(),
    statusCounts: { gank: 68, brawl: 5, battle: 2, hellcamp: 0 },
    colorMode: 'security',
    onColorModeChange: fn(),
    activityMinutes: 60,
    onActivityMinutesChange: fn(),
  },
};

export const PartialFilters: Story = {
  args: {
    statusFilters: { gank: true, brawl: false, battle: true, hellcamp: false },
    onStatusFilterChange: fn(),
    statusCounts: { gank: 42, brawl: 3, battle: 1, hellcamp: 0 },
    colorMode: 'region',
    onColorModeChange: fn(),
    activityMinutes: 10,
    onActivityMinutesChange: fn(),
  },
};

export const WithExternalLink: Story = {
  args: {
    statusFilters: { gank: true, brawl: true, battle: true, hellcamp: true },
    onStatusFilterChange: fn(),
    statusCounts: { gank: 55, brawl: 8, battle: 3, hellcamp: 1 },
    colorMode: 'alliance',
    onColorModeChange: fn(),
    activityMinutes: 60,
    onActivityMinutesChange: fn(),
    externalLink: '/ectmap',
  },
};
