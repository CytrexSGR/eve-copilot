import type { Meta, StoryObj } from '@storybook/react';
import { WarEconomyTicker } from './WarEconomyTicker';
import type { WarEconomy } from '../../types/economy';

const mockReport: WarEconomy = {
  timestamp: '2026-02-20T12:00:00Z',
  period: '24h',
  regional_demand: [
    {
      region_id: 10000060,
      region_name: 'Delve',
      kills: 890,
      isk_destroyed: 120_000_000_000,
      top_demanded_items: [],
      ship_classes: {},
      demand_score: 78,
    },
    {
      region_id: 10000014,
      region_name: 'Catch',
      kills: 540,
      isk_destroyed: 65_000_000_000,
      top_demanded_items: [],
      ship_classes: {},
      demand_score: 62,
    },
  ],
  hot_items: [
    {
      item_type_id: 34,
      item_name: 'Tritanium',
      quantity_destroyed: 500_000_000,
      market_price: 5.82,
    },
    {
      item_type_id: 4247,
      item_name: 'Helium Fuel Block',
      quantity_destroyed: 180_000,
      market_price: 14500,
    },
  ],
  fleet_compositions: [
    {
      region_id: 10000060,
      region_name: 'Delve',
      total_ships_lost: 450,
      composition: {},
      doctrine_hints: ['Eagle Fleet', 'Muninn Fleet'],
    },
  ],
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

const meta: Meta<typeof WarEconomyTicker> = {
  title: 'Economy & Market/War Economy/WarEconomyTicker',
  component: WarEconomyTicker,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof WarEconomyTicker>;

/**
 * Active ticker with hot zones, opportunities, fleets, demand items,
 * and global stats scrolling horizontally. Hover to pause.
 */
export const Default: Story = {
  args: {
    report: mockReport,
    alerts: [],
  },
};

/**
 * Ticker with war room alerts injected as priority items.
 */
export const WithAlerts: Story = {
  args: {
    report: mockReport,
    alerts: [
      {
        id: 'alert-1',
        type: 'manipulation' as const,
        message: 'Tritanium price spike in Jita',
        detail: '+15% above baseline price',
        priority: 'high' as const,
        timestamp: new Date(),
        icon: '📈',
      },
      {
        id: 'alert-2',
        type: 'fuel' as const,
        message: 'Helium Fuel Block shortage',
        detail: 'Volume down 40% in The Forge',
        priority: 'critical' as const,
        timestamp: new Date(),
        icon: '⛽',
      },
    ],
  },
};

/**
 * Empty report: shows "No recent activity" placeholder.
 */
export const Empty: Story = {
  args: {
    report: {
      ...mockReport,
      regional_demand: [],
      hot_items: [],
      fleet_compositions: [],
      global_summary: {
        ...mockReport.global_summary,
        total_kills_24h: 0,
        total_regions_active: 0,
        hottest_region: null,
      },
    },
    alerts: [],
  },
};
