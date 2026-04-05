import type { Meta, StoryObj } from '@storybook/react';
import { ArbitrageTab } from './ArbitrageTab';

const meta: Meta<typeof ArbitrageTab> = {
  title: 'Economy & Market/Market/ArbitrageTab',
  component: ArbitrageTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof ArbitrageTab>;

/**
 * Default: shows filter bar (cargo, jumps, min profit, turnover, competition)
 * and profitable routes from Jita to other hubs.
 * Routes display destination, safety, jumps, profit, ROI, and ISK/jump.
 * Click a route to expand and see individual items.
 */
export const Default: Story = {};
