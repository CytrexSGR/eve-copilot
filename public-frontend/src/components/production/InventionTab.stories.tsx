import type { Meta, StoryObj } from '@storybook/react';
import { InventionTab } from './InventionTab';

const meta: Meta<typeof InventionTab> = {
  title: 'Production/Projects/InventionTab',
  component: InventionTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof InventionTab>;

/**
 * Default: Decryptor comparison table with cost/run ranking,
 * best-option banner, and clickable decryptor detail cards.
 * Fetches invention data via MSW.
 */
export const Default: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
  },
};

/** Rifter: different item for invention analysis. */
export const Rifter: Story = {
  args: {
    selectedItem: { typeID: 587, typeName: 'Rifter', groupName: 'Frigate' },
  },
};
