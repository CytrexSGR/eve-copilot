import type { Meta, StoryObj } from '@storybook/react';
import { TradingTab } from './TradingTab';
import { fn } from '@storybook/test';
import {
  mockExtendedHotItems,
  mockWarzoneRoutes,
} from '../../../.storybook/mocks/data/war-economy';

const meta: Meta<typeof TradingTab> = {
  title: 'Economy & Market/War Economy/TradingTab',
  component: TradingTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof TradingTab>;

/**
 * Default: Hero stats, combat demand items, and warzone trade routes.
 * Expandable item and route rows with detailed price/cargo info.
 */
export const Default: Story = {
  args: {
    extendedHotItems: mockExtendedHotItems,
    warzoneRoutes: mockWarzoneRoutes,
    expandedItem: null,
    expandedRoute: null,
    onExpandItem: fn(),
    onExpandRoute: fn(),
    loading: false,
  },
};

/** Item expanded: shows buy/sell arbitrage, hub prices, destruction zones. */
export const ItemExpanded: Story = {
  args: {
    extendedHotItems: mockExtendedHotItems,
    warzoneRoutes: mockWarzoneRoutes,
    expandedItem: 2048,
    expandedRoute: null,
    onExpandItem: fn(),
    onExpandRoute: fn(),
    loading: false,
  },
};

/** Route expanded: shows cost, ROI, cargo manifest table. */
export const RouteExpanded: Story = {
  args: {
    extendedHotItems: mockExtendedHotItems,
    warzoneRoutes: mockWarzoneRoutes,
    expandedItem: null,
    expandedRoute: 10000014,
    onExpandItem: fn(),
    onExpandRoute: fn(),
    loading: false,
  },
};

/** Loading state: shows loading placeholder instead of data panels. */
export const Loading: Story = {
  args: {
    extendedHotItems: null,
    warzoneRoutes: null,
    expandedItem: null,
    expandedRoute: null,
    onExpandItem: fn(),
    onExpandRoute: fn(),
    loading: true,
  },
};
