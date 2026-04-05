import type { Meta, StoryObj } from '@storybook/react';
import { HistoryTab } from './HistoryTab';
import { mockTritaniumItem, mockDrakeItem } from '../../../.storybook/mocks/data/market';

const meta: Meta<typeof HistoryTab> = {
  title: 'Economy & Market/Market/HistoryTab',
  component: HistoryTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof HistoryTab>;

/**
 * Tritanium order book: shows regional price comparison
 * and Jita sell/buy order depth with volume bars.
 */
export const Tritanium: Story = {
  args: {
    selectedItem: mockTritaniumItem,
  },
};

/**
 * Drake order book: ship-class item for comparison.
 */
export const Drake: Story = {
  args: {
    selectedItem: mockDrakeItem,
  },
};
