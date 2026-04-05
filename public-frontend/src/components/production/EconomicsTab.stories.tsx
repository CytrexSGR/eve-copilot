import type { Meta, StoryObj } from '@storybook/react';
import { EconomicsTab } from './EconomicsTab';
import { fn } from '@storybook/test';

const meta: Meta<typeof EconomicsTab> = {
  title: 'Production/Projects/EconomicsTab',
  component: EconomicsTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof EconomicsTab>;

/**
 * Default: Manufacturing Opportunities table with filter bar,
 * sortable columns, and ROI color-coding. Fetches data via MSW.
 */
export const Default: Story = {
  args: {
    onNavigateToItem: fn(),
  },
};

/** Without navigation: item names are plain text, not clickable. */
export const WithoutNavigation: Story = {
  args: {},
};
