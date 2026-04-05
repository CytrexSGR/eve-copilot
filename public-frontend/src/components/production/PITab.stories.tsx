import type { Meta, StoryObj } from '@storybook/react';
import { PITab } from './PITab';

const meta: Meta<typeof PITab> = {
  title: 'Production/PI Chain/PITab',
  component: PITab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PITab>;

/**
 * With selected item: shows PI item analysis sub-tab with
 * material cost breakdown, production chain visualization,
 * and P0 resource summary.
 */
export const WithItem: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
  },
};

/**
 * No item selected: shows prompt to select an item,
 * with Chain Planner and Empire sub-tabs still accessible.
 */
export const NoItem: Story = {
  args: {
    selectedItem: null,
  },
};
