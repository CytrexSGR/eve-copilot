import type { Meta, StoryObj } from '@storybook/react';
import { ReactionsTab } from './ReactionsTab';

const meta: Meta<typeof ReactionsTab> = {
  title: 'Production/Projects/ReactionsTab',
  component: ReactionsTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof ReactionsTab>;

/**
 * Default: Reaction materials for a T2 item, showing expandable
 * reaction chain trees, category badges, and moon goo summary.
 * Fetches reaction requirements via MSW.
 */
export const Default: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
  },
};
