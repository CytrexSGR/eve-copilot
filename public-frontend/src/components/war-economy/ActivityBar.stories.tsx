import type { Meta, StoryObj } from '@storybook/react';
import { ActivityBar } from './ActivityBar';

const meta: Meta<typeof ActivityBar> = {
  title: 'Economy & Market/War Economy/ActivityBar',
  component: ActivityBar,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof ActivityBar>;

/** HOT combat intensity: 280 kills/hr, major conflict in progress. */
export const Hot: Story = {
  args: {
    killsPerHour: 280,
    iskPerHour: 42_000_000_000,
    regionsActive: 52,
    avgKillsPerRegion: 5.4,
  },
};

/** ACTIVE: busy but not extreme. 180 kills/hr. */
export const Active: Story = {
  args: {
    killsPerHour: 180,
    iskPerHour: 22_000_000_000,
    regionsActive: 38,
    avgKillsPerRegion: 4.7,
  },
};

/** MODERATE: normal activity. 120 kills/hr. */
export const Moderate: Story = {
  args: {
    killsPerHour: 120,
    iskPerHour: 12_000_000_000,
    regionsActive: 28,
    avgKillsPerRegion: 4.3,
  },
};

/** QUIET: low activity. 40 kills/hr. */
export const Quiet: Story = {
  args: {
    killsPerHour: 40,
    iskPerHour: 3_500_000_000,
    regionsActive: 12,
    avgKillsPerRegion: 3.3,
  },
};
