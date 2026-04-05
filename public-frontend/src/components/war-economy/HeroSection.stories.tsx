import type { Meta, StoryObj } from '@storybook/react';
import { HeroSection } from './HeroSection';
import type { WarEconomy } from '../../types/reports';

const mockReport: WarEconomy = {
  timestamp: '2026-02-20T12:00:00Z',
  period: '24h',
  regional_demand: [],
  hot_items: [],
  fleet_compositions: [],
  global_summary: {
    total_regions_active: 42,
    total_kills_24h: 6_200,
    total_isk_destroyed: 850_000_000_000,
    hottest_region: {
      region_id: 10000060,
      region_name: 'Delve',
      kills: 890,
    },
    total_opportunity_value: 12_500_000_000,
  },
};

const mockReportQuiet: WarEconomy = {
  ...mockReport,
  global_summary: {
    ...mockReport.global_summary,
    total_kills_24h: 1_400,
    total_regions_active: 18,
    hottest_region: {
      region_id: 10000002,
      region_name: 'The Forge',
      kills: 120,
    },
    total_isk_destroyed: 45_000_000_000,
    total_opportunity_value: 2_100_000_000,
  },
};

const meta: Meta<typeof HeroSection> = {
  title: 'Economy & Market/War Economy/HeroSection',
  component: HeroSection,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof HeroSection>;

/** High activity: HOT status (250+ kills/hr). Delve is hottest region. */
export const HotActivity: Story = {
  args: {
    report: mockReport,
    lastUpdated: new Date(),
  },
};

/** Quiet period: QUIET status (<80 kills/hr). */
export const QuietActivity: Story = {
  args: {
    report: mockReportQuiet,
    lastUpdated: new Date(),
  },
};
