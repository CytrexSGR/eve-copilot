import type { Meta, StoryObj } from '@storybook/react';
import { MarketTabNavigation } from './MarketTabNavigation';
import { fn } from '@storybook/test';

const meta: Meta<typeof MarketTabNavigation> = {
  title: 'Economy & Market/Market/MarketTabNavigation',
  component: MarketTabNavigation,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  args: {
    onTabChange: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof MarketTabNavigation>;

/** All tabs enabled, Prices tab active. */
export const Default: Story = {
  args: {
    activeTab: 'prices',
    hasSelectedItem: true,
  },
};

/** Arbitrage tab selected (no item required). */
export const ArbitrageActive: Story = {
  args: {
    activeTab: 'arbitrage',
    hasSelectedItem: false,
  },
};

/** No item selected - item-dependent tabs (Prices, History) are disabled. */
export const NoItemSelected: Story = {
  args: {
    activeTab: 'arbitrage',
    hasSelectedItem: false,
  },
};

/** Portfolio tab active. */
export const PortfolioActive: Story = {
  args: {
    activeTab: 'portfolio',
    hasSelectedItem: true,
  },
};
