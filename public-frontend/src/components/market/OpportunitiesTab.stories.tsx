import type { Meta, StoryObj } from '@storybook/react';
import { OpportunitiesTab } from './OpportunitiesTab';

const meta: Meta<typeof OpportunitiesTab> = {
  title: 'Economy & Market/Market/OpportunitiesTab',
  component: OpportunitiesTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof OpportunitiesTab>;

/**
 * Default: shows Manufacturing sub-tab with opportunity scanner.
 * Includes filter controls (min ROI, max difficulty, sort, search)
 * and a table of profitable items to manufacture.
 * Toggle to Trading sub-tab for station trading opportunities.
 */
export const Default: Story = {};
