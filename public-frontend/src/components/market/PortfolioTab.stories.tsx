import type { Meta, StoryObj } from '@storybook/react';
import { PortfolioTab } from './PortfolioTab';

const meta: Meta<typeof PortfolioTab> = {
  title: 'Economy & Market/Market/PortfolioTab',
  component: PortfolioTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PortfolioTab>;

/**
 * Default (logged in): shows Orders sub-tab with sell/buy order summary,
 * outbid alerts, and order table. Toggle to P&L for realized/unrealized
 * profit or Portfolio for wallet/escrow snapshots.
 */
export const Default: Story = {};
