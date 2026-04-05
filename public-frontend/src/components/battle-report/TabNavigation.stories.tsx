import type { Meta, StoryObj } from '@storybook/react';
import { TabNavigation } from './TabNavigation';
import { fn } from '@storybook/test';

const meta: Meta<typeof TabNavigation> = {
  title: 'BattleReport/TabNavigation',
  component: TabNavigation,
  parameters: { layout: 'centered' },
};
export default meta;
type Story = StoryObj<typeof TabNavigation>;

export const Battlefield: Story = {
  args: {
    activeTab: 'battlefield',
    onTabChange: fn(),
  },
};

export const Alliances: Story = {
  args: {
    activeTab: 'alliances',
    onTabChange: fn(),
  },
};

export const Intelligence: Story = {
  args: {
    activeTab: 'intelligence',
    onTabChange: fn(),
  },
};
