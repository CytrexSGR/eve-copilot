import type { Meta, StoryObj } from '@storybook/react';
import { MarketHeroSection } from './MarketHeroSection';

const meta: Meta<typeof MarketHeroSection> = {
  title: 'Economy & Market/Market/MarketHeroSection',
  component: MarketHeroSection,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof MarketHeroSection>;

/**
 * Default state: fetches hot items via MSW to calculate summary stats.
 * Shows "Market Suite" header with items count, avg spread, and market health.
 */
export const Default: Story = {};
