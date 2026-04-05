import type { Meta, StoryObj } from '@storybook/react';
import { MarketTicker } from './MarketTicker';

const meta: Meta<typeof MarketTicker> = {
  title: 'Economy & Market/Market/MarketTicker',
  component: MarketTicker,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof MarketTicker>;

/**
 * Default: fetches hot items and displays a scrolling ticker
 * with mineral, isotope, fuel block, moon material, and salvage prices.
 * Hover to pause the ticker animation.
 */
export const Default: Story = {};
