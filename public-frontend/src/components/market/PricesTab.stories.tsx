import type { Meta, StoryObj } from '@storybook/react';
import { PricesTab } from './PricesTab';
import {
  mockTritaniumItem,
  mockTritaniumDetail,
  mockDrakeItem,
} from '../../../.storybook/mocks/data/market';

const meta: Meta<typeof PricesTab> = {
  title: 'Economy & Market/Market/PricesTab',
  component: PricesTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PricesTab>;

/**
 * Tritanium: cheap mineral with tight spreads across all hubs.
 * Shows all 5 trade hub prices, volume, trend, and risk stats.
 */
export const Tritanium: Story = {
  args: {
    selectedItem: mockTritaniumItem,
    itemDetail: mockTritaniumDetail,
  },
};

/**
 * Without item detail - no description section shown.
 */
export const WithoutDetail: Story = {
  args: {
    selectedItem: mockTritaniumItem,
    itemDetail: null,
  },
};

/**
 * Drake battlecruiser: higher-value item for ship price comparison.
 */
export const Drake: Story = {
  args: {
    selectedItem: mockDrakeItem,
    itemDetail: null,
  },
};
