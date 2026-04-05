import type { Meta, StoryObj } from '@storybook/react';
import { MarketTab } from './MarketTab';

/**
 * MarketTab is a large data-fetching component (~800 lines) that shows
 * wormhole commodity prices, market indices, supply disruptions, and price
 * histories. It fetches data internally via wormholeApi.
 *
 * MSW handlers mock the /api/wormhole/market endpoint.
 */
const meta: Meta<typeof MarketTab> = {
  title: 'Intel & Battle/Wormhole/MarketTab',
  component: MarketTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof MarketTab>;

export const Default: Story = {};
